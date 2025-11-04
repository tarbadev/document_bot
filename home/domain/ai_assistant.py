import time
from typing import Optional

from langchain.chat_models import init_chat_model
from langchain_core.documents import Document
from langchain_core.prompts import ChatPromptTemplate
from langfuse import get_client
from langgraph.graph import StateGraph, START

from document_bot.analytics import debug, record_llm_call, record_question_attempt
from home.domain.document_repository import DocumentRepository
from home.domain.invalid_question_error import InvalidQuestionError
from home.domain.question_validator import QuestionValidator
from home.domain.quoted_answer import QuotedAnswer
from home.domain.state import State
from home.infrastructure.flagged_question_tracker import get_tracker

model = "gpt-4o-mini"
model_provider = "openai"


class AiAssistant:
    def __init__(self, document_repository: DocumentRepository, question_validator: QuestionValidator):
        self.graph = self._build_graph()
        self.document_repository = document_repository
        self.question_validator = question_validator
        self.llm = (init_chat_model(model, model_provider=model_provider)
                    .with_structured_output(QuotedAnswer))
        self.flagged_tracker = get_tracker()
        self.langfuse = get_client()

    def _build_graph(self):
        graph_builder = StateGraph(State).add_sequence([self.retrieve, self.generate])
        graph_builder.add_edge(START, "retrieve")
        return graph_builder.compile()

    def answer(self, question: str, new_document: list[Document], user_id: Optional[str] = None) -> str:
        validation_status = "safe"
        is_recovery = False

        if user_id:
            is_recovery = self.flagged_tracker.check_recovery(user_id)

        with self.langfuse.start_as_current_span(
            name="question_answer",
            input={"question": question, "question_length": len(question)},
            metadata={
                "has_new_document": new_document is not None and len(new_document) > 0,
                "user_id": user_id or "anonymous"
            }
        ) as trace_span:
            try:
                with self.langfuse.start_as_current_span(
                    name="validation",
                    input={"question": question}
                ) as validation_span:
                    try:
                        self.question_validator.validate(question, user_id=user_id)

                        validation_span.update(output={"passed": True})

                        if user_id:
                            was_recovery = self.flagged_tracker.record_success(user_id)
                            if was_recovery:
                                is_recovery = True

                        record_question_attempt(
                            user_id=user_id,
                            flagged=False,
                            is_recovery=is_recovery
                        )

                    except InvalidQuestionError as e:
                        validation_status = "flagged"
                        failed_validator = str(e)

                        validation_span.update(output={"passed": False, "reason": str(e)})

                        if user_id:
                            self.flagged_tracker.record_flagged(user_id)

                        record_question_attempt(
                            user_id=user_id,
                            flagged=True,
                            validator_failed=failed_validator
                        )

                        trace_span.update_trace(tags=["flagged", "blocked"])
                        trace_span.update(
                            output={"error": str(e)},
                            metadata={
                                "validation_status": validation_status,
                                "failed_validator": failed_validator
                            }
                        )

                        raise

                with self.langfuse.start_as_current_span(
                    name="retrieval",
                    input={"question": question}
                ) as retrieval_span:
                    result = self.graph.invoke({"question": question, "new_document": new_document})

                    retrieval_span.update(output={
                        "num_documents": len(result["existing_documents"]),
                        "sources": [doc.metadata.get("source", "unknown") for doc in result["existing_documents"]]
                    })

                debug("answer",
                      {
                          "question": question,
                          "source": [doc.metadata["source"] for doc in result["existing_documents"]],
                          "answer": result['answer'].model_dump()
                      })

                trace_span.update_trace(tags=["safe"] + (["recovery"] if is_recovery else []))
                trace_span.update(
                    output={"answer": result['answer'].model_dump()},
                    metadata={
                        "validation_status": validation_status,
                        "num_sources": len(result["existing_documents"]),
                        "is_recovery": is_recovery
                    }
                )

                return result["answer"].to_string()

            except Exception as e:
                trace_span.update_trace(tags=["error"])
                trace_span.update(
                    output={"error": str(e)},
                    metadata={"validation_status": validation_status}
                )
                raise

    def retrieve(self, state: State) -> State:
        state["existing_documents"] = self.document_repository.similarity_search(state["question"])
        return state

    def generate(self, state: State) -> dict:
        existing_documents = "\n\n".join([
            f"[Source {i + 1}]\n{doc.page_content}"
            for i, doc in enumerate(state["existing_documents"])
        ])
        num_existing = len(state["existing_documents"])
        new_document = "\n\nNew document:\n: None\n"
        if state.get("new_document") and len(state["new_document"]) > 0:
            new_document = (
                    "\n\n".join([
                        f"[Source {num_existing + i + 1}]\n{doc.page_content}"
                        for i, doc in enumerate(state["new_document"])
                    ]) +
                    "\n\"\"\""
            )

        total_documents = num_existing + (0 if state["new_document"] is None else 1)

        system_prompt = (
            "You're a helpful AI assistant. Given documents and a user's question, "
            "answer the user's question based only on the provided sources. "
            f"You have {total_documents} sources available."
            "\n\nExisting documents:\n\"\"\"\n{existing_documents}\n\"\"\""
            "\n\nNew document:\n\"\"\"\n{new_document}\n\"\"\""
        )

        prompt = ChatPromptTemplate.from_messages(
            [
                ("system", system_prompt),
                ("human", "{question}"),
            ]
        )
        prompt_value = prompt.invoke({
            "question": state["question"],
            "existing_documents": existing_documents,
            "new_document": new_document,
        })

        t0 = time.perf_counter()
        ok = True
        prompt_tokens = completion_tokens = total_tokens = None

        try:
            response = self.llm.invoke(prompt_value)
            usage = getattr(response, "usage", None)
            if usage:
                prompt_tokens = getattr(usage, "prompt_tokens", None)
                completion_tokens = getattr(usage, "completion_tokens", None)
                total_tokens = getattr(usage, "total_tokens", None)
            return {"answer": response}
        except Exception:
            ok = False
            raise
        finally:
            dt_ms = (time.perf_counter() - t0) * 1000.0
            tokens = None
            if total_tokens is not None:
                tokens = {
                    "prompt": prompt_tokens or 0,
                    "completion": completion_tokens or 0,
                    "total": total_tokens or 0
                }
            record_llm_call(model=model, ok=ok, duration_ms=dt_ms, tokens=tokens)
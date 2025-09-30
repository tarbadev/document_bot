import json
import math
import os

from django import forms
from django.views.generic import FormView
from openai import OpenAI

FAQ_FILE_PATH = "faq.json"
EMBEDDINGS_FILE_PATH = "faq-embeddings.json"
EMBEDDING_MODEL = "text-embedding-3-small"

client = OpenAI()


def setup_embeddings():
    with open(FAQ_FILE_PATH, "r", encoding="utf-8") as f:
        faqs = json.load(f)

    for item in faqs:
        print("Q:", item["q"])
        print("A:", item["a"])
        print("---")

    inputs = [item["q"] for item in faqs]

    resp = client.embeddings.create(model=EMBEDDING_MODEL, input=inputs)
    vecs = [d.embedding for d in resp.data]

    for item, emb in zip(faqs, vecs):
        item["embedding"] = emb

    with open(EMBEDDINGS_FILE_PATH, "w", encoding="utf-8") as f:
        json.dump(faqs, f, ensure_ascii=False, indent=2)

    print("Wrote {} with".format(EMBEDDINGS_FILE_PATH), len(faqs), "items.")

    return load_embeddings()


def load_embeddings():
    if not os.path.exists(EMBEDDINGS_FILE_PATH):
        return setup_embeddings()

    with open(EMBEDDINGS_FILE_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def add_to_messages(author, content):
    messages.append({"author": author, "content": content})


class AskQuestionForm(forms.Form):
    question = forms.CharField()
    index = load_embeddings()

    def search(self, query_embedding, index, k=1):
        scored = [(self.cosine(query_embedding, item["embedding"]), item) for item in index]
        scored.sort(key=lambda x: x[0], reverse=True)
        topk = scored[:k]
        return [{"similarity": round(sim, 4), "q": it["q"], "a": it["a"]} for sim, it in topk]

    def ask(self):
        question_asked = self.cleaned_data["question"]
        add_to_messages('user', question_asked)

        emb = client.embeddings.create(model=EMBEDDING_MODEL, input=question_asked).data[0].embedding

        result = self.search(emb, self.index, k=1)[0]

        print("Matched:", result["q"])
        answer = result["a"]
        print("Answer:", answer, "| similarity:", result["similarity"])

        add_to_messages('assistant', """
        Matched question: {}
        Answer: {}
        """.format(result["q"], answer))

        return answer

    @staticmethod
    def cosine(u, v):
        dot = sum(a * b for a, b in zip(u, v))
        nu = math.sqrt(sum(a * a for a in u))
        nv = math.sqrt(sum(b * b for b in v))
        return 0.0 if nu == 0.0 or nv == 0.0 else dot / (nu * nv)


messages = []


class HomePageView(FormView):
    template_name = 'home/home.html'
    form_class = AskQuestionForm
    success_url = '.'
    extra_context = {'messages': messages}

    def get_context_data(self, **kwargs):
        context = super(HomePageView, self).get_context_data(**kwargs)

        return context

    def form_valid(self, form):
        form.ask()

        return super(HomePageView, self).form_valid(form)

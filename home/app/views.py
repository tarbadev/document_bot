from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.generic import FormView

from document_bot.analytics import error
from home.app.ask_question_form import AskQuestionForm
from home.domain.invalid_question_error import InvalidQuestionError
from home.messages_repository import get_messages, delete_messages


class HomePageView(FormView):
    template_name = 'home/home.html'
    form_class = AskQuestionForm
    success_url = '.'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['messages'] = get_messages()
        return context

    def form_valid(self, form):
        user_id = self.request.session.session_key
        if not user_id:
            self.request.session.create()
            user_id = self.request.session.session_key

        try:
            form.upload_and_ask_question(self.request.FILES.get("file"), user_id=user_id)
        except InvalidQuestionError as e:
            error("form_valid", {
                "message": "Invalid question",
                "error": str(e),
                "question": form.cleaned_data.get("question"),
                "user_id": user_id
            })
            form.add_error('question', str(e) if str(e) else 'Your question is not appropriate or valid. Please try a different question.')
            return self.form_invalid(form)
        except Exception as e:
            error("form_valid", {
                "message": "Unexpected error",
                "error": str(e),
                "question": form.cleaned_data.get("question"),
                "user_id": user_id
            })
            form.add_error(None, 'An unexpected error occurred. Please try again.')
            return self.form_invalid(form)

        return super(HomePageView, self).form_valid(form)


@require_http_methods(["DELETE"])
def clear_messages(request):
    try:
        delete_messages()
        return JsonResponse({'success': True, 'message': 'Messages cleared successfully'})
    except Exception as e:
        error("clear_messages", {"message": "Error deleting messages", error: e, "request": request})
        return JsonResponse({'success': False, 'message': 'Failed to clear messages'}, status=500)

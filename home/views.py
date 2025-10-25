from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.generic import FormView
from home.ask_question_form import AskQuestionForm
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
        form.upload_and_ask_question(self.request.FILES.get("file"))

        return super(HomePageView, self).form_valid(form)

@require_http_methods(["DELETE"])
def clear_messages(request):
    try:
        delete_messages()
        return JsonResponse({'success': True, 'message': 'Messages cleared successfully'})
    except Exception as e:
        print(f"Error deleting messages: {e}")
        return JsonResponse({'success': False, 'message': 'Failed to clear messages'}, status=500)
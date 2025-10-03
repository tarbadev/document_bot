from django.views.generic import FormView

from home.ask_question_form import AskQuestionForm
from home.messages_repository import get_messages


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

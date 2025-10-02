from django.views.generic import FormView

from home.ask_question_form import AskQuestionForm
from home.messages_repository import get_messages


class HomePageView(FormView):
    template_name = 'home/home.html'
    form_class = AskQuestionForm
    success_url = '.'
    # extra_context = {'messages': get_messages()}

    def get_context_data(self, **kwargs):
        context = super(HomePageView, self).get_context_data(**kwargs)

        messages = get_messages()
        context['messages'] = messages

        print("GENERATING CONTEXT DATA")
        print(context["messages"])

        return context

    def form_valid(self, form):
        form = AskQuestionForm(self.request.POST, self.request.FILES)
        if form.is_valid():
            form.upload_and_ask_question(self.request.FILES.get("file"))

        return super(HomePageView, self).form_valid(form)

from django.views.generic import FormView

from home.ask_question_form import AskQuestionForm

messages = []


def add_to_messages(author, content):
    messages.append({"author": author, "content": content})


class HomePageView(FormView):
    template_name = 'home/home.html'
    form_class = AskQuestionForm
    success_url = '.'
    extra_context = {'messages': messages}

    def get_context_data(self, **kwargs):
        context = super(HomePageView, self).get_context_data(**kwargs)

        return context

    def form_valid(self, form):
        form = AskQuestionForm(self.request.POST, self.request.FILES)
        if form.is_valid():
            form.upload_and_ask_question(self.request.FILES["file"])

        return super(HomePageView, self).form_valid(form)

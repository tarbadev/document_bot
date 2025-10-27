from document_bot.analytics import debug
from home.models import Message


def get_messages():
    return Message.objects.all()

def delete_messages():
    Message.objects.all().delete()

def add_message(author: str, content: str):
    Message.objects.create(author=author, content=content).save()
    debug("add_message", { content: content, author: author})

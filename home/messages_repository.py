from home.models import Message


def get_messages():
    return Message.objects.all()


def add_message(author: str, content: str):
    Message.objects.create(author=author, content=content).save()
    print(f"Added '{content}' for role '{author}'")
    print(Message.objects.all())

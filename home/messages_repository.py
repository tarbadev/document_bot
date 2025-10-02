from home.models import Message


def get_messages():
    return Message.objects.all()


def add_to_messages(author: str, message: str):
    Message.objects.create(author=author, message=message).save()
    print(f"Added '{message}' for role '{author}'")
    print(Message.objects.all())

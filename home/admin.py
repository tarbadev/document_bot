from django.contrib import admin

from . import models


class MessageAdmin(admin.ModelAdmin):
    pass


admin.site.register(models.Message, MessageAdmin)

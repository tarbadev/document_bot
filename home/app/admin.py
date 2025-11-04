from django.contrib import admin

from home import models


class MessageAdmin(admin.ModelAdmin):
    list_display = ('author', 'content')


admin.site.register(models.Message, MessageAdmin)

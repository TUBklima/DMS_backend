from django.contrib import admin
from .models import UC2Observation

from . import models


class UC2Admin(admin.ModelAdmin):
    model = models.UC2Observation
    list_display = ('file', )

    def create(self, obj):
        return obj.file


admin.site.register(UC2Observation)

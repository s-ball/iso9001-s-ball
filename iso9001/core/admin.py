"""Declare models for the admin site"""

from django.contrib import admin

from .models import Process, PolicyAxis


# Register your models here.
admin.site.register((Process, PolicyAxis))

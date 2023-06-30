"""Declare models for the admin site"""

from typing import Any, Optional
from django.contrib import admin, messages
from django.db.models.fields.related import ForeignKey
from django.forms.models import ModelChoiceField
from django.http.request import HttpRequest
from django.utils.translation import ngettext, gettext as _

from adminsortable2.admin import SortableAdminMixin

from .models import Process, PolicyAxis, StatusModel, Contribution


# Register your models here.
@admin.register(Process, PolicyAxis)
class StatusModelAdmin(SortableAdminMixin, admin.ModelAdmin):
    """ModelAdmin for StatusModel subclasses.

    Provides actions to change the status through the model methods.
    """
    @admin.action(description=_("Make applicable"), permissions=['status'])
    def make_applicable(self, request, queryset):
        """Bump a bunch of objects into applicable status"""
        obj: StatusModel
        count = 0
        for obj in queryset:
            if obj.status != StatusModel.Status.APPLICABLE:
                obj.make_applicable()
                self.log_change(request, obj, "made applicable")
                count += 1
        self.message_user(request, ngettext(
            '{count} object was made applicable',
            '{count} objects were made applicable',
            count
            ).format(count=count),
            messages.SUCCESS if count > 0 else messages.WARNING)

    @admin.action(description=_("Create draft copies"), permissions=['add'])
    def build_draft(self, request, queryset):
        """Create draft copies"""
        obj: StatusModel
        count = 0
        for obj in queryset:
            draft = obj.build_draft()
            self.log_addition(request, draft, "created as draft")
            count += 1
        self.message_user(request, ngettext(
            '{count} draft object was created',
            '{count} draft objects were created',
            count
            ).format(count=count),
            messages.SUCCESS if count > 0 else messages.WARNING)

    @admin.action(description=_("Retire"), permissions=['status'])
    def retire(self, request, queryset):
        """Take a bunch of objects into retired status"""
        obj: StatusModel
        count = 0
        for obj in queryset:
            if obj.status == StatusModel.Status.APPLICABLE:
                obj.retire()
                self.log_change(request, obj, "retired")
                count += 1
        self.message_user(request, ngettext(
            '{count} object was retired',
            '{count} objects were retired',
            count
            ).format(count=count),
            messages.SUCCESS if count > 0 else messages.WARNING)

    def has_status_permission(self, request: HttpRequest) -> bool:
        """Only Quality Manager can change status of objects"""
        user = request.user
        return user.has_perm('core.is_qm')

    actions = ['make_applicable', 'build_draft', 'retire']
    list_display = ['__str__', 'status', 'start_date', 'end_date']


@admin.register(Contribution)
class ContributionAdmin(admin.ModelAdmin):
    """Use a custom ModelAdmin to only show applicable objects"""
    def formfield_for_foreignkey(self, db_field: ForeignKey[Any],
                                 request: Optional[HttpRequest],
                                 **kwargs: Any) -> Optional[ModelChoiceField]:
        model = {'process': Process, 'axis': PolicyAxis}
        kwargs['queryset'] = model[db_field.name].objects.filter(
            status=StatusModel.Status.APPLICABLE,
        )
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

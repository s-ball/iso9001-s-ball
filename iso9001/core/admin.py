"""Declare models for the admin site"""

from typing import Any, Optional
from django.contrib import admin, messages
from django.db.models.fields.related import ForeignKey
from django.forms.models import ModelChoiceField
from django.http.request import HttpRequest
from django.utils.translation import ngettext, gettext as _

from adminsortable2.admin import SortableAdminMixin

from .models import Process, PolicyAxis, StatusModel, Contribution, Objective
from .models import Document


# Register your models here.
class BaseStatusModelAdmin(admin.ModelAdmin):
    """ModelAdmin for StatusModel subclasses.

    Provides actions to change the status through the model methods.
    """
    pre_applicable_status = StatusModel.Status.DRAFT

    @admin.action(description=_("Make applicable"), permissions=['status'])
    def make_applicable(self, request, queryset):
        """Bump a bunch of objects into applicable status"""
        obj: StatusModel
        count = 0
        for obj in queryset.filter(status=self.pre_applicable_status):
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
        for obj in queryset.filter(status=StatusModel.Status.APPLICABLE):
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
        for obj in queryset.filter(status=StatusModel.Status.APPLICABLE):
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

@admin.register(Process, PolicyAxis)
class StatusModelAdmin(SortableAdminMixin, BaseStatusModelAdmin):
    """Use SortableAdminMixin to be able to sort processes and axes"""

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


@admin.register(Objective)
class ObjectiveAdmin(admin.ModelAdmin):
    """Add fields into the list view"""
    list_display = ['__str__', 'name', 'value', 'get_status']

    @admin.display(description=_('Process status'))
    def get_status(self, obj: Objective) -> str:
        """Gives the status of the associated process"""
        return obj.process.get_status_display()


@admin.register(Document)
class DocumentAdmin(BaseStatusModelAdmin):
    """Custom admin class to handle authorizations"""
    pre_applicable_status = StatusModel.Status.AUTHORIZED

    @admin.action(description=_("Authorize"), permissions=['status'])
    def authorize(self, request, queryset):
        """Bump draft documents to authorized status"""
        obj: Document
        count = 0
        for obj in queryset.filter(status=StatusModel.Status.DRAFT):
            obj.authorize(request.user)
            self.log_change(request, obj, "authorized")
            count += 1
        self.message_user(request, ngettext(
            '{count} object was authorized',
            '{count} objects were authorized',
            count
            ).format(count=count),
            messages.SUCCESS if count > 0 else messages.WARNING)

    @admin.display(description=_('Process status'))
    def process_status(self, obj) -> str:
        """Display the status of the associated process"""
        return obj.process.get_status_display()

    actions = ['make_applicable', 'build_draft', 'retire', 'authorize']
    list_display = ['__str__', 'status', 'process_status',
                    'start_date', 'end_date']

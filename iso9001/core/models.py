"""Models for the processes app"""
# pylint: disable=missing-class-docstring
# pylint: disable=too-few-public-methods
import datetime
from typing import Any, Collection, Optional, TypeVar

from django.db import models
from django.db.models import Q, F
from django.contrib.auth import get_user_model
from django.forms import ValidationError
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.core.exceptions import NON_FIELD_ERRORS, ObjectDoesNotExist, \
    PermissionDenied
from django.db import transaction

from concurrency.fields import AutoIncVersionField

# Ensure using the current User model
User = get_user_model()


# Create your models here.
# Will be used for generic cloning
SM = TypeVar('SM', bound='StatusModel')


class StatusModel(models.Model):
    class Status(models.IntegerChoices):
        DRAFT = 0, _('Draft')
        APPLICABLE = 1, _('Applicable')
        RETIRED = 2, _('Retired')
        AUTHORIZED = 3, _('authorized')

    status = models.SmallIntegerField(choices=Status.choices,
                                      default=Status.DRAFT)
    start_date = models.DateField(default=datetime.date.today)
    end_date = models.DateField(null=True, blank=True)
    # for django-concurrency optimistic locking
    version = AutoIncVersionField()
    previous = models.OneToOneField('self', related_name='successor',
                                    on_delete=models.SET_NULL,
                                    null=True, blank=True, default=None)

    def clone(self: SM) -> SM:
        """Creates a copy of self.
(expected to be overridden in subclasses)
"""
        raise NotImplementedError

    def build_draft(self: SM) -> SM:
        """Builds a draft copy of self using clone"""
        if self.status not in (StatusModel.Status.APPLICABLE,
                               StatusModel.Status.RETIRED):
            raise ValueError(_('{} is not in applicable status')
                             .format(str(self)))
        with transaction.atomic():
            draft = self.clone()
            draft.status = StatusModel.Status.DRAFT
            draft.previous = self
            draft.start_date = timezone.now()
            draft.save()
        return draft

    def make_applicable(self) -> None:
        """Pass a draft into applicable state"""
        # search for a previous version
        if self.status in (StatusModel.Status.APPLICABLE,
                           StatusModel.Status.RETIRED):
            raise ValueError(_('{} is already in inacceptable status')
                             .format(str(self)))
        with transaction.atomic():
            dat = timezone.now()
            if self.previous is not None and \
                    self.previous.status != StatusModel.Status.RETIRED:
                self.previous.retire(dat, recurse=False)
            self.status = StatusModel.Status.APPLICABLE
            self.end_date = None
            self.start_date = dat
            self.save()

    # pylint: disable=unused-argument
    def retire(self, end_date: datetime.datetime = None, recurse=True) -> None:
        """Pass a model to the retired state"""
        if self.status != StatusModel.Status.APPLICABLE:
            raise ValueError(_('{} is not in applicable status')
                             .format(str(self)))
        with transaction.atomic():
            if end_date is None:
                end_date = timezone.now()
            self.status = StatusModel.Status.RETIRED
            self.end_date = end_date
            self.save()

    # pylint: enable=unused-argument
    def unretire(self) -> None:
        """Revert an incorrect retirement"""
        if self.status != StatusModel.Status.RETIRED:
            raise ValueError(_('{} is not in retired status')
                             .format(str(self)))
        if self.__class__.objects.filter(previous=self).exists():
            raise ValueError(_('{} has already a successor')
                             .format(str(self)))
        self.status = StatusModel.Status.APPLICABLE
        self.end_date = None
        self.save()

    def revert(self):
        """Remove the authorization to be able to modify the draft"""
        if self.status != self.Status.AUTHORIZED:
            raise ValueError(_('{} is not in authorized status')
                             .format(str(self)))
        self.status = self.Status.DRAFT

    def clean_fields(self, exclude: Optional[Collection[str]] = ...) -> None:
        """status field should not be changed in a form"""
        errors = {}
        # do super validation
        try:
            super().clean_fields(exclude)
        except ValidationError as err:
            errors = err.update_error_dict(errors)
        # extract original status is any
        try:
            prev: StatusModel = self.__class__.objects.get(pk=self.pk)
        except ObjectDoesNotExist:
            prev = None
        if prev:
            if prev.status != self.status:
                errors['status'] = _('Status cannot be changed')
        elif self.status != StatusModel.Status.DRAFT:
            errors['status'] = _('Objects can only be created as draft')

        if errors:
            raise ValidationError(errors)

    def clean(self) -> None:
        # applicable objects should not be changed by normal forms
        errors = {}
        # first do super validation
        try:
            super().clean()
        except ValidationError as err:
            err.update_error_dict(errors)
        # test status
        if self.status != StatusModel.Status.DRAFT and 'status' not in errors:
            if NON_FIELD_ERRORS in errors:
                errors[NON_FIELD_ERRORS].append(
                    _('Only draft objects can change'))
            else:
                errors[NON_FIELD_ERRORS] = _('Only draft objects can change')

        if errors:
            raise ValidationError(errors)

    class Meta:
        abstract = True
        constraints = [models.UniqueConstraint(
            fields=('name',),
            condition=models.Q(status=1),
            name='%(class)s_name'
        ), models.CheckConstraint(
            name='%(class)s_dates',
            check=Q(end_date__gte=F('start_date')) | Q(end_date=None)
        )]


# pylint: disable=abstract-method
class AbstractDocument(StatusModel):
    """Abstract model for documented information"""
    class Meta(StatusModel.Meta):
        abstract = True
        constraints = [models.UniqueConstraint(
            fields=('process', 'name',),
            condition=models.Q(status=1),
            name='%(class)s_name'
        ), models.CheckConstraint(
            name='%(class)s_dates',
            check=Q(end_date__gte=F('start_date')) | Q(end_date=None)
        )]

    process = models.ForeignKey('Process', on_delete=models.CASCADE)
    name = models.CharField(max_length=64)
    pdf = models.FileField(upload_to='docs')

    def __str__(self):
        """Display name"""
        return f'{self.process.name}-{self.name}'


# pylint: enable=abstract-method
class Document(AbstractDocument):
    """Concrete model for applicable (versioned) documents"""
    parents = models.ManyToManyField('self', symmetrical=False,
                                     blank=True,
                                     related_name='children')
    autority = models.ForeignKey(User, on_delete=models.PROTECT,
                                 null=True, blank=True)

    def clone(self: SM) -> SM:
        return Document(process=self.process, name=self.name)

    @transaction.atomic
    def build_draft(self) -> 'Document':
        """Build a draft copy.

Make the draft have same parents as the original document and
make all children of the original document have the draft as parent."""
        draft = super().build_draft()
        draft.parents.set((self.parents.order_by('-start_date')[:1]))
        for child in self.children.all():
            child.parents.add(draft)
            child.save()
        draft.save()
        return draft

    def make_applicable(self) -> None:
        """A document shall be applicable only if its parent and process are.

Actually it must have no parent at all or one applicable parent.
When making a document applicable, all its children in authorized status
are made applicable too."""
        if self.process.status != StatusModel.Status.APPLICABLE:
            raise ValueError('Process is not applicable')
        if self.status != StatusModel.Status.AUTHORIZED:
            raise ValueError('This document has not be authorized')
        if self.parents.exists():
            if not self.parents.filter(
                    status=StatusModel.Status.APPLICABLE).exists():
                raise ValueError('This document has no applicable parent')
        with transaction.atomic():
            # If previous document was the process document, replace it
            if (self.process.doc and self.previous
                    and self.process.doc == self.previous):
                self.process.doc = self
            super().make_applicable()
            for child in self.children.filter(
                    status=StatusModel.Status.AUTHORIZED):
                child.make_applicable()

    def authorize(self, user: User):
        """A draft shall be authorized before it is made applicable"""
        if self.status != StatusModel.Status.DRAFT:
            raise ValueError('Only draft document can be authorized')
        if self.pdf is None:
            raise ValueError('This document contains no file')
        if not user.has_perm('core.authorize_document'):
            raise PermissionDenied
        with transaction.atomic():
            self.autority = user
            self.status = StatusModel.Status.AUTHORIZED
            self.save()

    def retire(self, end_date: datetime.date = None, recurse: bool = True
               ) -> None:
        if (self.process.doc and self.process.doc == self
                and self.process.status == StatusModel.Status.APPLICABLE):
            raise ValueError('Cannot remove the main document'
                             ' for an applicable process')
        with transaction.atomic():
            draft_parent = self.parents.filter(
                status=StatusModel.Status.DRAFT).first()
            if draft_parent is not None:
                draft = self.build_draft()
                draft.parents.set((draft_parent,))
                self.parents.remove(draft_parent)
            super().retire(end_date)
            if recurse:
                for child in self.children.all():
                    child.retire(end_date)

    @transaction.atomic
    def unretire(self) -> None:
        end_date = self.end_date
        super().unretire()
        for child in self.children.filter(
            status=StatusModel.Status.RETIRED, end_date=end_date,
        ):
            child.unretire()

    class Meta(AbstractDocument.Meta):
        permissions = [('authorize_document', _('May authorize documents'))]
        ordering = ('process', 'name', '-start_date')


class ProcessManager(models.Manager):
    """Custom manager to initialize a document at creation time"""
    def create(self, **kwargs: Any) -> 'Process':
        """Set an empty document for every new Process object"""
        with transaction.atomic():
            proc = super().create(**kwargs)
            proc.doc = Document.objects.create(
                process=proc, status=proc.status, name=proc.name,
                start_date=proc.start_date, end_date=proc.end_date)
            proc.save()
        return proc


class Process(StatusModel):
    name = models.SlugField(max_length=8)
    desc = models.TextField()
    pilots = models.ManyToManyField(to=User, blank=True)
    doc = models.ForeignKey(Document, on_delete=models.RESTRICT,
                            null=True, blank=True, related_name='+')

    model_order = models.PositiveSmallIntegerField(
        default=0, blank=False, null=False, db_index=True,
    )

    def clone(self) -> 'Process':
        return Process(name=self.name, desc=self.desc)

    @transaction.atomic()
    def build_draft(self) -> "Process":
        draft = super().build_draft()
        draft.pilots.set(self.pilots.all())
        if self.doc:
            draft.doc = self.doc.build_draft()
        draft.save()
        return draft

    @transaction.atomic()
    def make_applicable(self) -> None:
        super().make_applicable()
        self.doc.process = self
        self.doc.make_applicable()

    @transaction.atomic
    def retire(self, end_date: datetime.date = None, recurse=True) -> None:
        super().retire(end_date)
        if self.doc:
            self.doc.retire(end_date, recurse)

    def __str__(self):
        return str(self.name)

    objects = ProcessManager()

    class Meta(StatusModel.Meta):
        verbose_name = _('Process')
        verbose_name_plural = _('Processes')
        permissions = [('is_qm', _('Quality manager'))]
        ordering = ['model_order']


class PolicyAxis(StatusModel):
    name = models.SlugField(max_length=4)
    desc = models.CharField(max_length=64)
    long_desc = models.TextField()
    reviewed = models.DateField(default=timezone.now)
    processes = models.ManyToManyField(to=Process, through="Contribution",
                                       blank=True)

    model_order = models.PositiveSmallIntegerField(
        default=0, blank=False, null=False, db_index=True,
    )

    def clone(self) -> StatusModel:
        return PolicyAxis(name=self.name,
                          desc=self.desc,
                          long_desc=self.long_desc,
                          reviewed=self.reviewed)

    def build_draft(self) -> "PolicyAxis":
        draft = super().build_draft()
        draft.processes.set(self.processes.all())
        draft.save()
        return draft

    def __str__(self):
        return f'{self.name} : {self.desc}'

    class Meta(StatusModel.Meta):
        verbose_name = _('Quality policy axis')
        verbose_name_plural = _('Quality policy axes')
        ordering = ['model_order']


class Contribution(models.Model):
    class Importance(models.TextChoices):
        MINOR = 'x', _('Minor')
        MAJOR = 'X', _('Major')

    process = models.ForeignKey(Process, on_delete=models.CASCADE)
    axis = models.ForeignKey(PolicyAxis, on_delete=models.CASCADE)
    importance = models.CharField(choices=Importance.choices,
                                  default=Importance.MINOR,
                                  max_length=1)

    def __str__(self):
        return f'{self.process} -> {self.axis}'

    class Meta:
        verbose_name = _('Contribution')
        verbose_name_plural = _('Contributions')


class Objective(models.Model):
    process = models.ForeignKey(Process, on_delete=models.CASCADE)
    name = models.SlugField(max_length=4)
    desc = models.CharField(max_length=64)
    long_desc = models.TextField()
    value = models.CharField(max_length=32)

    def __str__(self):
        return f'{self.process.name}-{self.name}'

    class Meta:
        verbose_name = _('Objective')
        verbose_name_plural = _('Objectives')
        ordering = ['process__name', 'name']

"""Models for the processes app"""
# pylint: disable=missing-class-docstring
# pylint: disable=too-few-public-methods
import datetime

from django.db import models
from django.db.models import Q, F
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _
from django.utils import timezone


# Ensure using the current User model
User = get_user_model()


# Create your models here.
class StatusModel(models.Model):
    class Status(models.IntegerChoices):
        DRAFT = 0, _('Draft')
        APPLICABLE = 1, _('Applicable')
        RETIRED = 2, _('Retired')

    status = models.SmallIntegerField(choices=Status.choices,
                                      default=Status.DRAFT)
    start_date = models.DateField(default=datetime.date.today)
    end_date = models.DateField(null=True, blank=True)

    def retire(self, end_date: datetime.date = None) -> None:
        """Pass a model to the retired state"""
        if end_date is None:
            end_date = datetime.date.today()
        self.status = StatusModel.Status.RETIRED
        self.end_date = end_date
        self.save()

    def build_draft(self) -> "StatusModel":
        """Builds a draft copy of self
        (expected to be overridden in subclasses)
        """
        raise NotImplementedError()

    def make_applicable(self) -> None:
        """Pass a draft into applicable state"""
        # search for a previous version
        # pylint: disable=no-member
        prevs = self.__class__.objects.filter(
            name=self.name, status=StatusModel.Status.APPLICABLE)
        if prevs:
            prevs[0].retire()
        self.status = StatusModel.Status.APPLICABLE

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


class Process(StatusModel):
    name = models.SlugField(max_length=8)
    desc = models.TextField()
    pilots = models.ManyToManyField(to=User)

    def build_draft(self) -> "Process":
        draft = Process.objects.create(name=self.name, desc=self.desc)
        draft.pilots.set(self.pilots.all())
        return draft

    def __str__(self):
        return str(self.name)

    class Meta(StatusModel.Meta):
        verbose_name = _('Process')
        verbose_name_plural = _('Processes')
        permissions = [('is_qm', _('Quality manager'))]


class PolicyAxis(StatusModel):
    name = models.SlugField(max_length=4)
    desc = models.CharField(max_length=64)
    long_desc = models.TextField()
    reviewed = models.DateField(default=timezone.now)
    processes = models.ManyToManyField(to=Process, through="Contribution")

    def build_draft(self) -> "PolicyAxis":
        draft = PolicyAxis.objects.create(name=self.name,
                                          desc=self.desc,
                                          long_desc=self.long_desc,
                                          reviewed=self.reviewed)
        draft.processes.set(self.processes.all())
        return draft

    def __str__(self):
        return f'{self.name} : {self.desc}'

    class Meta:
        verbose_name = _('Quality policy axis')
        verbose_name_plural = _('Quality policy axes')


class Contribution(models.Model):
    class Importance(models.TextChoices):
        MINOR = 'x', _('Minor')
        MAJOR = 'X', _('Major')

    process = models.ForeignKey(Process, on_delete=models.CASCADE)
    axis = models.ForeignKey(PolicyAxis, on_delete=models.CASCADE)
    importance = models.CharField(choices=Importance.choices,
                                  default=Importance.MINOR,
                                  max_length=1)

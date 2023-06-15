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

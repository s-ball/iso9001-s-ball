"""Models for the processes app"""
# pylint: disable=missing-class-docstring
# pylint: disable=too-few-public-methods
import datetime
from django.db import models
from django.db.models import Q, F
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _


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
        verbose_name_plural = _('Process')
        permissions = [('is_qm', _('Quality manager'))]

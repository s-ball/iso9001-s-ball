"""Views for the core app"""
from typing import Any, Dict
from django.http import HttpResponse
from django.shortcuts import render
from django.views import generic
from django.utils.translation import gettext as _
from .models import Process, PolicyAxis


# Create your views here.
def home(request) -> HttpResponse:
    """The top level index view"""
    return render(request, 'core/index.html')


class ProcessesList(generic.ListView):
    """List processes.

    By default, only applicable processes are available.
    """
    queryset = Process.objects.filter(status=Process.Status.APPLICABLE)

    def get_context_data(self, **kwargs: Any) -> Dict[str, Any]:
        """Add a title to context_data"""
        context = super().get_context_data(**kwargs)
        context['title'] = _('Processes')
        return context


class AxesList(generic.ListView):
    """List quality axes.

    By default, only applicable axes are available.
    """
    model = PolicyAxis
    template_name = 'core/process_list.html'

    def get_context_data(self, **kwargs: Any) -> Dict[str, Any]:
        """Add a title to context_data"""
        context = super().get_context_data(**kwargs)
        context['title'] = _('Policy axes')
        return context

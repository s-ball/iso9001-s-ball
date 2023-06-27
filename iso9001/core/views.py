"""Views for the core app"""
from typing import Any, Dict
from django.http import HttpResponse
from django.shortcuts import render
from django.views import generic
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.utils.translation import gettext as _
from .models import Process, PolicyAxis, Contribution


# Create your views here.
def home(request) -> HttpResponse:
    """The top level index view"""
    return render(request, 'core/index.html')


class ProcessesList(PermissionRequiredMixin, generic.ListView):
    """List processes.

    By default, only applicable processes are available.
    """
    permission_required = "core.view_process"
    queryset = Process.objects.filter(status=Process.Status.APPLICABLE)

    def get_context_data(self, **kwargs: Any) -> Dict[str, Any]:
        """Add a title to context_data"""
        context = super().get_context_data(**kwargs)
        context['title'] = _('Processes')
        return context


class AxesList(PermissionRequiredMixin, generic.ListView):
    """List quality axes.

    By default, only applicable axes are available.
    """
    queryset = PolicyAxis.objects.filter(status=Process.Status.APPLICABLE)
    template_name = 'core/process_list.html'
    permission_required = 'core.view_policyaxis'

    def get_context_data(self, **kwargs: Any) -> Dict[str, Any]:
        """Add a title to context_data"""
        context = super().get_context_data(**kwargs)
        context['title'] = _('Quality axes')
        return context


class ContributionsList(PermissionRequiredMixin, generic.base.TemplateView):
    """Show the contributions of processes to axes"""
    permission_required = ['core.view_process', 'core.view_policyaxis']
    template_name = 'core/contribution_list.html'

    def get_context_data(self, **kwargs: Any) -> Dict[str, Any]:
        """Give the list of processes and their contributions"""

        def contrib(process: Process, axis: PolicyAxis) -> str:
            """Give X for major contrib, and x for minor one"""
            cont = Contribution.objects.filter(
                process=process, axis=axis,
            )
            if len(cont) == 0:
                return ''
            return ('X' if cont[0].importance == Contribution.Importance.MAJOR
                    else 'x')

        context = super().get_context_data(**kwargs)
        context['title'] = _('Contributions')
        axes = PolicyAxis.objects.filter(status=Process.Status.APPLICABLE)
        processes = Process.objects.filter(status=Process.Status.APPLICABLE)
        context['table_headers'] = [str(axis) for axis in axes]
        context['object_list'] = {str(process):
                                  [contrib(process, axis) for axis in axes]
                                  for process in processes
                                  } if len(axes) > 0 else None
        return context

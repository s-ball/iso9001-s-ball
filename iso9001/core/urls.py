"""URL configuration for core app."""
from django.urls import path
from . import views


urlpatterns = [
    path('', views.home, name='home'),
    path('process', views.ProcessesList.as_view(), name="processes"),
    path('axis', views.AxesList.as_view(), name="axes"),
    path('contribution', views.ContributionsList.as_view(),
         name="contributions"),
]

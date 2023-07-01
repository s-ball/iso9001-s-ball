"""Trivial context processor that injects the APP_VERSION into the context"""
from django.conf import settings


def set_version(request):
    """Just returns the APP_VERSION"""
    version = settings.APP_VERSION
    if len(version) > 12:
        version = version[:9] + '...'
    return {'APP_VERSION': settings.APP_VERSION,
            'DISPLAY_VERSION': version}

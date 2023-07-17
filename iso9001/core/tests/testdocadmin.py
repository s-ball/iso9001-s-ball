# Copyright s-ball 2023 - MIT license
"""Tests for the management of Document objects on the admin site"""

from unittest.mock import patch
from django.test import TestCase, Client, override_settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from core.models import Process, StatusModel
try:
    from bs4 import BeautifulSoup
except ImportError:
    BeautifulSoup = None

from .testmodels.testmemorystorage import newfile

User = get_user_model()
Status = StatusModel.Status


@override_settings(STORAGES={
    "default": {
        "BACKEND": "django.core.files.storage.memory.InMemoryStorage",
    },
    "staticfiles": {
        "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
    },
})
class TestDocAdmin(TestCase):
    """Tests for the DocAdmin class"""
    @classmethod
    def setUpTestData(cls) -> None:
        """Install 2 processes an 1 admin user and one authority"""
        cls.admin = User.objects.create_superuser(username='admin')
        cls.user2 = User.objects.create_user(username='user1')
        authorize = Permission.objects.get(
            content_type__app_label='core', codename='authorize_document')
        cls.user2.user_permissions.add(authorize)
        cls.p1 = Process.objects.create(name='P1', desc='Prod 1')
        cls.p1.doc.pdf = newfile('docs/P1', 'P1')
        cls.p1.doc.authorize(cls.admin)
        cls.p1.make_applicable()
        cls.p2 = Process.objects.create(name='P2', desc='Prod 2')

    # def test_add_and_authorize(self) -> None:
    #     """Add a pdf doc and authorize it"""
    #     client = Client()
    #     client.force_login(self.admin)
    #     client.post()
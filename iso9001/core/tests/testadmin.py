"""Tests for the admin site"""

from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from core.models import Process, StatusModel
try:
    from bs4 import BeautifulSoup
except ImportError:
    BeautifulSoup = None

User = get_user_model()


class TestStatusModelAdmin(TestCase):
    """Tests for the StatusModelAdmin class"""
    @classmethod
    def setUpTestData(cls) -> None:
        """Install 4 processes an 1 admin user"""
        cls.admin = User.objects.create_superuser(username='admin')
        cls.p1 = Process.objects.create(name='P1', desc='Prod 1')
        cls.p2 = Process.objects.create(name='P2', desc='Prod 2')
        cls.p3 = Process.objects.create(name='P3', desc='Prod 3')
        cls.p4 = Process.objects.create(name='P4', desc='Prod 4')

    def test_connect(self) -> None:
        """Just a simple connection to the admin site"""
        client = Client()
        client.force_login(self.admin)
        resp = client.get('/en/admin/core/process/')
        self.assertEqual(200, resp.status_code)

    def test_make_applicable_2(self) -> None:
        """Make p2 and p4 applicable"""
        client = Client()
        client.force_login(self.admin)
        self.p4.doc.authorize(self.admin)
        self.p2.doc.authorize(self.admin)
        self.p2.save()
        resp = client.post('/en/admin/core/process/',
                           {'action': 'make_applicable',
                            'select_across': '0',
                            'index': '0',
                            '_selected_action': [
                                str(self.p2.pk),
                                str(self.p4.pk),
                            ],
                            },
                           follow=True)
        self.assertEqual(200, resp.status_code)
        self.p1.refresh_from_db()
        self.p2.refresh_from_db()
        self.p3.refresh_from_db()
        self.p4.refresh_from_db()
        self.assertEqual(StatusModel.Status.APPLICABLE, self.p2.status)
        self.assertEqual(StatusModel.Status.APPLICABLE, self.p4.status)
        self.assertEqual(StatusModel.Status.DRAFT, self.p1.status)
        self.assertEqual(StatusModel.Status.DRAFT, self.p3.status)
        if BeautifulSoup:
            soup = BeautifulSoup(resp.content, 'html.parser')
            msgs = soup.find('ul', attrs={'class': 'messagelist'})
            self.assertIsNone(msgs.find('li', attrs={'class': 'warning'}))
            self.assertTrue(msgs.find('li', attrs={'class': 'success'}
                                      ).text.startswith('2'))

    def test_make_applicable_1(self) -> None:
        """Make p2 and p4 applicable when p2 already is.

        Only 1 process should change
        """
        client = Client()
        client.force_login(self.admin)
        self.p2.doc.authorize(self.admin)
        self.p2.make_applicable()
        self.p4.doc.authorize(self.admin)
        resp = client.post('/en/admin/core/process/',
                           {'action': 'make_applicable',
                            'select_across': '0',
                            'index': '0',
                            '_selected_action': [
                                str(self.p2.pk),
                                str(self.p4.pk),
                            ],
                            },
                           follow=True)
        self.assertEqual(200, resp.status_code)
        self.p1.refresh_from_db()
        self.p2.refresh_from_db()
        self.p3.refresh_from_db()
        self.p4.refresh_from_db()
        self.assertEqual(StatusModel.Status.APPLICABLE, self.p2.status)
        self.assertEqual(StatusModel.Status.APPLICABLE, self.p4.status)
        self.assertEqual(StatusModel.Status.DRAFT, self.p1.status)
        self.assertEqual(StatusModel.Status.DRAFT, self.p3.status)
        if BeautifulSoup:
            soup = BeautifulSoup(resp.content, 'html.parser')
            msgs = soup.find('ul', attrs={'class': 'messagelist'})
            self.assertIsNone(msgs.find('li', attrs={'class': 'warning'}))
            self.assertTrue(msgs.find('li', attrs={'class': 'success'}
                                      ).text.startswith('1'))

    def test_make_applicable_0(self) -> None:
        """Make p2 and p4 applicable when they already are.

        No process should change, so we should get a warning message
        """
        client = Client()
        client.force_login(self.admin)
        self.p2.doc.authorize(self.admin)
        self.p2.make_applicable()
        self.p4.doc.authorize(self.admin)
        self.p4.make_applicable()
        resp = client.post('/en/admin/core/process/',
                           {'action': 'make_applicable',
                            'select_across': '0',
                            'index': '0',
                            '_selected_action': [
                                str(self.p2.pk),
                                str(self.p4.pk),
                            ],
                            },
                           follow=True)
        self.assertEqual(200, resp.status_code)
        if BeautifulSoup:
            soup = BeautifulSoup(resp.content, 'html.parser')
            msgs = soup.find('ul', attrs={'class': 'messagelist'})
            self.assertIsNone(msgs.find('li', attrs={'class': 'success'}))
            self.assertTrue(msgs.find('li', attrs={'class': 'warning'}
                                      ).text.startswith('0'))

    def test_retire_1(self) -> None:
        """Retire p1 and p3 when p1 is draft.

        Only 1 process should change
        """
        client = Client()
        client.force_login(self.admin)
        self.p3.doc.authorize(self.admin)
        self.p3.make_applicable()
        resp = client.post('/en/admin/core/process/',
                           {'action': 'retire',
                            'select_across': '0',
                            'index': '0',
                            '_selected_action': [
                                str(self.p1.pk),
                                str(self.p3.pk),
                            ],
                            },
                           follow=True)
        self.assertEqual(200, resp.status_code)
        self.p1.refresh_from_db()
        self.p2.refresh_from_db()
        self.p3.refresh_from_db()
        self.p4.refresh_from_db()
        self.assertEqual(StatusModel.Status.DRAFT, self.p1.status)
        self.assertEqual(StatusModel.Status.DRAFT, self.p2.status)
        self.assertEqual(StatusModel.Status.RETIRED, self.p3.status)
        self.assertEqual(StatusModel.Status.DRAFT, self.p4.status)
        if BeautifulSoup:
            soup = BeautifulSoup(resp.content, 'html.parser')
            msgs = soup.find('ul', attrs={'class': 'messagelist'})
            self.assertIsNone(msgs.find('li', attrs={'class': 'warning'}))
            self.assertTrue(msgs.find('li', attrs={'class': 'success'}
                                      ).text.startswith('1'))

    def test_build_draft(self) -> None:
        """Builds a draft from an applicable process"""
        client = Client()
        client.force_login(self.admin)
        self.p1.doc.authorize(self.admin)
        self.p1.make_applicable()
        self.p1.pilots.add(self.admin)
        resp = client.post('/en/admin/core/process/',
                           {'action': 'build_draft',
                            'select_across': '0',
                            'index': '0',
                            '_selected_action': str(self.p1.pk)
                            },
                           follow=True)
        self.assertEqual(200, resp.status_code)
        self.p1.refresh_from_db()
        self.p2.refresh_from_db()
        self.p3.refresh_from_db()
        self.p4.refresh_from_db()
        self.assertEqual(StatusModel.Status.APPLICABLE, self.p1.status)
        self.assertEqual(StatusModel.Status.DRAFT, self.p2.status)
        self.assertEqual(StatusModel.Status.DRAFT, self.p3.status)
        self.assertEqual(StatusModel.Status.DRAFT, self.p4.status)
        if BeautifulSoup:
            soup = BeautifulSoup(resp.content, 'html.parser')
            msgs = soup.find('ul', attrs={'class': 'messagelist'})
            self.assertIsNone(msgs.find('li', attrs={'class': 'warning'}))
            self.assertTrue(msgs.find('li', attrs={'class': 'success'}
                                      ).text.startswith('1'))
            new = Process.objects.get(name='P1',
                                      status=StatusModel.Status.DRAFT)
            self.assertEqual(self.p1.desc, new.desc)
            self.assertEqual({self.admin}, set(new.pilots.all()))

    def test_add_permission_ko(self) -> None:
        """Ensure add permission is required to build drafts"""
        user1 = User.objects.create_user(username='user1', is_staff=True)
        view_process = Permission.objects.get(
            content_type__app_label='core',
            content_type__model='process',
            codename='view_process',
        )
        user1.user_permissions.add(view_process)
        client = Client()
        client.force_login(user1)
        resp = client.post('/en/admin/core/process/',
                           {'action': 'build_draft',
                            'select_across': '0',
                            'index': '0',
                            '_selected_action': str(self.p1.pk)
                            },
                           follow=True)
        self.assertEqual(200, resp.status_code)
        self.assertEqual(1, len(Process.objects.filter(name=self.p1.name)))

    def test_add_permission_ok(self) -> None:
        """Ensure add permission is required to build drafts"""
        user1 = User.objects.create_user(username='user1', is_staff=True)
        add_process = Permission.objects.get(
            content_type__app_label='core',
            content_type__model='process',
            codename='add_process',
        )
        view_process = Permission.objects.get(
            content_type__app_label='core',
            content_type__model='process',
            codename='view_process',
        )
        user1.user_permissions.add(add_process, view_process)
        user1.save()
        user1.refresh_from_db()
        self.assertTrue(user1.has_perm('core.add_process'))
        self.p1.doc.authorize(self.admin)
        self.p1.make_applicable()
        client = Client()
        client.force_login(user1)
        resp = client.post('/en/admin/core/process/',
                           {'action': 'build_draft',
                            'select_across': '0',
                            'index': '0',
                            '_selected_action': str(self.p1.pk)
                            },
                           follow=True)
        self.assertEqual(200, resp.status_code)
        self.assertEqual(2, len(Process.objects.filter(name=self.p1.name)))

    def test_status_permission_ko(self) -> None:
        """Ensure is_qm permission is required for make_applicable"""
        user1 = User.objects.create_user(username='user1', is_staff=True)
        view_process = Permission.objects.get(
            content_type__app_label='core',
            content_type__model='process',
            codename='view_process',
        )
        user1.user_permissions.add(view_process)
        client = Client()
        client.force_login(user1)
        resp = client.post('/en/admin/core/process/',
                           {'action': 'make_applicable',
                            'select_across': '0',
                            'index': '0',
                            '_selected_action': str(self.p1.pk)
                            },
                           follow=True)
        self.assertEqual(200, resp.status_code)
        self.p1.refresh_from_db()
        self.assertEqual(StatusModel.Status.DRAFT, self.p1.status)

    def test_status_permission_ok(self) -> None:
        """Ensure is_qm permission is required for make_applicable"""
        user1 = User.objects.create_user(username='user1', is_staff=True)
        is_qm = Permission.objects.get(
            content_type__app_label='core',
            content_type__model='process',
            codename='is_qm',
        )
        view_process = Permission.objects.get(
            content_type__app_label='core',
            content_type__model='process',
            codename='view_process',
        )
        user1.user_permissions.add(is_qm, view_process)
        user1.save()
        user1.refresh_from_db()
        self.assertTrue(user1.has_perm('core.is_qm'))
        client = Client()
        client.force_login(user1)
        self.p1.doc.authorize(self.admin)
        self.p1.save()
        resp = client.post('/en/admin/core/process/',
                           {'action': 'make_applicable',
                            'select_across': '0',
                            'index': '0',
                            '_selected_action': str(self.p1.pk)
                            },
                           follow=True)
        self.assertEqual(200, resp.status_code)
        self.p1.refresh_from_db()
        self.assertEqual(StatusModel.Status.APPLICABLE, self.p1.status)

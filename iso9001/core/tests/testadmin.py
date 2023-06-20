"""Tests for the admin site"""

from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from core.models import Process, StatusModel
from bs4 import BeautifulSoup


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
        resp = client.get('/admin/core/process/')
        self.assertEqual(200, resp.status_code)

    def test_make_applicable_2(self) -> None:
        """Make p2 and p4 applicable when p4 is retired"""
        client = Client()
        client.force_login(self.admin)
        self.p4.make_applicable()
        self.p4.retire()
        resp = client.post('/admin/core/process/',
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
        self.p2.make_applicable()
        resp = client.post('/admin/core/process/',
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
        self.p2.make_applicable()
        self.p4.make_applicable()
        resp = client.post('/admin/core/process/',
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
        self.p3.make_applicable()
        resp = client.post('/admin/core/process/',
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
        soup = BeautifulSoup(resp.content, 'html.parser')
        msgs = soup.find('ul', attrs={'class': 'messagelist'})
        self.assertIsNone(msgs.find('li', attrs={'class': 'warning'}))
        self.assertTrue(msgs.find('li', attrs={'class': 'success'}
                                  ).text.startswith('1'))

    def test_build_draft(self) -> None:
        """Builds a draft from an applicable process"""
        client = Client()
        client.force_login(self.admin)
        self.p1.make_applicable()
        self.p1.pilots.add(self.admin)
        resp = client.post('/admin/core/process/',
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
        soup = BeautifulSoup(resp.content, 'html.parser')
        msgs = soup.find('ul', attrs={'class': 'messagelist'})
        self.assertIsNone(msgs.find('li', attrs={'class': 'warning'}))
        self.assertTrue(msgs.find('li', attrs={'class': 'success'}
                                  ).text.startswith('1'))
        new = Process.objects.get(name='P1', status=StatusModel.Status.DRAFT)
        self.assertEqual(self.p1.desc, new.desc)
        self.assertEqual({self.admin}, set(new.pilots.all()))

"""Tests for the admin site"""

from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.urls import reverse
from core.models import Process, StatusModel, PolicyAxis, Contribution
try:
    from bs4 import BeautifulSoup  # pyright: ignore reportMissingImports
except ImportError:
    import sys

    print("""
    *** WARNING ***
        =======
    BeautifulSoup is not installed, some tests will not be run
    """, file=sys.stderr)
    BeautifulSoup = None

User = get_user_model()


class TestViews(TestCase):
    """Test for core app views"""
    @classmethod
    def setUpTestData(cls) -> None:
        """Install 2 processes, 1 admin user and 1 normal user"""
        cls.admin = User.objects.create_superuser(username='admin')
        cls.user1 = User.objects.create_user(username='user1')
        cls.p1 = Process.objects.create(name='P1', desc='Prod 1',
                                        status=StatusModel.Status.APPLICABLE)
        cls.p2 = Process.objects.create(name='P2', desc='Prod 2')

    def test_base_not_connected(self) -> None:
        """Ensure menu contains a connection entry"""
        client = Client()
        resp = client.get(reverse('home'))
        self.assertEqual(200, resp.status_code)
        if BeautifulSoup:
            soup = BeautifulSoup(resp.content, 'html.parser')
            menu = soup.find(attrs={'id': 'menu'})
            url = reverse('login')
            atag = menu.css.select(f'a[href^="{url}"]')
            self.assertTrue('Connect' in atag[0].text)

    def test_base_connected(self) -> None:
        """Ensure menu contains the user name and no connection entry"""
        client = Client()
        client.force_login(self.user1)
        resp = client.get(reverse('home'))
        self.assertEqual(200, resp.status_code)
        if BeautifulSoup:
            soup = BeautifulSoup(resp.content, 'html.parser')
            menu = soup.find(attrs={'id': 'menu'})
            url = reverse('login')
            atag = menu.css.select(f'a[href^="{url}"]')
            self.assertEqual(0, len(atag))
            for tag in menu.find_all():
                if 'user1' in tag.text:
                    return
            self.fail('username not found in menu')

    def test_process_list(self) -> None:
        """Ensure that we get the applicable process"""
        client = Client()
        perm = Permission.objects.get(
            content_type__app_label='core',
            content_type__model='process',
            codename='view_process',
        )
        self.user1.user_permissions.add(perm)
        self.user1.save()
        client.force_login(self.user1)
        resp = client.get(reverse('processes'))
        self.assertEqual(200, resp.status_code)
        if BeautifulSoup:
            soup = BeautifulSoup(resp.content, 'html.parser')
            names = soup.findAll('th', attrs={'scope': 'row'})
            self.assertEqual(1, len(names))
            self.assertEqual('P1', names[0].text)

    def test_process_no_perm(self) -> None:
        """Ensure that view_process permission is required"""
        client = Client()
        client.force_login(self.user1)
        resp = client.get(reverse('processes'))
        self.assertEqual(403, resp.status_code)

    def test_axes_list(self) -> None:
        """Ensure that we can list applicable axes"""
        PolicyAxis.objects.create(name='A1', desc='Axe 1',
                                       status=StatusModel.Status.APPLICABLE)
        PolicyAxis.objects.create(name='A2', desc='Axe 2')
        PolicyAxis.objects.create(name='A3', desc='Axe 3',
                                       status=StatusModel.Status.APPLICABLE)
        client = Client()
        perm = Permission.objects.get(
            content_type__app_label='core',
            content_type__model='policyaxis',
            codename='view_policyaxis',
        )
        self.user1.user_permissions.add(perm)
        self.user1.save()
        client.force_login(self.user1)
        resp = client.get(reverse('axes'))
        self.assertEqual(200, resp.status_code)
        if BeautifulSoup:
            soup = BeautifulSoup(resp.content, 'html.parser')
            names = soup.findAll('th', attrs={'scope': 'row'})
            self.assertEqual(2, len(names))
            self.assertEqual('A1', names[0].text)
            self.assertEqual('A3', names[1].text)


class TestContrib(TestCase):
    """Tests for the Contribution view"""
    @classmethod
    def setUpTestData(cls) -> None:
        """Install 3 processes, 3 axes and 1 user"""
        cls.user1 = User.objects.create_user(username='user1')
        cls.p1 = Process.objects.create(name='P1', desc='Prod 1',
                                        status=StatusModel.Status.APPLICABLE)
        cls.p2 = Process.objects.create(name='P2', desc='Prod 2')
        cls.p3 = Process.objects.create(name='P3', desc='Prod 3',
                                        status=StatusModel.Status.APPLICABLE)
        cls.a1 = PolicyAxis.objects.create(
            name='A1', desc='Axis 1', status=StatusModel.Status.APPLICABLE)
        cls.a2 = PolicyAxis.objects.create(name='A2', desc='Axis 2')
        cls.a3 = PolicyAxis.objects.create(
            name='A3', desc='Axis 3', status=StatusModel.Status.APPLICABLE)

    def test_no_perms(self) -> None:
        """Controls that permission are required to show the view"""
        client = Client()
        client.force_login(self.user1)
        resp = client.get(reverse('contributions'))
        self.assertEqual(403, resp.status_code)

    def test_only_applicable(self) -> None:
        """Controls that only objects in applicable state are shown"""
        perms = Permission.objects.filter(
            content_type__app_label='core',
            codename__startswith='view_',
        )
        self.user1.user_permissions.add(*(perm for perm in perms
                                          if perm.content_type.model
                                          != Contribution))
        client = Client()
        client.force_login(self.user1)
        resp = client.get(reverse('contributions'))
        self.assertEqual(200, resp.status_code)
        if BeautifulSoup:
            soup = BeautifulSoup(resp.content, 'html.parser')
            axes = soup.css.select('main thead > tr > th')
            self.assertEqual(3, len(axes))
            processes = soup.css.select('main tbody > tr > th')
            self.assertEqual(2, len(processes))

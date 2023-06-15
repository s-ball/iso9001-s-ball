"""Models tests"""

from django.contrib.auth.models import Permission
from django.test import TestCase
from core.models import Process, User


# Create your tests here.
class TestProcess(TestCase):
    """Tests for Process model"""
    @classmethod
    def setUpTestData(cls) -> None:
        """Install some users: one QM and 2 others"""
        cls.qm = User.objects.create(username='QM')
        cls.user1 = User.objects.create(username='User1')
        cls.user2 = User.objects.create(username='User2')
        is_qm = Permission.objects.get(codename='is_qm',
                                       content_type__app_label='core')
        cls.qm.user_permissions.add(is_qm)

    def test_perms(self) -> None:
        """Controls permission assignment"""
        self.assertTrue(self.qm.has_perm('core.is_qm'))
        self.assertFalse(self.user1.has_perm('core.is_qm'))

    def test_pilot(self) -> None:
        """Try to setup a process and a pilot"""
        proc = Process.objects.create(name='P1',
                                      desc='Produce something')
        proc.pilots.add(self.user1)
        proc.save()
        self.assertTrue(proc in self.user1.process_set.all())

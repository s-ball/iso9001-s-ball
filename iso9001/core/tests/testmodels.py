"""Models tests"""

from django.contrib.auth.models import Permission
from django.test import TestCase
from core.models import Process, User, PolicyAxis, Contribution


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


class TestAxes(TestCase):
    """Tests for the PolicyAxis and Contribution models"""
    @classmethod
    def setUpTestData(cls) -> None:
        """Install 1 process and 2 axes"""
        cls.proc = Process.objects.create(name='P1',
                                          desc='Produce something')
        cls.axis1 = PolicyAxis.objects.create(name='A1',
                                              desc='Axis 1')
        cls.axis2 = PolicyAxis.objects.create(name='A2',
                                              desc='Axis 2')

    def test_default(self) -> None:
        """Controls that adding a new axe sets a minor contribution"""
        self.axis1.processes.add(self.proc)
        contrib = Contribution.objects.get(process=self.proc, axis=self.axis1)
        self.assertEqual(Contribution.Importance.MINOR, contrib.importance)

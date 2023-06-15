"""Models tests"""

from django.contrib.auth.models import Permission
from django.db import IntegrityError
from django.test import TestCase
from core.models import Process, User, PolicyAxis, Contribution, StatusModel


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

    def test_build_draft(self) -> None:
        """Try to build a draft copy"""
        proc = Process.objects.create(name='P1',
                                      desc='Produce something',
                                      status=StatusModel.Status.APPLICABLE)
        proc.pilots.add(self.user1)
        proc.pilots.add(self.qm)
        proc.save()
        draft = proc.build_draft()
        self.assertEqual(StatusModel.Status.DRAFT, draft.status)
        self.assertTrue(self.qm in draft.pilots.all())

    def test_applicable_new(self) -> None:
        """Make applicable a new Process model"""
        proc = Process.objects.create(name='P1',
                                      desc='Produce something')
        proc.make_applicable()
        self.assertEqual(StatusModel.Status.APPLICABLE, proc.status)

    def test_applicable_new_version(self) -> None:
        """Build a draft on an applicable Process and make it applicable."""
        proc = Process.objects.create(name='P1',
                                      desc='Produce something',
                                      status=StatusModel.Status.APPLICABLE)
        proc.pilots.add(self.user1)
        proc.pilots.add(self.qm)
        draft = proc.build_draft()
        draft.make_applicable()
        # make applicable changed proc in database only...
        proc.refresh_from_db()
        self.assertEqual(StatusModel.Status.RETIRED, proc.status)
        self.assertEqual(StatusModel.Status.APPLICABLE, draft.status)

    def test_str(self) -> None:
        """Test __str__ special method"""
        proc = Process.objects.create(name='P1',
                                      desc='Produce something')
        self.assertEqual("P1", str(proc))


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
        cls.axis1.processes.add(cls.proc)

    def test_default(self) -> None:
        """Controls that adding a new axis sets a minor contribution"""
        contrib = Contribution.objects.get(process=self.proc, axis=self.axis1)
        self.assertEqual(Contribution.Importance.MINOR, contrib.importance)

    def test_build_draft(self) -> None:
        """Try to build a draft copy"""
        self.axis1.status = StatusModel.Status.APPLICABLE
        self.axis1.save()
        draft = self.axis1.build_draft()
        self.assertEqual(StatusModel.Status.DRAFT, draft.status)
        self.assertIn(self.proc, draft.processes.all())

    def test_str(self) -> None:
        """Test __str__ special method"""
        self.assertEqual('A1 : Axis 1', str(self.axis1))


class TestStatus(TestCase):
    """Tests for multiple version of a model"""
    @classmethod
    def setUpTestData(cls) -> None:
        """Initialize one process as DRAFT and one as APPLICABLE"""
        cls.p1 = Process.objects.create(name='P1', desc='Produce something')
        cls.p2 = Process.objects.create(name='P2', desc='Produce nothing',
                                        status=StatusModel.Status.APPLICABLE)

    def test_no_two_applicable(self) -> None:
        """Try to create an applicable copy"""
        with self.assertRaises(IntegrityError):
            Process.objects.create(name='P2', desc='Produce nothing',
                                   status=StatusModel.Status.APPLICABLE)

    def test_draft_copy(self) -> None:
        """Create a draft copy"""
        p21 = Process.objects.create(name='P2', desc='Produce nothing')
        self.assertNotEqual(p21.pk, self.p2.pk)

    def test_change_applicable(self) -> None:
        """Retire a process and create a new applicable one"""
        self.p2.status = StatusModel.Status.RETIRED
        self.p2.save()
        p21 = Process.objects.create(name='P2', desc='Produce nothing',
                                     status=StatusModel.Status.APPLICABLE)
        self.assertNotEqual(p21.pk, self.p2.pk)

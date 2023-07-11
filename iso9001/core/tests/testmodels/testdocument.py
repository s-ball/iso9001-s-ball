"""Models tests"""
from unittest.mock import patch
from django.contrib.auth.models import Permission
from django.db import IntegrityError
from django.test import TestCase
from core.models import Process, User, Document, StatusModel


DRAFT = StatusModel.Status.DRAFT
APPLICABLE = StatusModel.Status.APPLICABLE
RETIRED = StatusModel.Status.RETIRED
AUTHORIZED = StatusModel.Status.AUTHORIZED


# Create your tests here.

# the patch allows not to care for setting a file in the documents
@patch('django.core.files.base.File.__bool__', lambda *args: True)
class TestDocument(TestCase):
    """Tests for the Document model"""
    @classmethod
    def setUpTestData(cls) -> None:
        """Create some users and get relevant permissions"""
        cls.is_qm = Permission.objects.get(codename='is_qm',
                                           content_type__app_label='core')
        cls.authorize = Permission.objects.get(
            codename='authorize_document',
            content_type__app_label='core',
        )
        # admin has "qm", user1 has authorize_document
        cls.admin = User.objects.create_user(username='admin')
        cls.admin.user_permissions.add(cls.is_qm)
        cls.user1 = User.objects.create_user(username='user1')
        cls.user1.user_permissions.add(cls.authorize)

    def test_draft_from_valid_retired(self) -> None:
        """Build a retired process, and make an applicable version of it"""
        proc1 = Process.objects.create(name='P1', desc='.', status=RETIRED)
        proc1.doc = Document.objects.create(name='main', process=proc1,
                                            status=RETIRED)
        proc2 = proc1.build_draft()
        # ensure a draft copy of the document was made
        self.assertEqual(proc1.doc, proc2.doc.previous)
        proc2.doc.authorize(self.user1)
        proc2.make_applicable()
        self.assertEqual(APPLICABLE, proc2.status)
        self.assertEqual(APPLICABLE, proc2.doc.status)

    def test_draft_from_invalid_retired(self) -> None:
        """Build a retired process, with a successor, and try a second one"""
        proc1 = Process.objects.create(name='P1', desc='.', status=RETIRED)
        proc1.doc = Document.objects.create(name='main', process=proc1,
                                            status=RETIRED)
        proc2 = proc1.build_draft()
        proc2.doc.authorize(self.user1)
        proc2.make_applicable()
        with self.assertRaises(IntegrityError):
            proc1.build_draft()

    def test_draft_from_applicable(self) -> None:
        """Build an applicable process, and make an new version of it"""
        proc1 = Process.objects.create(name='P1', desc='.', status=APPLICABLE)
        proc1.doc = Document.objects.create(name='main', process=proc1,
                                            status=APPLICABLE)
        proc2 = proc1.build_draft()
        # ensure a draft copy of the document was made
        self.assertEqual(proc1.doc, proc2.doc.previous)
        proc2.doc.authorize(self.user1)
        proc2.make_applicable()
        self.assertEqual(APPLICABLE, proc2.status)
        self.assertEqual(APPLICABLE, proc2.doc.status)
        self.assertEqual(RETIRED, proc1.status)
        self.assertEqual(RETIRED, proc1.doc.status)

    def test_revert(self) -> None:
        """Revert an authorization"""
        proc = Process.objects.create(name='P1', desc='.')
        proc.doc.authorize(self.user1)
        self.assertEqual(AUTHORIZED, proc.doc.status)
        proc.doc.revert()
        self.assertEqual(DRAFT, proc.doc.status)

    def test_wrong_revert(self) -> None:
        """Revert an authorization"""
        proc = Process.objects.create(name='P1', desc='.')
        with self.assertRaises(ValueError):
            proc.doc.revert()

    def test_make_applicable_wrong_process(self) -> None:
        """Call make_applicable while process is not"""
        proc = Process.objects.create(name='P1', desc='.')
        proc.doc.authorize(self.user1)
        with self.assertRaises(ValueError):
            proc.doc.make_applicable()

    def test_make_applicable_wrong_parent(self) -> None:
        """Call make_applicable with no applicable parent"""
        proc = Process.objects.create(name='P1', desc='.', status=APPLICABLE)
        doc1 = Document.objects.create(name='parent', process=proc)
        doc1.parents.add(proc.doc)
        doc1.authorize(self.user1)
        doc2 = Document.objects.create(name='child', process=proc)
        doc2.parents.add(doc1)
        # ensure doc1 can be made applicable
        doc1.make_applicable()
        doc1.retire(recurse=False)
        doc2.authorize(self.user1)
        # but doc2 cannot
        with self.assertRaises(ValueError):
            doc2.make_applicable()


@patch('django.core.files.base.File.__bool__', lambda *args: True)
class TestManyDocuments(TestCase):
    """Tests for the a process with a number of documents"""
    @classmethod
    def setUpTestData(cls) -> None:
        """Create some users and get relevant permissions"""
        cls.is_qm = Permission.objects.get(codename='is_qm',
                                           content_type__app_label='core')
        cls.authorize = Permission.objects.get(
            codename='authorize_document',
            content_type__app_label='core',
        )
        # admin has "qm", user1 has authorize_document
        cls.admin = User.objects.create_user(username='admin')
        cls.admin.user_permissions.add(cls.is_qm)
        cls.user1 = User.objects.create_user(username='user1')
        cls.user1.user_permissions.add(cls.authorize)
        # Build a process and some documents
        cls.proc = Process.objects.create(name='P1', desc='.',
                                          status=APPLICABLE)
        cls.proc.doc = Document.objects.create(
            name='Process', process=cls.proc, status=APPLICABLE)
        cls.doc1 = Document.objects.create(name='Doc1', process=cls.proc,
                                           status=APPLICABLE)
        cls.doc1.parents.add(cls.proc.doc)
        cls.doc2 = Document.objects.create(name='Doc2', process=cls.proc,
                                           status=APPLICABLE)
        cls.doc2.parents.add(cls.proc.doc)
        cls.doc11 = Document.objects.create(name='Doc11', process=cls.proc,
                                            status=APPLICABLE)
        cls.doc11.parents.add(cls.doc1)
        cls.doc12 = Document.objects.create(name='Doc12', process=cls.proc,
                                            status=APPLICABLE)
        cls.doc12.parents.add(cls.doc1)

    def test_build_draft(self) -> None:
        """Build a draft of the whole process"""
        proc2 = self.proc.build_draft()
        # ensure a draft copy of the document was made
        self.assertEqual(self.proc.doc, proc2.doc.previous)
        # ensure that copy inherited the child documents
        self.assertEqual([doc.pk for doc in self.proc.doc.children.all()],
                         [doc.pk for doc in proc2.doc.children.all()])

    def test_make_applicable_proc_one_child(self) -> None:
        """Build drafts from proc, doc2 and doc11 and authorize only doc2"""
        proc2 = self.proc.build_draft()
        proc2.doc.authorize(self.user1)
        draft2 = self.doc2.build_draft()
        draft2.authorize(self.user1)
        draft11 = self.doc11.build_draft()
        draft11.authorize(self.user1)
        proc2.make_applicable()
        self.assertTrue(APPLICABLE, proc2.doc.status)
        self.assertTrue(APPLICABLE, draft2.status)
        self.assertTrue(RETIRED, self.doc2.status)
        self.assertTrue(AUTHORIZED, draft11.status)

    def test_make_applicable_one_child(self) -> None:
        """Build drafts for main doc, doc2 and doc11 and authorize only doc2"""
        draft = self.proc.doc.build_draft()
        draft.authorize(self.user1)
        draft2 = self.doc2.build_draft()
        draft2.authorize(self.user1)
        draft11 = self.doc11.build_draft()
        draft11.authorize(self.user1)
        draft.make_applicable()
        self.assertTrue(APPLICABLE, draft.status)
        self.assertTrue(APPLICABLE, draft2.status)
        self.assertTrue(RETIRED, self.doc2.status)
        self.assertTrue(AUTHORIZED, draft11.status)

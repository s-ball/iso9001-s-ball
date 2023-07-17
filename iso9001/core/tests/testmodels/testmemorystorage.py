# Copyright s-ball 2023 - MIT license
"""Various test with specific storage back ends"""
import pathlib

from django.test import TestCase, override_settings
from django.core.files.storage import default_storage, FileSystemStorage
from django.core.files.storage.memory import InMemoryStorage
from django.core.files.base import ContentFile
from django.conf import settings

from core.models import Process, User


class DefaultStorageTest(TestCase):
    """Test usage of Storage"""
    def test_storage(self) -> None:
        """Ensure usage of file system storage"""
        self.assertIsInstance(default_storage, FileSystemStorage)


def newfile(name: str, content: bytes | str) -> str:
    """Creates a new file on the default storage"""
    name = default_storage.get_available_name(name)
    return default_storage.save(name, ContentFile(content))


@override_settings(STORAGES={
    "default": {
        "BACKEND": "django.core.files.storage.memory.InMemoryStorage",
    },
    "staticfiles": {
        "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
    },
})
class StorageTest(TestCase):
    """Test usage of Storage"""
    def test_storage(self) -> None:
        """Ensure usage of in memory storage"""
        self.assertIsInstance(default_storage, InMemoryStorage)

    def test_create_file(self) -> None:
        """Ensure that a in memory file does not exist on the file system"""
        file = default_storage.open('docs/foo.txt', 'w')
        file.write('foo\nbar\n')
        file.close()
        lsdir = default_storage.listdir(settings.MEDIA_ROOT)
        self.assertNotEqual(0, len(lsdir))
        self.assertTrue(default_storage.exists('docs/foo.txt'))
        root = pathlib.Path(settings.MEDIA_ROOT)
        self.assertTrue(root.exists())
        self.assertFalse((root / 'docs' / 'foo.txt').exists())

    def test_dummy_document(self) -> None:
        """Ensure that an in memory file is enough to authorize a Document"""
        pdf = newfile('docs/foo.txt', 'foo')
        admin = User.objects.create_superuser('admin')
        proc = Process.objects.create(name='P1', desc='.')
        proc.doc.pdf = pdf
        self.assertTrue(proc.doc.pdf)
        proc.doc.authorize(admin)
        self.assertEqual(admin, proc.doc.autority)

    def test_no_doc(self) -> None:
        """Ensure that authorizing a document with no pdf file raises"""
        admin = User.objects.create_superuser('admin')
        proc = Process.objects.create(name='P1', desc='.')
        self.assertFalse(proc.doc.pdf)
        with self.assertRaises(ValueError):
            proc.doc.authorize(admin)

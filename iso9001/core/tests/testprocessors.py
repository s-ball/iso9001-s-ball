"""Tests for the context processor adding the version into a request"""
from unittest.mock import patch
from django.test import TestCase

from core import context_processor


class TestVersionProcessor(TestCase):
    """Controls that a correct version is returned"""
    def test_short_version(self) -> None:
        """For a short version"""
        given = "1.2.3"
        with patch.object(context_processor.settings, "APP_VERSION", given):
            versions = context_processor.set_version(None)
            self.assertEqual(given, versions['APP_VERSION'])
            self.assertEqual(given, versions['DISPLAY_VERSION'])

    def test_long_version(self) -> None:
        """For a short version"""
        given = "1.2.3dev4.5.6.7"
        with patch.object(context_processor.settings, "APP_VERSION", given):
            versions = context_processor.set_version(None)
            self.assertEqual(given, versions['APP_VERSION'])
            self.assertNotEqual(given, versions['DISPLAY_VERSION'])
            self.assertEqual(given[:9], versions['DISPLAY_VERSION'][:9])
            self.assertEqual('...', versions['DISPLAY_VERSION'][9:])

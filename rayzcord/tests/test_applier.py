"""Unit tests for the server style applier utility methods."""

import unittest
from rayzcord.rayzcserve.applier import ServerStyleApplier


class TestApplierSanitization(unittest.TestCase):
    """Validates channel and role name sanitization logic."""

    def test_text_channel_formatting(self):
        """Ensure spaces become hyphens for text channels."""
        raw = "My General Chat Room"
        cleaned = ServerStyleApplier.clean_channel_name(raw, is_text_channel=True)
        self.assertEqual(cleaned, "My-General-Chat-Room")

    def test_voice_channel_formatting(self):
        """Ensure spaces are preserved for voice channels."""
        raw = "Lounge Room 1"
        cleaned = ServerStyleApplier.clean_channel_name(raw, is_text_channel=False)
        self.assertEqual(cleaned, "Lounge Room 1")

    def test_length_boundary(self):
        """Ensure names are truncated to 100 characters."""
        oversized = "a" * 150
        cleaned = ServerStyleApplier.clean_channel_name(oversized)
        self.assertEqual(len(cleaned), 100)


if __name__ == "__main__":
    unittest.main()

"""Unit tests for the RayzCServe Unicode font engine."""

import unittest
from rayzcord.rayzcserve.fonts import FONTS, format_font_page, get_font


class TestFontEngine(unittest.TestCase):
    """Validates the font transformation catalog and pagination."""

    def test_total_fonts_count(self):
        """Ensure there are at least 100 configured font styles."""
        self.assertGreaterEqual(len(FONTS), 100)

    def test_font_retrieval(self):
        """Ensure every font can be retrieved by 1-based ID."""
        for font_id in range(1, len(FONTS) + 1):
            font = get_font(font_id)
            self.assertIsNotNone(font, f"Font #{font_id} was not retrieved.")
            self.assertEqual(font.font_id, font_id)
            self.assertTrue(len(font.name) > 0)

    def test_font_transformations(self):
        """Ensure each font executes a transformation without crashing."""
        sample_text = "General Chat 123"
        for font in FONTS:
            transformed = font.transform(sample_text)
            self.assertIsInstance(transformed, str)
            self.assertTrue(len(transformed) > 0, f"Font #{font.font_id} produced empty output.")

    def test_font_pagination(self):
        """Ensure font page formatting produces valid text for pages 1 to 11."""
        for page in range(1, 12):
            rendered = format_font_page(page_number=page, per_page=10, sample_text="rules")
            self.assertIn("Available Fonts", rendered)
            self.assertIn(f"Page {page}/", rendered)


if __name__ == "__main__":
    unittest.main()

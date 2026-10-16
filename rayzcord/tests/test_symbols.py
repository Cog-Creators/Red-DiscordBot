"""Unit tests for the RayzCServe symbol and border engine."""

import unittest
from rayzcord.rayzcserve.symbols import SYMBOLS, format_symbols_page, get_symbol


class TestSymbolEngine(unittest.TestCase):
    """Validates the symbol and border formatting engine."""

    def test_total_symbols_count(self):
        """Ensure symbols are loaded."""
        self.assertGreaterEqual(len(SYMBOLS), 20)

    def test_symbol_retrieval(self):
        """Ensure each symbol can be retrieved by ID."""
        for sym_id in range(1, len(SYMBOLS) + 1):
            sym = get_symbol(sym_id)
            self.assertIsNotNone(sym, f"Symbol #{sym_id} was not retrieved.")
            self.assertEqual(sym.symbol_id, sym_id)

    def test_symbol_application(self):
        """Ensure formatting encloses input text properly."""
        sample = "announcements"
        for sym in SYMBOLS:
            result = sym.apply(sample)
            self.assertIn(sample, result, f"Symbol #{sym.symbol_id} lost original text.")

    def test_symbol_page_formatting(self):
        """Ensure symbol page formatter runs properly."""
        output = format_symbols_page(sample_text="welcome")
        self.assertIn("Available Symbols", output)
        brackets_only = format_symbols_page(category_filter="Brackets", sample_text="welcome")
        self.assertIn("Available Symbols", brackets_only)


if __name__ == "__main__":
    unittest.main()

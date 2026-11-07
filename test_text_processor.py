import unittest

from chechen_text_processor import ChechenTextProcessor


class HyphenTest(unittest.TestCase):
    def setUp(self):
        self.processor = ChechenTextProcessor()

    def test_keeps_compound_words(self):
        self.assertEqual(self.processor.extract_and_clean_words("гӏиллакх-оьздангалла"), ["гӏиллакх-оьздангалла"])

    def test_drops_hyphen_fragments(self):
        words = self.processor.extract_and_clean_words("ду- -а -- хетта-")
        self.assertFalse([w for w in words if w.startswith("-") or w.endswith("-")], words)


if __name__ == "__main__":
    unittest.main()

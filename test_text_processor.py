import unittest

from chechen_corpus_toolkit import ExportGenerator
from chechen_text_processor import ChechenTextProcessor
from review.generate_candidates import default_list


class HyphenTest(unittest.TestCase):
    def setUp(self):
        self.processor = ChechenTextProcessor()

    def test_keeps_compound_words(self):
        self.assertEqual(self.processor.extract_and_clean_words("гӏиллакх-оьздангалла"), ["гӏиллакх-оьздангалла"])

    def test_drops_hyphen_fragments(self):
        words = self.processor.extract_and_clean_words("ду- -а -- хетта-")
        self.assertFalse([w for w in words if w.startswith("-") or w.endswith("-")], words)


class ReviewCandidatesTest(unittest.TestCase):
    def test_default_lists(self):
        ru = {"для": 187, "хилла": 120, "кхин": 150}
        self.assertEqual(default_list("для", 2, ru), "drop")
        self.assertIsNone(default_list("хилла", 500, ru))  # frequent in Chechen
        self.assertIsNone(default_list("кхин", 1, ru))  # Chechen-only letters
        self.assertEqual(default_list("да", 50, ru), "keep")
        self.assertEqual(default_list("кх", 3, ru), "drop")


class AospExportTest(unittest.TestCase):
    def test_drops_tripled_letters(self):
        words = [w for w, _ in ExportGenerator.filter_keyman_words([("дааа", 5), ("ааа", 5), ("кхаа", 5)])]
        self.assertEqual(words, ["кхаа"])

    def test_frequencies_stay_in_normal_aosp_range(self):
        scaled = dict(ExportGenerator.map_to_aosp_frequencies([("а", 1000), ("ма", 10), ("хьо", 1)]))
        self.assertEqual((scaled["а"], scaled["хьо"]), (254, 15))
        self.assertTrue(15 < scaled["ма"] < 254)


if __name__ == "__main__":
    unittest.main()

import os
import tempfile
import unittest

from chechen_corpus_toolkit import ExportGenerator
from chechen_text_processor import ChechenTextProcessor


class HyphenTest(unittest.TestCase):
    def setUp(self):
        self.processor = ChechenTextProcessor()

    def test_keeps_compound_words(self):
        self.assertEqual(self.processor.extract_and_clean_words("гӏиллакх-оьздангалла"), ["гӏиллакх-оьздангалла"])

    def test_drops_hyphen_fragments(self):
        words = self.processor.extract_and_clean_words("ду- -а -- хетта-")
        self.assertFalse([w for w in words if w.startswith("-") or w.endswith("-")], words)


class BlacklistTest(unittest.TestCase):
    def test_review_tsv_blacklists_only_drop_rows(self):
        with tempfile.NamedTemporaryFile("w", suffix=".tsv", encoding="utf-8", delete=False) as f:
            f.write("word\tce_count\tru_f\tcategory\tdecision\nдля\t2\t187\trussian?\tdrop\nда\t9\t200\ttwo-letter\tkeep\n")
        processor = ChechenTextProcessor()
        processor.load_blacklist(f.name)
        os.unlink(f.name)
        self.assertEqual(processor.blacklisted_words, {"для"})


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

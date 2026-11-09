import unittest

from chechen_text_processor import ChechenTextProcessor
from russian_filter import CE, LOAN, RU, SWITCH, Lexicon, strip_russian, tag

RUSSIAN = {w: 150 for w in ("он", "сказал", "что", "знает", "правду", "не", "как", "воду", "глядел",
                             "университет", "телевизор")}
# "не", "как", "что", "воду" also occur in Chechen context, so only their neighbors can settle them
HOMOGRAPHS = {"не": 20, "как": 20, "что": 20, "воду": 20}
LEXICON = Lexicon(ru=RUSSIAN, ce=HOMOGRAPHS, ce_context=HOMOGRAPHS)


class WordRuleTest(unittest.TestCase):
    def test_chechen_letters(self):
        self.assertEqual(tag(["кхин"], LEXICON), [CE])

    def test_russian_stem_with_chechen_ending_is_loan(self):
        self.assertEqual(tag(["университетехь"], LEXICON), [LOAN])

    def test_russian_ending(self):
        self.assertEqual(tag(["красного"], LEXICON), [RU])

    def test_override_wins(self):
        lexicon = LEXICON._replace(overrides={"красного", "телевизор"})
        self.assertEqual(tag(["красного", "телевизор", "красного"], lexicon), [CE, LOAN, CE])


class ContextTest(unittest.TestCase):
    def test_homographs_in_russian_phrase(self):
        self.assertEqual(tag(["он", "не", "знает", "как", "сказал"], LEXICON), [RU] * 5)

    def test_homograph_in_chechen_phrase(self):
        self.assertEqual(tag(["тӏаьхьа", "воду", "хьо"], LEXICON), [CE] * 3)

    def test_lone_russian_word_is_switch(self):
        self.assertEqual(tag(["со", "телевизор", "хьоьжу"], LEXICON), [CE, SWITCH, CE])

    def test_russian_quote_removed_chechen_kept(self):
        clean, removed = strip_russian("Хьо дика ву. Он сказал, что знает правду. Со цӏа вогӏу, телевизор хьажа.",
                                       LEXICON)
        self.assertEqual(clean.split(), "Хьо дика ву. , . Со цӏа вогӏу, хьажа.".split())
        self.assertEqual(removed, [("он", RU), ("сказал", RU), ("что", RU), ("знает", RU), ("правду", RU),
                                   ("телевизор", SWITCH)])


class ProcessorTest(unittest.TestCase):
    def test_russian_absent_from_frequencies(self):
        processor = ChechenTextProcessor()
        processor.russian_lexicon = LEXICON
        frequencies = processor.process_corpus([{"text": "Хьо университетехь дика ву. Он сказал, что знает правду."}])
        self.assertEqual(set(frequencies), {"хьо", "университетехь", "дика", "ву"})
        self.assertEqual(processor.removed_russian[RU], 5)


if __name__ == "__main__":
    unittest.main()

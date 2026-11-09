"""Remove Russian from Chechen corpus text before word counting.

Self-contained and deterministic: word rules give each word a tag from the word alone,
sequence passes then settle the rest from context.

    clean_text, removed = strip_russian(text, lexicon)   # removed: [(word, RU | SWITCH), ...]
"""
import re
from collections import Counter
from functools import reduce
from pathlib import Path
from typing import Iterable, List, NamedTuple, Optional, Set, Tuple

CE, LOAN, SWITCH, RU, UNKNOWN = "CE", "LOAN", "SWITCH", "RU", "UNKNOWN"

DEFAULT_OVERRIDES = Path(__file__).parent / "keep_words.txt"

CHECHEN_MARKERS = ("ӏ", "кх", "къ", "хь", "аь", "оь", "уь", "юь", "яь", "гӏ", "еь")
# A native speaker must check both ending lists.
CHECHEN_ENDINGS = ("ашкахь", "ашна", "ашца", "ехь", "аца", "ера", "ийн", "аш", "ан", "ца", "на", "ах", "ин")
RUSSIAN_ENDINGS = ("ого", "ому", "ему", "ыми", "ями", "ами", "ость", "ться", "ешь", "ишь", "ется", "ются",
                   "ение", "ения", "ание", "ания", "ский", "ская", "ское", "ских", "ской", "ый", "ая", "ое",
                   "ые", "ых", "ую", "юю", "ть")

RU_COMMON = 100       # AOSP f (15-254) from which a Russian word counts as common
CE_RARE = 4           # corpus count up to which a word counts as rare in Chechen
CE_CONTEXT_SHARE = 0.2  # below this share of occurrences next to a Chechen-lettered word, a word is not Chechen
MIN_STEM = 3
CONTEXT_WINDOW = 3    # resolved neighbors looked at on each side of an UNKNOWN word
MIN_RU_SPAN = 3       # a shorter RU run inside a Chechen sentence is a SWITCH

_TOKEN = re.compile(r"[\w\-]+")
_SENTENCE = re.compile(r"[^.!?…\n]+")
_CYRILLIC = re.compile(r"[а-я]")
_FOLD = str.maketrans("i1ιіё", "ӏӏӏӏе")


class Lexicon(NamedTuple):
    ru: dict          # Russian word -> AOSP frequency
    ce: dict          # Chechen corpus word -> count, taken before filtering so slightly contaminated
    ce_context: dict  # same, counting only occurrences next to a word with Chechen-only letters
    overrides: Set[str] = frozenset()


def normalize(token: str) -> str:
    return token.lower().translate(_FOLD).strip("-")


def _has_chechen_letters(word: str) -> bool:
    return any(marker in word for marker in CHECHEN_MARKERS)


def _sentences(text: str):
    """Yield each sentence as [(start, end, normalized word)], skipping numbers and non-Cyrillic tokens."""
    for sentence in _SENTENCE.finditer(text):
        tokens = [(sentence.start() + m.start(), sentence.start() + m.end(), normalize(m.group()))
                  for m in _TOKEN.finditer(sentence.group())]
        yield [t for t in tokens if _CYRILLIC.search(t[2])]


def load_ru_frequencies(combined_path: str) -> dict:
    ru = {}
    with open(combined_path, encoding="utf-8") as f:
        for line in f:
            m = re.match(r"\s*word=([^,]+),f=(\d+)", line)
            if m:
                word = m.group(1).lower().replace("ё", "е")
                ru[word] = max(ru.get(word, 0), int(m.group(2)))
    return ru


def build_lexicon(ru_combined_path: str, texts: Iterable[str],
                  overrides_path: Optional[str] = DEFAULT_OVERRIDES) -> Lexicon:
    ce, ce_context = Counter(), Counter()
    for text in texts:
        for tokens in _sentences(text):
            words = [w for _, _, w in tokens]
            marked = [_has_chechen_letters(w) for w in words]
            for i, word in enumerate(words):
                ce[word] += 1
                ce_context[word] += any(marked[max(0, i - 1):i] + marked[i + 1:i + 2])
    overrides = set(Path(overrides_path).read_text(encoding="utf-8").split()) if overrides_path else set()
    return Lexicon(load_ru_frequencies(ru_combined_path), ce, ce_context, overrides)


# Word rules: (word, lexicon) -> tag | None

def override(word, lexicon):
    if word in lexicon.overrides:
        return LOAN if word in lexicon.ru else CE


def loan_with_chechen_ending(word, lexicon):
    if word in lexicon.ru:
        return None
    for ending in CHECHEN_ENDINGS:
        stem = word[:-len(ending)]
        if word.endswith(ending) and len(stem) >= MIN_STEM and stem in lexicon.ru:
            return LOAN


def chechen_letters(word, lexicon):
    if _has_chechen_letters(word):
        return CE


def russian_ending(word, lexicon):
    if any(word.endswith(e) and len(word) >= len(e) + MIN_STEM for e in RUSSIAN_ENDINGS):
        return RU


def common_russian_rare_chechen(word, lexicon):
    count = lexicon.ce.get(word, 0)
    if lexicon.ru.get(word, 0) >= RU_COMMON and (
            count <= CE_RARE or lexicon.ce_context.get(word, 0) < CE_CONTEXT_SHARE * count):
        return RU


def not_in_russian_wordlist(word, lexicon):
    if word not in lexicon.ru:
        return CE


# Order is priority. The loan rule runs before the letter rule so "университетехь" is LOAN, not CE.
WORD_RULES = [override, loan_with_chechen_ending, chechen_letters, russian_ending,
              common_russian_rare_chechen, not_in_russian_wordlist]


# Sequence passes: (words, tags) -> tags

def unknown_takes_neighbors(words, tags):
    """A homograph ("не", "воду") is Russian only when resolved Russian neighbors outnumber Chechen ones."""
    resolved = [(i, t) for i, t in enumerate(tags) if t != UNKNOWN]
    result = list(tags)
    for i, t in enumerate(tags):
        if t == UNKNOWN:
            near = ([x for j, x in resolved if j < i][-CONTEXT_WINDOW:]
                    + [x for j, x in resolved if j > i][:CONTEXT_WINDOW])
            ru = near.count(RU)
            result[i] = RU if ru > len(near) - ru else CE
    return result


def short_runs_are_switches(words, tags):
    if tags.count(RU) * 2 > len(tags):
        return tags
    result = list(tags)
    start = 0
    while start < len(tags):
        end = start
        while end < len(tags) and tags[end] == tags[start]:
            end += 1
        if tags[start] == RU and end - start < MIN_RU_SPAN:
            result[start:end] = [SWITCH] * (end - start)
        start = end
    return result


SEQUENCE_PASSES = [unknown_takes_neighbors, short_runs_are_switches]


def deciding_rule(word: str, lexicon: Lexicon) -> Tuple[str, str]:
    """(tag, rule name) of the first word rule that decides; for evaluation and debugging."""
    for rule in WORD_RULES:
        result = rule(word, lexicon)
        if result:
            return result, rule.__name__
    return UNKNOWN, "context"


def tag(words: List[str], lexicon: Lexicon) -> List[str]:
    """Tag the normalized words of one sentence."""
    tags = [deciding_rule(w, lexicon)[0] for w in words]
    return reduce(lambda t, p: p(words, t), SEQUENCE_PASSES, tags)


def strip_russian(text: str, lexicon: Lexicon) -> Tuple[str, List[Tuple[str, str]]]:
    removed, kept, last = [], [], 0
    for tokens in _sentences(text):
        for (start, end, word), t in zip(tokens, tag([w for _, _, w in tokens], lexicon)):
            if t in (RU, SWITCH):
                removed.append((word, t))
                kept.append(text[last:start])
                last = end
    kept.append(text[last:])
    return "".join(kept), removed

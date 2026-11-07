"""Add new native-review candidates to review/keep.txt or review/drop.txt, leaving reviewed words alone.

Usage:
    python review/generate_candidates.py exports/keyman_wordlist.tsv path/to/aosp-dictionaries/wordlists/main_ru.combined

Candidates and their default list:
  likely Russian  common in Russian (ru f >= 100), rare in the Chechen corpus (count <= 4), no Chechen-only
                  letter combination -> drop.txt
  two-letter      -> keep.txt, or drop.txt if it has no vowel (a lone letter fragment like "кх")
"""
import csv
import re
import sys
from pathlib import Path

REVIEW_DIR = Path(__file__).parent
CHECHEN_MARKERS = ("ӏ", "кх", "къ", "хь", "аь", "оь", "уь", "юь", "яь", "гӏ", "еь")
VOWELS = set("аеёиоуыэюя")


def load_ru_frequencies(combined_path: str) -> dict:
    ru = {}
    with open(combined_path, encoding="utf-8") as f:
        for line in f:
            m = re.match(r"\s*word=([^,]+),f=(\d+)", line)
            if m:
                word = m.group(1).lower()
                ru[word] = max(ru.get(word, 0), int(m.group(2)))
    return ru


def default_list(word: str, count: int, ru: dict):
    if ru.get(word, 0) >= 100 and count <= 4 and not any(m in word for m in CHECHEN_MARKERS):
        return "drop"
    if len(word) == 2:
        return "keep" if VOWELS & set(word) else "drop"
    return None


def read_list(name: str) -> set:
    path = REVIEW_DIR / f"{name}.txt"
    return set(path.read_text(encoding="utf-8").split()) if path.exists() else set()


def main(keyman_tsv: str, ru_combined: str) -> None:
    lists = {name: read_list(name) for name in ("keep", "drop")}
    reviewed = lists["keep"] | lists["drop"]
    ru = load_ru_frequencies(ru_combined)

    with open(keyman_tsv, encoding="utf-8") as f:
        for row in csv.DictReader(f, delimiter="\t"):
            word = row["word"]
            target = None if word in reviewed else default_list(word, int(row["count"]), ru)
            if target:
                lists[target].add(word)

    for name, words in lists.items():
        (REVIEW_DIR / f"{name}.txt").write_text("".join(w + "\n" for w in sorted(words)), encoding="utf-8", newline="\n")
        print(f"{name}.txt: {len(words)} words")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    main(sys.argv[1], sys.argv[2])

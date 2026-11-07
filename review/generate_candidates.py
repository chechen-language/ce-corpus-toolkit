"""Add new native-review candidates to review/aosp_review.tsv, keeping every existing decision.

Usage:
    python review/generate_candidates.py exports/keyman_wordlist.tsv path/to/aosp-dictionaries/wordlists/main_ru.combined

Candidates:
  russian?   common in Russian (ru f >= 100), rare in the Chechen corpus (count <= 4), no Chechen-only letter
             combination. Default: drop.
  two-letter every two-letter word. Default: keep, or drop if it has no vowel (a lone letter fragment like "кх").
"""
import csv
import re
import sys
from pathlib import Path

REVIEW_FILE = Path(__file__).parent / "aosp_review.tsv"
COLUMNS = ["word", "ce_count", "ru_f", "category", "decision"]
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


def candidate(word: str, count: int, ru: dict):
    if word in ru and ru[word] >= 100 and count <= 4 and not any(m in word for m in CHECHEN_MARKERS):
        return {"word": word, "ce_count": count, "ru_f": ru[word], "category": "russian?", "decision": "drop"}
    if len(word) == 2:
        decision = "keep" if VOWELS & set(word) else "drop"
        return {"word": word, "ce_count": count, "ru_f": ru.get(word, ""), "category": "two-letter", "decision": decision}
    return None


def main(keyman_tsv: str, ru_combined: str) -> None:
    existing = {}
    if REVIEW_FILE.exists():
        with open(REVIEW_FILE, encoding="utf-8") as f:
            existing = {row["word"]: row for row in csv.DictReader(f, delimiter="\t")}

    ru = load_ru_frequencies(ru_combined)
    with open(keyman_tsv, encoding="utf-8") as f:
        for row in csv.DictReader(f, delimiter="\t"):
            if row["word"] not in existing:
                found = candidate(row["word"], int(row["count"]), ru)
                if found:
                    existing[found["word"]] = found

    rows = sorted(existing.values(), key=lambda r: (r["category"], -int(r["ru_f"] or 0), r["word"]))
    with open(REVIEW_FILE, "w", encoding="utf-8", newline="\n") as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNS, delimiter="\t", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    print(f"{len(rows)} rows in {REVIEW_FILE}")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    main(sys.argv[1], sys.argv[2])

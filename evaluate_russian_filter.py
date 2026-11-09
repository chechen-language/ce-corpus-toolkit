"""Precision and recall of the Russian filter against labeled word lists (one word per line).

Usage:
    python evaluate_russian_filter.py main_ru.combined --ru drop.txt --ce keep.txt [--corpus corpus.json] [--no-overrides]

A word counts as predicted Russian when the filter removes most of its corpus occurrences
(a word absent from the corpus is tagged on its own). Each error shows the word rule that decided it;
"context" means the sequence passes did. For tuning, not for CI.
"""
import argparse
import json
import sys
from collections import Counter
from pathlib import Path

from russian_filter import DEFAULT_OVERRIDES, RU, SWITCH, _sentences, build_lexicon, deciding_rule, tag


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("ru_wordlist")
    parser.add_argument("--ru", action="append", required=True, help="file of words labeled Russian")
    parser.add_argument("--ce", action="append", required=True, help="file of words labeled Chechen")
    parser.add_argument("--corpus", default=".cache/latest.json")
    parser.add_argument("--no-overrides", action="store_true",
                        help="ignore the override list (it is seeded from the same labels)")
    args = parser.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")

    read = lambda paths: {w for p in paths for w in Path(p).read_text(encoding="utf-8").split()}
    labeled_ru, labeled_ce = read(args.ru), read(args.ce)
    texts = [e["text"] for e in json.loads(Path(args.corpus).read_text(encoding="utf-8"))
             if isinstance(e, dict) and isinstance(e.get("text"), str)]
    lexicon = build_lexicon(args.ru_wordlist, texts, None if args.no_overrides else DEFAULT_OVERRIDES)

    removed, kept = Counter(), Counter()
    for text in texts:
        for tokens in _sentences(text):
            words = [w for _, _, w in tokens]
            for word, t in zip(words, tag(words, lexicon)):
                (removed if t in (RU, SWITCH) else kept)[word] += 1

    def predicted_russian(word: str) -> bool:
        if removed[word] or kept[word]:
            return removed[word] > kept[word]
        return tag([word], lexicon)[0] in (RU, SWITCH)

    hits = {w for w in labeled_ru if predicted_russian(w)}
    false_alarms = {w for w in labeled_ce if predicted_russian(w)}
    misses = labeled_ru - hits
    print(f"labeled: {len(labeled_ru)} Russian, {len(labeled_ce)} Chechen")
    print(f"precision: {len(hits) / max(len(hits | false_alarms), 1):.1%}")
    print(f"recall:    {len(hits) / max(len(labeled_ru), 1):.1%}")
    for title, words in (("Chechen removed as Russian", false_alarms), ("Russian kept", misses)):
        print(f"\n{title} ({len(words)}), by deciding rule:")
        for word in sorted(words, key=lambda w: (deciding_rule(w, lexicon)[1], w)):
            print(f"  {deciding_rule(word, lexicon)[1]:28} {word}  removed {removed[word]}, kept {kept[word]}")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Generate a question-frequency list of words exclusive to one answer type."""
import argparse
from collections import Counter
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
WORDS = re.compile(r"[a-z]+")
CLASSES = ("technician", "general", "extra")


def latest_pool(root, license_class):
    candidates = []
    for directory in root.iterdir():
        match = re.fullmatch(rf"{re.escape(license_class)}-(\d{{4}})-(\d{{4}})", directory.name)
        if match and directory.is_dir():
            candidates.append((int(match[1]), int(match[2]), directory))
    if not candidates:
        raise ValueError(f"No top-level {license_class} question pool found")
    directory = max(candidates)[2]
    path = directory / (directory.name + ".json")
    if not path.is_file():
        raise ValueError(f"Missing JSON for newest {license_class} pool: {path}")
    return path


def words(answer):
    return set(WORDS.findall(answer.lower()))


def exclusive_counts(questions, kind):
    counts = {"correct": Counter(), "wrong": Counter()}
    for question in questions:
        answers, correct = question["answers"], question["correct"]
        if not isinstance(answers, list) or not answers or type(correct) is not int or not 0 <= correct < len(answers) or not all(isinstance(a, str) for a in answers):
            raise ValueError(f"Invalid answers or correct index for {question.get('id', 'unknown question')}")
        counts["correct"].update(words(answers[correct]))
        wrong_words = set()
        for index, answer in enumerate(answers):
            if index != correct:
                wrong_words.update(words(answer))
        counts["wrong"].update(wrong_words)
    other = "wrong" if kind == "correct" else "correct"
    return sorted(((word, count) for word, count in counts[kind].items()
                   if count >= 2 and word not in counts[other]),
                  key=lambda item: (-item[1], item[0]))[:100]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("kind", choices=("correct", "wrong"))
    args = parser.parse_args()
    for license_class in CLASSES:
        pool = latest_pool(ROOT, license_class)
        with pool.open(encoding="utf-8") as source:
            questions = json.load(source)
        if not isinstance(questions, list) or not questions:
            raise ValueError(f"Question pool is empty or invalid: {pool}")
        result = exclusive_counts(questions, args.kind)
        output = ROOT / "word-lists" / f"{license_class}-{args.kind}-only.txt"
        output.parent.mkdir(exist_ok=True)
        output.write_text(f"# {license_class.capitalize()} pool: {pool.relative_to(ROOT)}\n"
                          f"# Words exclusive to {args.kind} answers; count = questions\n"
                          "# At least 2 questions; maximum 100 words; ties alphabetical\n"
                          + "".join(f"{count}\t{word}\n" for word, count in result), encoding="utf-8")
        print(f"Wrote {len(result)} words to {output.relative_to(ROOT)}")


if __name__ == "__main__":
    main()

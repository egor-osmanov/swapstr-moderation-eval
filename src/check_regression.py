"""Fail if a committed score falls below its clear-set floor.

Clear listings are allow_clear plus block_clear. The Claude floors are the
ones the project treats as the regression gate. The keyword floor allows the
production filter's known false-positive rate and fails if that rate gets worse
or if recall drops.
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

FLOORS = (
    {
        "path": ROOT / "results" / "keyword_baseline.json",
        "name": "keyword filter",
        "min_recall": 0.98,
        "max_fpr": 0.30,
    },
    {
        "path": ROOT / "results" / "claude_classifier_v1.json",
        "name": "Claude prompt v1",
        "min_recall": 0.98,
        "max_fpr": 0.01,
    },
    {
        "path": ROOT / "results" / "claude_classifier_v2.json",
        "name": "Claude prompt v2",
        "min_recall": 0.98,
        "max_fpr": 0.01,
    },
)


def check(path, name, min_recall, max_fpr):
    report = json.loads(path.read_text())
    clear = report["clear"]
    recall = clear["recall"]
    fpr = clear["fpr"]
    failures = []
    if recall < min_recall:
        failures.append(f"{name} clear recall {recall:.1%} is below {min_recall:.0%}")
    if fpr > max_fpr:
        failures.append(f"{name} clear false-positive rate {fpr:.1%} is above {max_fpr:.0%}")
    return failures


def main():
    failures = []
    for floor in FLOORS:
        failures.extend(check(**floor))
    if failures:
        print("\n".join(failures))
        return 1
    print("clear-set floors held")
    return 0


if __name__ == "__main__":
    sys.exit(main())

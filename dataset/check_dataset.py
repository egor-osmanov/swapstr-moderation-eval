"""Check dataset/listings.jsonl against the policy keyword list.

This is a dataset lint, not the model scorer.
"""

import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.keyword_baseline import find_keywords, load_policy

POLICY = load_policy(ROOT / "policy" / "prohibited_items.json")
PATH = ROOT / "dataset" / "listings.jsonl"

CATEGORIES = list(POLICY["categories"])
SLICES = {"allow_clear", "block_clear", "borderline", "adversarial"}
ADV_TYPES = {
    "misspelling",
    "leetspeak",
    "euphemism",
    "prompt_injection",
    "split",
    "homoglyph",
    "coded",
}
FIELDS = {
    "id",
    "title",
    "description",
    "gold",
    "category",
    "slice",
    "adversarial_type",
    "note",
}


def hits(text):
    return [
        (hit["category"], hit["keyword"])
        for hit in find_keywords(text, "", POLICY)
    ]


def main():
    rows = [json.loads(line) for line in PATH.read_text().splitlines() if line.strip()]
    errors = []
    ids = [row["id"] for row in rows]
    if len(ids) != len(set(ids)):
        errors.append("duplicate ids")

    for row in rows:
        missing = FIELDS - row.keys()
        if missing:
            errors.append(f"{row.get('id')}: missing {sorted(missing)}")
        if row["gold"] not in {"allow", "block"}:
            errors.append(f"{row['id']}: bad gold")
        if row["slice"] not in SLICES:
            errors.append(f"{row['id']}: bad slice")
        if row["gold"] == "allow" and row["category"] != "none":
            errors.append(f"{row['id']}: allow row has a category")
        if row["gold"] == "block" and row["category"] not in CATEGORIES:
            errors.append(f"{row['id']}: block row has a bad category")
        if row["slice"] == "adversarial":
            if row["adversarial_type"] not in ADV_TYPES:
                errors.append(f"{row['id']}: bad adversarial_type")
        elif row["adversarial_type"] is not None:
            errors.append(f"{row['id']}: adversarial_type set outside that slice")
        if not row["title"].strip() or not row["description"].strip() or not row["note"].strip():
            errors.append(f"{row['id']}: empty text")

    print(f"rows {len(rows)}")
    print("slice", dict(Counter(row["slice"] for row in rows)))
    print("gold", dict(Counter(row["gold"] for row in rows)))
    print(
        "block_clear category",
        dict(Counter(row["category"] for row in rows if row["slice"] == "block_clear")),
    )
    print(
        "adversarial_type",
        dict(Counter(row["adversarial_type"] for row in rows if row["slice"] == "adversarial")),
    )

    print("\nplain allow_clear keyword hits (should be empty):")
    for row in rows:
        if row["slice"] == "allow_clear" and not row["note"].startswith("Trap"):
            found = hits(f"{row['title']} {row['description']}")
            if found:
                errors.append(f"{row['id']} plain hit {found[:6]}")
                print(f"  {row['id']} {row['title']}: {found[:6]}")

    print("\ntrap allow_clear with no keyword hit:")
    for row in rows:
        if row["slice"] == "allow_clear" and row["note"].startswith("Trap"):
            found = hits(f"{row['title']} {row['description']}")
            if not found:
                errors.append(f"{row['id']} trap missed")
                print(f"  {row['id']} {row['title']}")

    print("\nblock_clear keyword misses:")
    for row in rows:
        if row["slice"] == "block_clear":
            found = hits(f"{row['title']} {row['description']}")
            if not found:
                print(f"  {row['id']} {row['title']}")

    print("\nadversarial keyword misses:")
    for row in rows:
        if row["slice"] == "adversarial":
            found = hits(f"{row['title']} {row['description']}")
            if not found:
                print(f"  {row['id']} [{row['adversarial_type']}] {row['title']}")

    expected = {
        "allow_clear": 70,
        "block_clear": 60,
        "borderline": 25,
        "adversarial": 25,
    }
    actual = Counter(row["slice"] for row in rows)
    for slice_, count in expected.items():
        if actual[slice_] != count:
            errors.append(f"{slice_} is {actual[slice_]}, expected {count}")

    if len(rows) != 180:
        errors.append(f"count is {len(rows)}, expected 180")

    if errors:
        print("\nERRORS")
        for error in errors:
            print(f"  {error}")
        return 1

    print("\nok")
    return 0


if __name__ == "__main__":
    sys.exit(main())

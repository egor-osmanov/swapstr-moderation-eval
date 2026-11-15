"""Score the production keyword filter on dataset/listings.jsonl."""

import json
from collections import defaultdict
from pathlib import Path

from src.keyword_baseline import load_policy, predict
from src.score import score_rows

ROOT = Path(__file__).resolve().parents[1]
LISTINGS = ROOT / "dataset" / "listings.jsonl"
POLICY = ROOT / "policy" / "prohibited_items.json"
OUT = ROOT / "results" / "keyword_baseline.json"


def load_listings(path):
    return [json.loads(line) for line in Path(path).read_text().splitlines() if line.strip()]


def annotate(rows, policy):
    annotated = []
    for row in rows:
        result = predict(row["title"], row["description"], policy)
        annotated.append(
            {
                "id": row["id"],
                "title": row["title"],
                "slice": row["slice"],
                "adversarial_type": row["adversarial_type"],
                "gold": row["gold"],
                "gold_category": row["category"],
                "predicted": result["decision"],
                "keyword": result["keyword"],
                "matched_category": result["category"],
            }
        )
    return annotated


def subset_report(rows):
    report = score_rows(rows)
    report["false_positives"] = [row for row in rows if row["gold"] == "allow" and row["predicted"] == "block"]
    report["false_negatives"] = [row for row in rows if row["gold"] == "block" and row["predicted"] == "allow"]
    return report


def round_report(report):
    rounded = dict(report)
    for key in ("precision", "recall", "f1", "fpr"):
        if rounded[key] is not None:
            rounded[key] = round(rounded[key], 4)
    return rounded


def by_key(rows, key):
    grouped = defaultdict(list)
    for row in rows:
        grouped[row[key]].append(row)
    return {name: round_report(score_rows(group)) for name, group in sorted(grouped.items())}


def category_recall(rows, categories):
    recall = {}
    for category in categories:
        group = [row for row in rows if row["gold"] == "block" and row["gold_category"] == category]
        scored = score_rows(group) if group else None
        recall[category] = None if scored is None else round_report(scored)
    return recall


def build_report(rows, policy):
    annotated = annotate(rows, policy)
    clear = [row for row in annotated if row["slice"] in {"allow_clear", "block_clear"}]
    true_positives = [
        row for row in annotated if row["gold"] == "block" and row["predicted"] == "block"
    ]
    category_mismatches = [
        row for row in true_positives if row["matched_category"] != row["gold_category"]
    ]
    return {
        "baseline": {
            "name": "production_keyword_filter",
            "source": "swapster-enhanced/src/utils/prohibitedItems.js isProhibitedItem",
            "rule": "Lowercase title and description, first substring hit in policy order, any hit is block.",
        },
        "n": len(annotated),
        "all": round_report(subset_report(annotated)),
        "clear": round_report(subset_report(clear)),
        "by_slice": by_key(annotated, "slice"),
        "by_adversarial_type": by_key(
            [row for row in annotated if row["slice"] == "adversarial"],
            "adversarial_type",
        ),
        "recall_by_gold_category": category_recall(annotated, policy["categories"]),
        "category_mismatches_on_true_positives": category_mismatches,
    }


def pct(rate):
    if rate is None:
        return "n/a"
    return f"{rate * 100:.1f}%"


def print_block(title, block):
    print(
        f"{title}: n={block['n']}  precision {pct(block['precision'])}  "
        f"recall {pct(block['recall'])}  f1 {pct(block['f1'])}  "
        f"false-positive rate {pct(block['fpr'])}"
    )
    print(f"  tp {block['tp']}  fp {block['fp']}  tn {block['tn']}  fn {block['fn']}")


def print_report(report):
    print_block("All listings", report["all"])
    print_block("Clear listings only", report["clear"])
    print("\nBy slice")
    for name, block in report["by_slice"].items():
        print_block(f"  {name}", block)
    print("\nAdversarial recall")
    for name, block in report["by_adversarial_type"].items():
        print_block(f"  {name}", block)
    print("\nRecall by gold category")
    for name, block in report["recall_by_gold_category"].items():
        print_block(f"  {name}", block)
    print("\nFalse negatives")
    for row in report["all"]["false_negatives"]:
        print(f"  {row['id']} [{row['slice']}] {row['title']}")
    print("\nFalse positives")
    for row in report["all"]["false_positives"]:
        print(f"  {row['id']} [{row['slice']}] {row['title']}  keyword={row['keyword']}")
    mismatches = report["category_mismatches_on_true_positives"]
    print(f"\nTrue positives with the wrong category: {len(mismatches)}")
    for row in mismatches:
        print(
            f"  {row['id']} gold={row['gold_category']} matched={row['matched_category']} "
            f"keyword={row['keyword']}  {row['title']}"
        )


def main():
    policy = load_policy(POLICY)
    rows = load_listings(LISTINGS)
    report = build_report(rows, policy)
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps(report, indent=2) + "\n")
    print_report(report)
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()

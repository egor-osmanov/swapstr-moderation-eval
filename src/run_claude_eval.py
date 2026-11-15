"""Score a classifier prompt with Claude. Reuses saved responses on disk.

Requires ANTHROPIC_API_KEY in the environment. The key is not written to the cache.
Pass a prompt path to score another version. The default is prompt v1.
"""

import argparse
import hashlib
import json
import os
import sys
import time
from pathlib import Path

from src.claude_eval import EFFORT, MAX_TOKENS, MODEL, build_request, comparable_decision, parse_response, post_message
from src.keyword_baseline import load_policy
from src.prompt import PROMPT_PATH, listing_message, load_system_prompt
from src.run_keyword_eval import (
    by_key,
    category_recall,
    load_listings,
    print_block,
    round_report,
    subset_report,
)

ROOT = Path(__file__).resolve().parents[1]
LISTINGS = ROOT / "dataset" / "listings.jsonl"
POLICY = ROOT / "policy" / "prohibited_items.json"
KEYWORD_RESULTS = ROOT / "results" / "keyword_baseline.json"


def cache_dir(system, model):
    digest = hashlib.sha256(system.encode()).hexdigest()[:16]
    return ROOT / "results" / "cache" / model / digest


def load_cached(path):
    if not path.exists():
        return None
    return json.loads(path.read_text())


def fetch_one(row, system, api_key, folder, model):
    path = folder / f"{row['id']}.json"
    cached = load_cached(path)
    if cached is not None:
        cached["parsed"] = parse_response(cached["response"])
        return cached
    body = build_request(system, listing_message(row["title"], row["description"]), model=model)
    response = _post_with_retry(body, api_key)
    record = {
        "id": row["id"],
        "model": model,
        "effort": EFFORT,
        "max_tokens": MAX_TOKENS,
        "response": response,
        "parsed": parse_response(response),
    }
    path.write_text(json.dumps(record) + "\n")
    return record


def _post_with_retry(body, api_key):
    delay = 2
    last_error = None
    for _ in range(4):
        try:
            return post_message(body, api_key)
        except RuntimeError as error:
            last_error = error
            text = str(error)
            if not any(code in text for code in (" 429:", " 529:", " 500:", " 503:")):
                raise
            time.sleep(delay)
            delay *= 2
    raise last_error


def annotate(rows, records):
    annotated = []
    for row, record in zip(rows, records):
        parsed = record["parsed"]
        annotated.append(
            {
                "id": row["id"],
                "title": row["title"],
                "slice": row["slice"],
                "adversarial_type": row["adversarial_type"],
                "gold": row["gold"],
                "gold_category": row["category"],
                "predicted": comparable_decision(row["gold"], parsed),
                "model_decision": parsed["decision"],
                "model_category": parsed["category"],
                "reason": parsed["reason"],
                "status": parsed["status"],
                "stop_reason": parsed["stop_reason"],
            }
        )
    return annotated


def headline(keyword_path):
    if not keyword_path.exists():
        return None
    report = json.loads(keyword_path.read_text())
    return {
        "clear": {key: report["clear"][key] for key in ("precision", "recall", "fpr")},
        "all": {key: report["all"][key] for key in ("precision", "recall", "fpr")},
    }


def build_report(annotated, policy, prompt_path, model):
    clear = [row for row in annotated if row["slice"] in {"allow_clear", "block_clear"}]
    problems = [row for row in annotated if row["status"] != "ok"]
    return {
        "classifier": {
            "prompt": str(prompt_path.relative_to(ROOT)),
            "model": model,
            "effort": EFFORT,
            "max_tokens": MAX_TOKENS,
            "note": "Haiku 5.5 rejects temperature. Effort low is the pinned control. A refusal or unparsed reply is scored as the wrong decision.",
        },
        "n": len(annotated),
        "parse_failures": sum(row["status"] == "parse_failure" for row in annotated),
        "refusals": sum(row["status"] == "refusal" for row in annotated),
        "problems": problems,
        "all": round_report(subset_report(annotated)),
        "clear": round_report(subset_report(clear)),
        "by_slice": by_key(annotated, "slice"),
        "by_adversarial_type": by_key(
            [row for row in annotated if row["slice"] == "adversarial"],
            "adversarial_type",
        ),
        "recall_by_gold_category": category_recall(annotated, policy["categories"]),
        "keyword_baseline": headline(KEYWORD_RESULTS),
    }


def result_path(prompt_path, model):
    if model == MODEL:
        name = f"claude_{prompt_path.stem}.json"
    else:
        name = f"claude_{prompt_path.stem}_{model}.json"
    return ROOT / "results" / name


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("prompt", nargs="?", default=str(PROMPT_PATH))
    parser.add_argument("--model", default=MODEL)
    args = parser.parse_args(argv)
    prompt_path = Path(args.prompt)
    if not prompt_path.is_absolute():
        prompt_path = ROOT / prompt_path
    system = load_system_prompt(prompt_path)
    rows = load_listings(LISTINGS)
    folder = cache_dir(system, args.model)
    folder.mkdir(parents=True, exist_ok=True)
    out = result_path(prompt_path, args.model)
    missing = [row for row in rows if not (folder / f"{row['id']}.json").exists()]
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if missing and not api_key:
        print(
            f"{len(missing)} of {len(rows)} listings have no saved response for {prompt_path.name} on {args.model}. "
            "Set ANTHROPIC_API_KEY and rerun python -m src.run_claude_eval."
        )
        return 2
    records = []
    for index, row in enumerate(rows, start=1):
        record = fetch_one(row, system, api_key, folder, args.model)
        records.append(record)
        parsed = record["parsed"]
        if index == 1 or index % 20 == 0 or index == len(rows):
            print(f"{index}/{len(rows)} {row['id']} {parsed['status']} {parsed['decision']}")
    policy = load_policy(POLICY)
    report = build_report(annotate(rows, records), policy, prompt_path, args.model)
    out.write_text(json.dumps(report, indent=2) + "\n")
    print_block(f"{args.model}, all listings", report["all"])
    print_block(f"{args.model}, clear listings only", report["clear"])
    print(f"parse failures {report['parse_failures']}  refusals {report['refusals']}")
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

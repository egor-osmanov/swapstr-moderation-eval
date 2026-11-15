"""Port of isProhibitedItem from the Swapstr app.

Same rule as swapster-enhanced/src/utils/prohibitedItems.js:
lowercase the title and description, scan categories and keywords in file
order, and return on the first substring hit. Any hit is a block.
"""

import json
from pathlib import Path


def load_policy(path):
    return json.loads(Path(path).read_text())


def find_keywords(title, description, policy):
    text = f"{title} {description}".lower()
    found = []
    for category, keywords in policy["categories"].items():
        for keyword in keywords:
            if keyword.lower() in text:
                found.append(
                    {
                        "category": category,
                        "keyword": keyword,
                        "reason": policy["reasons"][category],
                    }
                )
    return found


def predict(title, description, policy):
    found = find_keywords(title, description, policy)
    if not found:
        return {
            "decision": "allow",
            "category": None,
            "keyword": None,
            "reason": None,
        }
    first = found[0]
    return {
        "decision": "block",
        "category": first["category"],
        "keyword": first["keyword"],
        "reason": first["reason"],
    }

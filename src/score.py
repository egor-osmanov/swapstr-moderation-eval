"""Score allow/block predictions against gold labels.

Block is the positive class.
"""


def counts(pairs):
    tp = fp = tn = fn = 0
    for gold, predicted in pairs:
        if gold == "block" and predicted == "block":
            tp += 1
        elif gold == "allow" and predicted == "block":
            fp += 1
        elif gold == "allow" and predicted == "allow":
            tn += 1
        elif gold == "block" and predicted == "allow":
            fn += 1
        else:
            raise ValueError(f"unexpected pair {gold}, {predicted}")
    return {"tp": tp, "fp": fp, "tn": tn, "fn": fn}


def rates(confusion):
    tp = confusion["tp"]
    fp = confusion["fp"]
    tn = confusion["tn"]
    fn = confusion["fn"]
    precision = tp / (tp + fp) if tp + fp else None
    recall = tp / (tp + fn) if tp + fn else None
    fpr = fp / (fp + tn) if fp + tn else None
    if precision is not None and recall is not None and precision + recall:
        f1 = 2 * precision * recall / (precision + recall)
    else:
        f1 = None
    return {
        **confusion,
        "n": tp + fp + tn + fn,
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "fpr": fpr,
    }


def score_rows(rows):
    return rates(counts((row["gold"], row["predicted"]) for row in rows))

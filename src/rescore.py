"""Re-score the published runs from saved replies.

This does not call the API. A missing cache exits with the same code as the
Claude runner. The held-out file is not part of this command.
"""

from src.check_regression import main as check_main
from src.run_claude_eval import main as claude_main
from src.run_keyword_eval import main as keyword_main


def main():
    steps = (
        ("keyword filter", keyword_main, None),
        ("Claude prompt v1", claude_main, None),
        ("Claude prompt v2", claude_main, ["prompts/classifier_v2.md"]),
        ("clear-set floors", check_main, None),
    )
    for name, fn, argv in steps:
        print(f"\n== {name} ==")
        code = fn() if argv is None else fn(argv)
        if code:
            return code
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

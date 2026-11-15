"""Load the classifier system prompt. This module does not call an API."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROMPT_PATH = ROOT / "prompts" / "classifier_v1.md"
MARKER = "## SYSTEM\n"


def load_system_prompt(path=PROMPT_PATH):
    text = Path(path).read_text()
    if MARKER not in text:
        raise ValueError(f"{path} is missing the SYSTEM marker")
    prompt = text.split(MARKER, 1)[1].strip()
    if not prompt:
        raise ValueError(f"{path} has an empty system prompt")
    return prompt


def listing_message(title, description):
    return f"Title: {title}\nDescription: {description}"

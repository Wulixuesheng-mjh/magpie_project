"""Small, source-backed Magpie behavior extracts, NOT a full gateway emulator.

Source commit: 6a6e4fefac9261db4e1eeb769665a21ebaefbd12.
These Python ports are not yet differential-tested against the Go runtime.
"""
import re


def cut_middle(text, head=3000, tail=1000):
    return text[:head] + "\n…\n" + text[-tail:] if len(text) > head + tail else text


def read_intent(answer, intents):
    # Go regexp \d is ASCII, unlike Python's default \d.
    match = re.search(r"[0-9]+", answer)
    if not match:
        raise ValueError("answer_error")
    digits = match.group().lstrip("0") or "0"
    # strconv.Atoi is bounded by the platform int (64 bit on the study host).
    if len(digits) > 19:
        raise ValueError("answer_error")
    number = int(digits)
    if number > 2**63 - 1 or number > len(intents):
        raise ValueError("answer_error")
    return (None if number == 0 else intents[number - 1]), str(number)


def strict_number_format(answer, n):
    value = answer.strip()
    return bool(re.fullmatch(r"[0-9]+", value)) and len(value) <= 19 and int(value) <= n


def previous_fallback(intent, error, previous, intents):
    """Only model errors trigger previous intent; valid none does not."""
    if error and previous in intents:
        return {"intent": previous, "fallback": "previous", "error": error}
    return {"intent": intent, "fallback": None, "error": error}

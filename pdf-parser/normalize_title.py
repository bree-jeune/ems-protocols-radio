import re
import string

def normalize_title(s: str) -> str:
    # If s is empty/None/Falsey, return "" so it does not break later.
    if not s:
        return ""

    # 1) lower-case everything
    s = s.lower()

    # 2) strip leading/trailing whitespace
    s = s.strip()

    # 3) remove punctuation you don’t care about
    #    keep only letters, numbers, and spaces
    #    ch.isalnum() → letters and numbers 
    #    ch.isspace() → spaces
    #    removes punctuation like / , & - .
    s = "".join(ch for ch in s if ch.isalnum() or ch.isspace())

    # 4) collapse multiple spaces into one
    # Turns runs of spaces/tabs/newlines into a single space
    s = re.sub(r"\s+", " ", s)

    # Returns the normalized form for safe comparison.
    return s

test_titles = [
    "Abdominal / Flank Pain, Nausea & Vomiting",
    "  ABDOMINAL  / FLANK PAIN, NAUSEA & VOMITING   ",
]

for t in test_titles:
    print(t, "->", normalize_title(t))

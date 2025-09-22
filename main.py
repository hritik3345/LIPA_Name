import functions_framework
import re
from flask import jsonify

REFUSAL_PATTERNS = re.compile(
    r"\b(?:no|don'?t|do not|won'?t|will not|prefer not|rather not|skip|not now)\b|"
    r"\b(?:why|what for|not comfortable|keep it private)\b",
    re.I,
)

INTRO_PATTERNS = re.compile(
    r"(?:^|\b)(?:my\s+name\s+is|i\s*am|this\s*is|you\s*can\s*call\s*me|call\s*me)\s+",
    re.I,
)

# Words that clearly aren't names in this domain
BLOCKLIST_WORDS = {
    "lipaglyn", "tablet", "tablets", "drug", "medicine", "mr", "mrs", "ms",
    "doctor", "dr", "dose", "dosing", "mg", "what", "why", "how", "where",
    "when", "which", "faq", "question", "help","uses","define","nash","nafld","studies"
}

# Accept letters (Latin incl. accents) + common name punctuation
NAME_TOKEN = r"[A-Za-zÀ-ÖØ-öø-ÿ]+(?:[-'][A-Za-zÀ-ÖØ-öø-ÿ]+)?"
CANDIDATE_RE = re.compile(rf"^{NAME_TOKEN}(?:\s+{NAME_TOKEN}){{0,2}}$")  # 1–3 tokens

def _titlecase_name(name: str) -> str:
    parts = []
    for w in name.split():
        if w.lower() in {"dr", "dr."}:
            parts.append("Dr.")
        else:
            parts.append(w[:1].upper() + w[1:].lower())
    return " ".join(parts)

def looks_like_question_or_sentence(text: str) -> bool:
    if "?" in text:
        return True
    # Long inputs with many words probably aren’t names
    if len(text.split()) >= 5:
        return True
    # Contains obvious non-name punctuation
    if re.search(r"[,:;@/\\\d]", text):
        return True
    # Starts with interrogatives
    if re.match(r"^\s*(what|why|how|where|when|which)\b", text, re.I):
        return True
    return False

def extract_candidate(raw: str) -> str | None:
    txt = raw.strip()

    # If they wrote a sentence, try to pull name after “my name is / I am / call me”
    m = INTRO_PATTERNS.search(txt)
    if m:
        candidate = txt[m.end():].strip()
        # stop at first punctuation
        candidate = re.split(r"[,.!?;:]\s*", candidate)[0].strip()

        # Keep only first 1–3 tokens
        tokens = candidate.split()
        candidate = " ".join(tokens[:3])

        return candidate or None

    # Otherwise treat the whole input as a candidate (short, no punctuation)
    return txt

def is_valid_name(candidate: str) -> bool:
    if not candidate or looks_like_question_or_sentence(candidate):
        return False

    # Too short/long
    if len(candidate) < 2 or len(candidate) > 40:
        return False

    # Must match the 1–3 token pattern
    if not CANDIDATE_RE.match(candidate):
        return False

    # Blocklist words (domain terms / interrogatives)
    low = candidate.lower()
    if any(w in BLOCKLIST_WORDS for w in low.replace("-", " ").replace("'", " ").split()):
        return False

    return True

@functions_framework.http
def handle_webhook(request):
    if request.method == "GET":
        return ("OK", 200)

    body = request.get_json(silent=True) or {}
    session_info = body.get("sessionInfo") or {}
    params = (session_info.get("parameters") or {}).copy()
    raw = params.get("name")

    # No attempt yet → do nothing
    if not raw:
        return jsonify({})

    # Refusal
    if REFUSAL_PATTERNS.search(raw):
        return jsonify({
            "sessionInfo": {"parameters": {
                "name": None,                # clear any partial fill
                "name_provided": "false"
            }},
            "fulfillmentResponse": {
                "messages": [{
                    "text": {"text": [
                        "Got it — sharing your name is optional. I can still help. "
                        "How can I assist you with Lipaglyn research and studies?"
                    ]}
                }]
            }
        })

    # Try to extract + validate
    candidate = extract_candidate(raw)
    if candidate and is_valid_name(candidate):
        clean = _titlecase_name(candidate)
        return jsonify({
            "sessionInfo": {"parameters": {
                "name": clean,
                "name_provided": "true"
            }},
            "fulfillmentResponse": {
                "messages": [{
                    "text": {"text": [
                        f"Thanks, Dr.{clean}!😊 I'm here to help. How can I assist you with the 'Lipaglyn Research Studies and Information' today?
                    ]}
                }]
            }
        })

    # Not a valid name → clear param and continue non-blocking
    return jsonify({
        "sessionInfo": {"parameters": {
            "name": None,                 # clears the slot so CX won’t stick with bad value
            "name_provided": "false"
        }},
        "fulfillmentResponse": {
            "messages": [{
                "text": {"text": [
                    "No worries — your name is optional. If you’d like, you can tell me "
                    "your name to personalize the chat (e.g., “I am Asha”). "
                    "Meanwhile, what can I help you find about Lipaglyn?"
                ]}
            }]
        }
    })

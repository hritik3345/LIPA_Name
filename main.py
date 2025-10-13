import functions_framework
import re
from flask import jsonify

# --- Pattern Definitions ---
REFUSAL_PATTERNS = re.compile(
    r"\b(?:no|don'?t|do not|won'?t|will not|prefer not|rather not|skip|not now)\b|"
    r"\b(?:why|what for|not comfortable|keep it private)\b",
    re.I,
)

INTRO_PATTERNS = re.compile(
    r"(?:^|\b)(?:my\s+name\s+is|i\s*am|this\s*is|you\s*can\s*call\s*me|call\s*me)\s+",
    re.I,
)

# Greeting words (new addition)
GREETING_PATTERNS = re.compile(
    r"\b(?:hi|hello|hey|hiya|greetings|good\s*(morning|afternoon|evening))\b",
    re.I,
)

# Words that clearly aren't names in this domain
BLOCKLIST_WORDS = {
    "lipaglyn", "tablet", "tablets", "drug", "medicine", "mr", "mrs", "ms",
    "doctor", "dr", "dose", "dosing", "mg", "what", "why", "how", "where",
    "when", "which", "faq", "question", "help", "uses", "define", "nash", "nafld", "studies"
}

# Accept letters (Latin incl. accents) + common name punctuation
NAME_TOKEN = r"[A-Za-zÀ-ÖØ-öø-ÿ]+(?:[-'][A-Za-zÀ-ÖØ-öø-ÿ]+)?"
CANDIDATE_RE = re.compile(rf"^{NAME_TOKEN}(?:\s+{NAME_TOKEN}){{0,2}}$")  # 1–3 tokens


# --- Helper Functions ---
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
    if len(text.split()) >= 5:
        return True
    if re.search(r"[,:;@/\\\d]", text):
        return True
    if re.match(r"^\s*(what|why|how|where|when|which)\b", text, re.I):
        return True
    return False


def extract_candidate(raw: str) -> str | None:
    txt = raw.strip()
    m = INTRO_PATTERNS.search(txt)
    if m:
        candidate = txt[m.end():].strip()
        candidate = re.split(r"[,.!?;:]\s*", candidate)[0].strip()
        tokens = candidate.split()
        candidate = " ".join(tokens[:3])
        return candidate or None
    return txt


def is_valid_name(candidate: str) -> bool:
    if not candidate or looks_like_question_or_sentence(candidate):
        return False
    if len(candidate) < 2 or len(candidate) > 40:
        return False
    if not CANDIDATE_RE.match(candidate):
        return False
    low = candidate.lower()
    if any(w in BLOCKLIST_WORDS for w in low.replace("-", " ").replace("'", " ").split()):
        return False
    return True


# --- Main Webhook Function ---
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

    # --- NEW: Handle Greetings ---
    if GREETING_PATTERNS.search(raw):
        return jsonify({
            "sessionInfo": {"parameters": {
                "name": None,
                "name_provided": "false"
            }},
            "fulfillmentResponse": {
                "messages": [{
                    "text": {"text": [
                        "Hello there! 👋 It’s great to meet you. Could you please share your name with me so we can get started?"
                    ]}
                }]
            }
        })

    # --- Handle Refusal ---
    if REFUSAL_PATTERNS.search(raw):
        return jsonify({
            "sessionInfo": {"parameters": {
                "name": None,
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

    # --- Try Extracting and Validating a Name ---
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
                        f"Thanks, Dr.{clean}! 😊 I'm here to help. How can I assist you with the 'Lipaglyn Research Studies and Information' today?"
                    ]}
                }]
            }
        })

    # --- Invalid / Non-name input ---
    return jsonify({
        "sessionInfo": {"parameters": {
            "name": None,
            "name_provided": "false"
        }},
        "fulfillmentResponse": {
            "messages": [{
                "text": {"text": [
                    "No worries — your name is optional. If you’d like, you can tell me your name so I can address you properly. "
                    "Meanwhile, what can I help you find about Lipaglyn?"
                ]}
            }]
        }
    })

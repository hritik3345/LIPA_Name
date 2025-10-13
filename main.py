import functions_framework
import re
from flask import jsonify

# --- Patterns ---
REFUSAL_PATTERNS = re.compile(
    r"\b(?:no|don'?t|do not|won'?t|will not|prefer not|rather not|skip|not now)\b|"
    r"\b(?:why|what for|not comfortable|keep it private)\b", re.I,
)
INTRO_PATTERNS = re.compile(
    r"(?:^|\b)(?:my\s+name\s+is|i\s*am|this\s*is|you\s*can\s*call\s*me|call\s*me)\s+",
    re.I,
)
GREETING_PATTERNS = re.compile(
    r"\b(?:hi|hello|hey|hiya|greetings|good\s*(morning|afternoon|evening))\b", re.I,
)

BLOCKLIST_WORDS = {
    "lipaglyn", "tablet", "tablets", "drug", "medicine", "mr", "mrs", "ms",
    "doctor", "dr", "dose", "dosing", "mg", "what", "why", "how", "where",
    "when", "which", "faq", "question", "help", "uses", "define", "nash", "nafld", "studies"
}

NAME_TOKEN = r"[A-Za-zÀ-ÖØ-öø-ÿ]+(?:[-'][A-Za-zÀ-ÖØ-öø-ÿ]+)?"
CANDIDATE_RE = re.compile(rf"^{NAME_TOKEN}(?:\s+{NAME_TOKEN}){{0,2}}$")

def _titlecase_name(name: str) -> str:
    parts = []
    for w in name.split():
        if w.lower() in {"dr", "dr."}:
            parts.append("Dr.")
        else:
            parts.append(w[:1].upper() + w[1:].lower())
    return " ".join(parts)

def looks_like_question_or_sentence(text: str) -> bool:
    if "?" in text or len(text.split()) >= 5:
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
        return " ".join(tokens[:3]) or None
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

# --- MAIN FUNCTION ---
@functions_framework.http
def handle_webhook(request):
    if request.method == "GET":
        return ("OK", 200)

    body = request.get_json(silent=True) or {}
    session_info = body.get("sessionInfo") or {}
    params = (session_info.get("parameters") or {}).copy()
    raw = params.get("name")

    if not raw:
        return jsonify({})

    txt = raw.strip()

    # --- Greeting ---
    if GREETING_PATTERNS.search(txt):
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
                }],
                "mergeBehavior": "REPLACE"
            }
        })

    # --- Refusal ---
    if REFUSAL_PATTERNS.search(txt):
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

    # --- Extract and Validate Name ---
    candidate = extract_candidate(txt)
    if candidate and is_valid_name(candidate):
        clean = _titlecase_name(candidate)
        greeting_text = f"Thanks,, Dr. {clean}! 😊 How can I assist you with the 'Lipaglyn Research Studies and Information' today?"
        return jsonify({
            "sessionInfo": {"parameters": {
                "name": clean,
                "name_provided": "true"
            }},
            "fulfillmentResponse": {
                "messages": [{
                    "text": {"text": [greeting_text]}
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

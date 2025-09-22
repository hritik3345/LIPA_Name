import functions_framework
import json
import re
from flask import jsonify

@functions_framework.http
def handle_webhook(request):
    # Health check
    if request.method == "GET":
        return ("OK", 200)

    # Safely parse JSON
    request_json = request.get_json(silent=True) or {}
    session_info = request_json.get("sessionInfo") or {}
    params = session_info.get("parameters") or {}
    user_input = params.get("name")

    if not user_input:
        return jsonify({})

    user_input_lower = user_input.lower()

    # Define refusal patterns (unchanged)
    refusal_patterns = [
        r"\b(no|don't|will not|refuse|prefer not)\b",
        r"\b(why|what for)\b",
    ]

    for pattern in refusal_patterns:
        if re.search(pattern, user_input_lower):
            dialogflow_response = {
                "sessionInfo": {"parameters": {"name_provided": "false"}},
                "fulfillmentResponse": {
                    "messages": [
                        {
                            "text": {
                                "text": [
                                    "I understand. Providing your name helps me to personalize our conversation. If you change your mind, tell me your name. Otherwise, how can I assist you with Lipaglyn Studies and Research?"
                                ]
                            }
                        }
                    ]
                },
            }
            return jsonify(dialogflow_response)

    # More specific name extraction logic
    extracted_name = ""

    # This pattern looks for "my name is..." or "i am..."
    match = re.search(r"(?:my name is|i am|you can call me)\s+([\w\s]+)", user_input_lower)
    if match:
        extracted_name = match.group(1).strip().title()
    else:
        # A new, more specific pattern to identify a proper name
        # This will look for capitalized words, a common pattern for names
        proper_name_pattern = r"\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)?\b"
        matches = re.findall(proper_name_pattern, user_input)
        if matches:
            # Take the first matched proper name as the likely name
            extracted_name = matches[0]
        else:
            # Fallback to the original logic if no specific pattern is found
            extracted_name = user_input.strip().title()

    # Prepare the success response
    dialogflow_response = {
        "sessionInfo": {
            "parameters": {
                "name": extracted_name,
                "name_provided": "true"
            }
        },
        "fulfillmentResponse": {
            "messages": [
                {
                    "text": {
                        "text": [
                            f"Thank you, Dr.{extracted_name}! 😊 I'm here to help. How can I assist you with the 'Lipaglyn Research Studies and Information' today?"
                        ]
                    }
                }
            ]
        },
    }
    return jsonify(dialogflow_response)

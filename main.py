import functions_framework
import json
import re
from flask import jsonify

@functions_framework.http
def handle_webhook(request):
    # Health check & human-in-browser check
    if request.method == "GET":
        return ("OK", 200)

    # Safely parse JSON
    request_json = request.get_json(silent=True) or {}
    session_info = request_json.get("sessionInfo") or {}
    params = session_info.get("parameters") or {}
    user_input = params.get("name")

    # If no name provided yet, return empty JSON (Dialogflow CX-friendly)
    if not user_input:
        return jsonify({})

    user_input_lower = user_input.lower()

    # Define refusal patterns
    refusal_patterns = [
        r"\b(no|don't|will not|refuse|prefer not)\b",
        r"\b(why|what for)\b",
    ]

    # Check for refusal or inquiry
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

    # If no refusal is found, proceed with name extraction logic
    extracted_name = ""
    match = re.search(r"(?:i am|my name is|you can call me)\s+(.*)", user_input_lower)
    
    if match:
        extracted_name = match.group(1).strip().title()
   else:
      
        match_reverse = re.search(r"(\w+)\s+(?:i am|is my name)", user_input_lower)
        if match_reverse:
            extracted_name = match_reverse.group(1).strip().title()
        else:
            # Fallback for just the name "Rajesh"
            extracted_name = user_input.strip().title()

    # Prepare the success response with the cleaned name and a fulfillment message
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

import functions_framework
import json
import re

@functions_framework.http
def handle_webhook(request):
    request_json = request.get_json(silent=True)
    
    try:
        user_input = request_json['sessionInfo']['parameters']['name']
    except KeyError:
        return json.dumps({})
        
    user_input_lower = user_input.lower()

    # Define refusal patterns
    refusal_patterns = [
        r'\b(no|don\'t|will not|refuse|prefer not)\b',
        r'\b(why|what for)\b'
    ]

    # Check for refusal or inquiry
    for pattern in refusal_patterns:
        if re.search(pattern, user_input_lower):
            # User is refusing or asking a question
            dialogflow_response = {
                "sessionInfo": {
                    "parameters": {
                        "name_provided": "false"  # A new flag to indicate no name was provided
                    }
                },
                "fulfillmentResponse": {
                    "messages": [
                        {
                            "text": {
                                "text": [
                                    "I understand. Providing your name helps me to personalize our conversation. If you change your mind, just let me know your name. Otherwise, how can I assist you with Lipaglyn Studies and Research?"
                                ]
                            }
                        }
                    ]
                }
            }
            return json.dumps(dialogflow_response)

    # If no refusal is found, proceed with name extraction logic
    extracted_name = ""
    match = re.search(r'(?:i am|my name is|you can call me)\s+(.*)', user_input_lower)
    
    if match:
        extracted_name = match.group(1).strip().title()
    else:
        extracted_name = user_input.strip().title()

    # Send back the extracted name and a success flag
    dialogflow_response = {
        "sessionInfo": {
            "parameters": {
                "name": extracted_name,
                "name_provided": "true"
            }
        }
    }

    return json.dumps(dialogflow_response)

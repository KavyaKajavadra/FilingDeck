import os
import json
from datetime import datetime
import warnings
import google.generativeai as genai
warnings.filterwarnings("ignore", category=FutureWarning, module="google.generativeai")

# Load Gemini API key from environment
genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))

# Use the Gemini Pro model
model = genai.GenerativeModel('gemini-pro')

SYSTEM_PROMPT = """
You are the official AI assistant for 'FileSure', a modern, tech-forward tax and compliance agency based in India (Mumbai/Thane, serving Pan-India digitally).
Your goal is to answer client questions about FileSure's services, pricing, compliance deadlines (GST, ROC, TDS, ITR), and encourage them to sign up.

### Business Info & Tone
- **Tone**: Professional, extremely polite, helpful, and concise (since this is WhatsApp, keep answers short). Use emojis tastefully.
- **Company Name**: FileSure
- **Key Offerings**: GST Filing, TDS Returns, ROC Annual Filings, Company Incorporation, Professional Tax.
- **Pricing Plans**: 
  - Starter Plan (₹999/month): GST Filing, Compliance Calendar, WhatsApp Support.
  - Growth Plan (₹2,499/month - Most Popular): Everything in Starter + TDS, Professional Tax, ITR, Priority Support.
  - Complete Plan (₹4,999/month): Everything in Growth + ROC Annual Filings, DIR-3 KYC, Relationship Manager.
- **One-time Services**: Company Incorporation (₹4999-9999), PAN Application (₹499), GST Registration (₹1499), Udyam Registration (₹499).

### Human Handoff Rule [CRITICAL]
If the user asks a highly complex tax question, asks for legal advice, gets frustrated, or explicitly asks to "talk to a human", "talk to Kavya", "customer care", "agent", etc., you MUST respond exactly with the following JSON string and nothing else:
{"handoff": true, "message": "I'll connect you with a human expert from our team right away! They will reply to you here on WhatsApp shortly."}

Otherwise, just answer their question normally as text. Do NOT use JSON unless you are triggering a human handoff.
"""

def get_ai_response(user_message, conversation_history):
    """
    Generates an AI response using Gemini.
    conversation_history should be a list of dicts: [{'role': 'user'|'model', 'parts': ['text']}]
    """
    # Create the context by prepending the system prompt to the history
    # Gemini requires specific formats for history.
    formatted_history = []
    
    # We fake the system prompt by having the user send it first, and the model acknowledging it.
    formatted_history.append({"role": "user", "parts": [SYSTEM_PROMPT]})
    formatted_history.append({"role": "model", "parts": ["Understood. I am the FileSure WhatsApp assistant."]})
    
    # Append actual conversation history
    for msg in conversation_history:
        formatted_history.append(msg)
        
    try:
        chat = model.start_chat(history=formatted_history)
        response = chat.send_message(user_message)
        
        # Check if the AI decided to handoff
        try:
            # Try to parse as JSON in case it triggered the handoff rule
            data = json.loads(response.text)
            if data.get("handoff"):
                return {"text": data.get("message", "Connecting you to a human..."), "handoff": True}
        except json.JSONDecodeError:
            pass # It's a normal text response
            
        return {"text": response.text, "handoff": False}
        
    except Exception as e:
        print(f"Error generating AI response: {e}")
        return {"text": "I'm sorry, I am having trouble connecting to my servers right now. Can I help you with anything else?", "handoff": False}

import os
import datetime
from fastapi import FastAPI, Request, Response, status, HTTPException
from supabase import create_client, Client
from twilio.twiml.messaging_response import MessagingResponse
from dotenv import load_dotenv

# Import your Grocery Agent from the separate file
from agents.grocery import handle_grocery_request

# 1) Load environment variables from .env
load_dotenv()

# 2) Read environment variables
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")  # Optional for now
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")    # Optional for now

# 3) Initialize Supabase client
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# 4) Initialize FastAPI
app = FastAPI()

@app.get("/")
def read_root():
    """
    Simple health check or "Hello World" endpoint.
    """
    return {"message": "Hello World"}

@app.get("/test-supabase")
def test_supabase():
    """
    Quick check to confirm we can create a Supabase client.
    This does NOT perform an actual database query by default.
    """
    return {"message": "Supabase client ready (not actually querying yet)."}

@app.post("/test-insert")
def test_insert():
    """
    Test endpoint to insert a sample record into the 'items' table.
    """
    try:
        now = datetime.datetime.utcnow().isoformat()
        data_to_insert = {
            "user_id": "+1234567890",      # just a fake phone number for testing
            "category": "testcategory",
            "subcategory": "testsubcategory",
            "name": "Just a test item",
            "timestamp": now
        }
        response = supabase.table("items").insert(data_to_insert).execute()
        if not response.data:
            raise HTTPException(
                status_code=400,
                detail="Supabase error: No data returned"
            )
        return {
            "status": "success",
            "data": response.data
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/sms")
async def receive_sms(request: Request) -> Response:
    """
    Twilio will send an HTTP POST (form-encoded) to this endpoint
    whenever an SMS is received. We'll parse the message and either:
      1) Attempt "data entry" if it fits the two-line format
      2) Otherwise, route to our handle_request function
    """
    form_data = await request.form()
    from_number = form_data.get("From")  # The sender's phone number
    body_text = form_data.get("Body")    # The SMS text message

    # Basic validations
    if not from_number or not body_text:
        return _twilio_response("Error: Missing phone number or message body.", is_error=True)

    if is_data_entry_format(body_text):
        # If it matches the two-line pattern, treat it as data insertion
        return store_data_entry(from_number, body_text)
    else:
        # Otherwise, route to an agent (e.g., Grocery Agent)
        answer = handle_request(from_number, body_text)
        return _twilio_response(answer)

def is_data_entry_format(body_text: str) -> bool:
    """
    Checks if the incoming text has at least two lines,
    which we treat as 'category[, subcategory]' and 'name'.
    Example:
      Grocery
      Bananas
    or
      Grocery, produce
      Bananas
    """
    lines = body_text.strip().split("\n")
    return len(lines) >= 2

def store_data_entry(from_number: str, body_text: str) -> Response:
    """
    Parse the text as 'category[, subcategory]' on line1, and 'name' on line2,
    then store it in Supabase. We convert category/subcategory/name to lowercase
    for consistent matching later.
    """
    lines = body_text.strip().split("\n")
    line1 = lines[0].strip()
    line2 = lines[1].strip()

    if "," in line1:
        parts = line1.split(",", 1)
        category = parts[0].strip().lower()   # always store in lowercase
        subcategory_raw = parts[1].strip().lower()
        subcategory = subcategory_raw if subcategory_raw else None
    else:
        category = line1.lower()
        subcategory = None

    name = line2.strip().lower()  # also store name in lowercase

    # Validate
    if not category or not name:
        return _twilio_response("Error: Missing category or name.", is_error=True)

    now = datetime.datetime.utcnow().isoformat()
    data_to_insert = {
        "user_id": from_number,
        "category": category,
        "subcategory": subcategory,
        "name": name,
        "timestamp": now
    }

    try:
        response = supabase.table("items").insert(data_to_insert).execute()
        if not response.data:
            return _twilio_response("Database error: No data returned", is_error=True)
        return _twilio_response("Stored!")
    except Exception as e:
        return _twilio_response(f"Unexpected error: {str(e)}", is_error=True)

def handle_request(from_number: str, body_text: str) -> str:
    """
    Routes non-data-entry messages to the correct agent.
    Currently only handling 'grocery' keywords as an example.
    """
    text_lower = body_text.lower()
    if "grocery" in text_lower:
        return handle_grocery_request(body_text, from_number, supabase)
    else:
        return (
            "Sorry, I’m not sure what you need.\n"
            "Try sending:\n"
            "  Grocery\n"
            "  Bananas\n\n"
            "OR\n"
            "  Remove grocery bananas\n"
            "to remove an item."
        )

def _twilio_response(message: str, is_error: bool = False) -> Response:
    """
    Build a TwiML response so Twilio will send an SMS back to the user.
    We'll return 200 in all cases, because Twilio doesn't
    strictly require a different error status code.
    """
    twiml_resp = MessagingResponse()
    twiml_resp.message(message)
    return Response(
        content=str(twiml_resp),
        media_type="application/xml",
        status_code=status.HTTP_200_OK
    )

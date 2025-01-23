import os
import datetime
from fastapi import FastAPI, Request, Response, status, HTTPException
from supabase import create_client, Client
from twilio.twiml.messaging_response import MessagingResponse
from dotenv import load_dotenv

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
            "category": "TestCategory",
            "subcategory": "TestSubcategory",
            "name": "Just a test item",     # Changed from "item" to "name"
            "timestamp": now
        }

        # Insert into Supabase
        response = supabase.table("items").insert(data_to_insert).execute()

        # Check if there's data in the response
        if not response.data:
            raise HTTPException(
                status_code=400,
                detail="Supabase error: No data returned"
            )

        # On success, return the data
        return {
            "status": "success",
            "data": response.data  # Access .data directly
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/sms")
async def receive_sms(request: Request) -> Response:
    """
    Twilio will send an HTTP POST (form-encoded) to this endpoint
    whenever an SMS is received. We'll parse the message, validate it,
    insert into Supabase, and return a TwiML response.
    """
    form_data = await request.form()
    from_number = form_data.get("From")  # The sender's phone number
    body_text = form_data.get("Body")    # The SMS text message

    # Basic validations
    if not from_number or not body_text:
        return _twilio_response("Error: Missing phone number or message body.", is_error=True)

    lines = body_text.strip().split("\n")
    if len(lines) < 2:
        # Not enough lines => error
        return _twilio_response(
            "Error: Message should contain at least two lines:\n"
            "Line 1: category[, subcategory]\n"
            "Line 2: name",
            is_error=True
        )

    line1 = lines[0].strip()
    line2 = lines[1].strip()

    # Parse category/subcategory
    if "," in line1:
        parts = line1.split(",", 1)  # Split on the first comma only
        category = parts[0].strip()
        subcategory = parts[1].strip() or None
    else:
        # No comma => entire line is category
        category = line1
        subcategory = None

    # The name is line2
    name = line2.strip()

    # Validate category & name
    if not category:
        return _twilio_response("Error: Missing category.", is_error=True)
    if not name:
        return _twilio_response("Error: Missing name.", is_error=True)

    # Insert into Supabase
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
        # Check if there's data in the response
        if not response.data:
            return _twilio_response(
                "Database error: No data returned",
                is_error=True
            )

        # Successfully stored
        subcat_str = subcategory if subcategory else "None"
        success_message = (
            f"Stored:\n"
            f"Category: {category}\n"
            f"Subcategory: {subcat_str}\n"
            f"Name: {name}"
        )
        return _twilio_response(success_message)

    except Exception as e:
        return _twilio_response(f"Unexpected error: {str(e)}", is_error=True)

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

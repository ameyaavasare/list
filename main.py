import os
import datetime
from fastapi import FastAPI, Request, Response, status, HTTPException
from supabase import create_client, Client
from supabase.client import APIError
from dotenv import load_dotenv
from twilio.twiml.messaging_response import MessagingResponse

# 1) Load environment variables from .env
load_dotenv()

# 2) Read environment variables
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

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
    """
    return {"message": "Supabase client ready (not actually querying yet)."}


@app.post("/test-insert")
def test_insert():
    """
    Test endpoint to insert a sample record into the 'items' table.
    """

    try:
        # 1) Prepare data
        now = datetime.datetime.utcnow().isoformat()
        data_to_insert = {
            "user_id": "+1234567890",  # Fake phone number for testing
            "category": "TestCategory",
            "subcategory": "TestSubcategory",
            "item": "Just a test item",
            "timestamp": now
        }

        # 2) Insert into Supabase using a list (recommended)
        response = supabase.table("items").insert([data_to_insert]).execute()

        # 3) According to the official docs, we can check 'response.error'
        if response.error:
            # response.error might be a string or dict describing the error
            raise HTTPException(
                status_code=response.status or 400,
                detail=f"Supabase error: {response.error}"
            )

        # 4) Also check the status
        if response.status >= 400:
            raise HTTPException(
                status_code=response.status,
                detail=f"Unexpected status from Supabase: {response.status} {response.status_text}"
            )

        # 5) If no error, response.data should contain the inserted row(s)
        inserted = response.data  # Typically a list of inserted records

        return {
            "status": "success",
            "inserted": inserted
        }

    except APIError as e:
        # If supabase-py encounters a deeper error, it may raise APIError
        raise HTTPException(status_code=400, detail=f"Supabase APIError: {str(e)}")
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
    from_number = form_data.get("From")
    body_text = form_data.get("Body")

    # Basic checks
    if not from_number or not body_text:
        return _twilio_response("Error: Missing phone number or message body.", is_error=True)

    lines = body_text.strip().split("\n")
    if len(lines) < 2:
        return _twilio_response(
            "Error: Message should contain at least two lines:\n"
            "Line 1: category[, subcategory]\n"
            "Line 2: item",
            is_error=True
        )

    # Separate lines
    line1 = lines[0].strip()
    line2 = lines[1].strip()

    # Category & subcategory
    if "," in line1:
        parts = line1.split(",", 1)
        category = parts[0].strip()
        subcategory = parts[1].strip() or None
    else:
        category = line1
        subcategory = None

    if not category or not line2:
        return _twilio_response("Error: Missing category or item.", is_error=True)

    data_to_insert = {
        "user_id": from_number,
        "category": category,
        "subcategory": subcategory,
        "item": line2.strip(),
        "timestamp": datetime.datetime.utcnow().isoformat()
    }

    try:
        response = supabase.table("items").insert([data_to_insert]).execute()

        if response.error:
            # Something went wrong in the DB
            return _twilio_response(f"Database error: {response.error}", is_error=True)

        if response.status >= 400:
            return _twilio_response(
                f"Unexpected status from Supabase: {response.status} {response.status_text}",
                is_error=True
            )

        # success
        subcat_str = subcategory if subcategory else "None"
        success_msg = (
            f"Stored:\n"
            f"Category: {category}\n"
            f"Subcategory: {subcat_str}\n"
            f"Item: {line2}"
        )
        return _twilio_response(success_msg)

    except APIError as e:
        return _twilio_response(f"Supabase APIError: {str(e)}", is_error=True)
    except Exception as e:
        return _twilio_response(f"Unexpected error: {str(e)}", is_error=True)


def _twilio_response(message: str, is_error: bool = False) -> Response:
    """
    Returns TwiML so Twilio can send an SMS response back.
    """
    twiml_resp = MessagingResponse()
    twiml_resp.message(message)
    return Response(
        content=str(twiml_resp),
        media_type="application/xml",
        status_code=status.HTTP_200_OK
    )

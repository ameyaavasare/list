import os
import datetime
from fastapi import FastAPI, Request, Response, status, HTTPException
from supabase import create_client, Client
from supabase.client import APIError
from dotenv import load_dotenv
from twilio.twiml.messaging_response import MessagingResponse

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

app = FastAPI()

@app.get("/")
def read_root():
    return {"message": "Hello World"}

@app.get("/test-supabase")
def test_supabase():
    return {"message": "Supabase client ready (not actually querying yet)."}

@app.post("/test-insert")
def test_insert():
    try:
        now = datetime.datetime.utcnow().isoformat()
        data_to_insert = {
            "user_id": "+1234567890",
            "category": "TestCategory",
            "subcategory": "TestSubcategory",
            "item": "Just a test item",
            "timestamp": now
        }

        response = supabase.table("items").insert(data_to_insert).execute()

        # According to official docs, we can check 'response.error'
        if response.error:
            # 'response.error' might be a dictionary describing the error
            raise HTTPException(
                status_code=response.status or 400,
                detail=f"Supabase error: {response.error}"
            )

        # If no error, status should be 201 for an insert
        if response.status >= 400:
            raise HTTPException(
                status_code=response.status,
                detail=f"Supabase returned an unexpected status ({response.status_text}): {response.data}"
            )

        # On success, 'response.data' contains the inserted rows
        return {"status": "success", "data": response.data}

    except APIError as e:
        # supabase-py might raise an exception on deeper errors
        raise HTTPException(status_code=400, detail=f"Supabase APIError: {str(e)}")

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/sms")
async def receive_sms(request: Request) -> Response:
    form_data = await request.form()
    from_number = form_data.get("From")
    body_text = form_data.get("Body")

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

    line1, line2 = lines[0].strip(), lines[1].strip()

    if "," in line1:
        parts = line1.split(",", 1)
        category = parts[0].strip()
        subcategory = parts[1].strip() or None
    else:
        category = line1
        subcategory = None

    if not category or not line2:
        return _twilio_response("Error: Missing category or item.", is_error=True)

    now = datetime.datetime.utcnow().isoformat()
    data_to_insert = {
        "user_id": from_number,
        "category": category,
        "subcategory": subcategory,
        "item": line2.strip(),
        "timestamp": now
    }

    try:
        response = supabase.table("items").insert(data_to_insert).execute()

        if response.error:
            return _twilio_response(
                f"Database error: {response.error}",
                is_error=True
            )

        if response.status >= 400:
            return _twilio_response(
                f"Unexpected status from Supabase: {response.status} {response.status_text}",
                is_error=True
            )

        # success
        subcat_str = subcategory if subcategory else "None"
        return _twilio_response(
            f"Stored:\nCategory: {category}\nSubcategory: {subcat_str}\nItem: {line2}"
        )

    except APIError as e:
        return _twilio_response(f"Supabase APIError: {str(e)}", is_error=True)

    except Exception as e:
        return _twilio_response(f"Unexpected error: {str(e)}", is_error=True)

def _twilio_response(message: str, is_error: bool = False) -> Response:
    twiml_resp = MessagingResponse()
    twiml_resp.message(message)
    return Response(
        content=str(twiml_resp),
        media_type="application/xml",
        status_code=status.HTTP_200_OK
    )

import os
from dotenv import load_dotenv
from fastapi import FastAPI
from supabase import create_client, Client

# 1) Load environment variables from .env
load_dotenv()

# 2) Read environment variables
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# 3) Initialize Supabase client
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

app = FastAPI()

@app.get("/")
def read_root():
    return {"message": "Hello World"}

# Optional: a test endpoint to confirm Supabase connectivity
@app.get("/test-supabase")
def test_supabase():
    # We'll just return a static message for now,
    # but you could do a real query here if you have a table.
    return {"message": "Supabase client ready (not actually querying yet)."}

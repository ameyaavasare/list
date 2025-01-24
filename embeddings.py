import os
import time
from pathlib import Path
from openai import OpenAI
from supabase import create_client, Client
from dotenv import load_dotenv

# Get the project root directory (where .env should be)
root_dir = Path(__file__).parent
dotenv_path = root_dir / '.env'

# Load .env file explicitly from the root directory
load_dotenv(dotenv_path=dotenv_path)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY must be set in environment variables")

client = OpenAI(api_key=OPENAI_API_KEY)

def generate_embedding(text: str, max_retries: int = 3) -> list[float]:
    """Generate embedding with retry logic."""
    for attempt in range(max_retries):
        try:
            response = client.embeddings.create(
                input=text,
                model="text-embedding-3-small"
            )
            embedding = response.data[0].embedding
            if len(embedding) != 1536:  # Validate dimension
                raise ValueError(f"Expected 1536-dimensional embedding, got {len(embedding)}")
            return embedding
        except Exception as e:
            if attempt == max_retries - 1:
                raise
            time.sleep(1)  # Wait before retry

def generate_restaurant_embeddings():
    # 1) Load environment variables
    SUPABASE_URL = os.getenv("SUPABASE_URL")
    SUPABASE_KEY = os.getenv("SUPABASE_KEY")

    if not SUPABASE_URL or not SUPABASE_KEY:
        raise ValueError("Missing Supabase credentials. Check your .env file.")

    # 2) Initialize clients
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

    # 3) Fetch all rows and their categories
    response = supabase.table("items").select("category").execute()

    # Print all unique categories
    categories = [row['category'] for row in response.data if row.get('category')]
    print("\nAll categories found in database:")
    if categories:
        for category in sorted(set(categories)):
            print(f"- {category}")
    else:
        print("No categories found in the database")

    # Now continue with the original query
    response = supabase.table("items").select("*").eq("category", "restaurant").is_("embedding", "null").execute()
    rows = response.data or []

    if not rows:
        print("\nNo restaurant rows need embeddings.")
        return

    print(f"Generating embeddings for {len(rows)} restaurant rows...")

    # 4) For each row, generate an embedding and update 'embedding' column
    for row in rows:
        row_id = row["id"]
        name = row.get("name") or ""
        notes = row.get("notes") or ""

        # Combine name + notes or use whichever text you want to embed
        text_to_embed = f"{name} {notes}".strip()
        if not text_to_embed:
            continue

        # Generate embedding with retry logic
        try:
            vector = generate_embedding(text_to_embed)
        except Exception as e:
            print(f"Error generating embedding for row {row_id}: {e}")
            continue

        # 5) Update Supabase with the embedding vector
        try:
            supabase.table("items") \
                .update({"embedding": vector}) \
                .eq("id", row_id) \
                .execute()
        except Exception as e:
            print(f"Error updating Supabase for row {row_id}: {e}")

    print("Embedding generation complete.")

if __name__ == "__main__":
    generate_restaurant_embeddings()

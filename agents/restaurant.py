import os
import openai
from supabase import Client
from dotenv import load_dotenv

load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
client = openai.OpenAI(api_key=OPENAI_API_KEY)

def handle_restaurant_request(body_text: str, user_id: str, supabase: Client) -> str:
    """
    Updated to handle embedding-based "recommend" queries for restaurants.
      - "list restaurants" => same as before
      - "remove restaurant" => same as before
      - "recommend ..." => uses vector search + LLM RAG
    """
    lower_text = body_text.lower()

    # 1) LIST
    if "list" in lower_text:
        items = supabase.table("items") \
            .select("*") \
            .eq("category", "restaurant") \
            .execute().data
        if not items:
            return "No restaurant items found."

        response_lines = ["All restaurant items:"]
        for i, item in enumerate(items, start=1):
            response_lines.append(f"{i}. {item['name']}")
        return "\n".join(response_lines)

    # 2) REMOVE
    if "remove restaurant" in lower_text:
        remainder = lower_text.split("remove restaurant", 1)[1].strip()
        if not remainder:
            supabase.table("items") \
                .delete() \
                .eq("category", "restaurant") \
                .execute()
            return "All restaurant items removed!"
        else:
            item_name_to_remove = remainder
            supabase.table("items") \
                .delete() \
                .eq("category", "restaurant") \
                .eq("name", item_name_to_remove) \
                .execute()
            return f"Removed restaurant item: {item_name_to_remove}"

    # 3) EMBEDDING-BASED RECOMMEND
    if "recommend" in lower_text:
        # STEP A: Create an embedding of the user's query
        user_query = body_text  # or parse out the substring after "recommend"
        try:
            embed_resp = client.embeddings.create(
                model="text-embedding-3-small",
                input=user_query
            )
            query_vec = embed_resp.data[0].embedding
        except Exception as e:
            return f"Error generating embedding for query: {str(e)}"

        # STEP B: Vector similarity search in Supabase
        #   This snippet uses an RPC call named "match_restaurants" you define in Postgres.
        #   If you haven't created it, see the note below.
        try:
            # We'll request the top 3 matches
            rpc_response = supabase.rpc("match_restaurants", {
                "query_embedding": query_vec,
                "match_count": 3
            }).execute()
            if not rpc_response.data:
                return "No relevant restaurants found via vector search."
            top_rows = rpc_response.data
        except Exception as e:
            return f"Error performing vector search: {str(e)}"

        # STEP C: Build a short prompt for LLM with top matches
        #   Include user query + the returned restaurants
        context_lines = []
        for i, row in enumerate(top_rows, start=1):
            nm = row["name"]
            notes = row["notes"] or "No notes available"
            context_lines.append(f"{i}) {nm}: {notes}")

        prompt_for_llm = (
            f"User Query: {user_query}\n\n"
            f"Here are the top matching restaurants:\n"
            + "\n".join(context_lines)
            + "\n\nPlease provide a short recommendation that best fits the user's request."
        )

        # STEP D: Feed this into OpenAI for final RAG response
        try:
            completion = openai.Completion.create(
                model="text-davinci-003",  # or gpt-3.5-turbo etc.
                prompt=prompt_for_llm,
                max_tokens=120,
                temperature=0.7
            )
            final_answer = completion.choices[0].text.strip()
            return final_answer
        except Exception as e:
            return f"Error calling LLM for final recommendation: {str(e)}"

    # If none matched
    return (
        "Not sure what you want to do with restaurants.\n"
        "You can say:\n"
        "  'list restaurants' (to list everything),\n"
        "  'remove restaurant' (remove all items),\n"
        "  'remove restaurant [item]' (remove a single item),\n"
        "  or 'recommend a fancy place' for an embedding-based recommendation."
    )

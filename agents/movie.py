import re
from supabase import Client

def handle_movie_request(body_text: str, user_id: str, supabase: Client) -> str:
    """
    Processes movie-related requests:
      - "list movies" -> lists ALL movie items (for ALL users).
      - "remove movie" -> deletes ALL movie items.
      - "remove movie [name]" -> deletes a single movie (case-insensitive match).
      - "recommend me an action movie" -> naive approach, searching 'notes' column for keywords.
    """
    lower_text = body_text.lower()

    # 1) LIST
    if "list movies" in lower_text:
        items = supabase.table("items") \
            .select("*") \
            .eq("category", "movie") \
            .execute().data

        if not items:
            return "No movies found."

        response_lines = ["All movies:"]
        for i, item in enumerate(items, start=1):
            response_lines.append(f"{i}. {item['name']}")
        return "\n".join(response_lines)

    # 2) REMOVE
    if "remove movie" in lower_text:
        remainder = lower_text.split("remove movie", 1)[1].strip()
        if not remainder:
            # Remove ALL
            supabase.table("items") \
                .delete() \
                .eq("category", "movie") \
                .execute()
            return "All movies removed!"
        else:
            # Remove single (case-insensitive)
            matching_items = supabase.table("items") \
                .select("*") \
                .eq("category", "movie") \
                .ilike("name", remainder) \
                .execute()
            if matching_items.data:
                supabase.table("items") \
                    .delete() \
                    .eq("category", "movie") \
                    .ilike("name", remainder) \
                    .execute()
                return f"Removed movie: {remainder}"
            else:
                return f"No movie found matching: {remainder}"

    # 3) RECOMMEND (e.g. "recommend me an action movie")
    match = re.search(r"recommend me a?n?\s+(.*?)\s+movie", lower_text)
    if match:
        genre = match.group(1).strip()
        # search 'notes' column for that genre, ignoring case
        items = supabase.table("items") \
            .select("*") \
            .eq("category", "movie") \
            .ilike("notes", f"%{genre}%") \
            .execute().data

        if not items:
            return f"No recommendations found for {genre} movies."
        else:
            response_lines = [f"Recommended {genre} movie(s):"]
            for i, item in enumerate(items, start=1):
                response_lines.append(f"{i}. {item['name']}")
            return "\n".join(response_lines)

    # Fallback
    return (
        "Not sure what you want to do with movies.\n"
        "Try:\n"
        "  'list movies' (to list everything),\n"
        "  'remove movie' (remove all),\n"
        "  'remove movie [title]' (remove one),\n"
        "  'recommend me an action movie' (recommendation)."
    )

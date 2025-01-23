from supabase import Client

def handle_tv_request(body_text: str, user_id: str, supabase: Client) -> str:
    """
    Processes TV-related requests:
      1) 'list tv' or 'list tv shows' -> lists ALL tv items (for all users).
      2) 'remove tv' -> deletes ALL tv items for all users.
      3) 'remove tv [name]' -> deletes a single tv item by matching [name].
      4) 'recommend tv' -> returns a simple recommendation list.
    """
    lower_text = body_text.lower()

    # 1) LIST TV SHOWS
    if "list tv" in lower_text or "list tv shows" in lower_text:
        items = supabase.table("items") \
            .select("*") \
            .eq("category", "tv") \
            .execute().data

        if not items:
            return "No TV items found."

        response_lines = ["All TV items:"]
        for i, item in enumerate(items, start=1):
            response_lines.append(f"{i}. {item['name']}")
        return "\n".join(response_lines)

    # 2) REMOVE TV
    if "remove tv" in lower_text:
        # e.g. "remove tv breaking bad"
        remainder = lower_text.split("remove tv", 1)[1].strip()

        if not remainder:
            # If there's nothing after, remove ALL tv items
            supabase.table("items") \
                .delete() \
                .eq("category", "tv") \
                .execute()
            return "All TV items removed!"
        else:
            # There's some text after "remove tv"
            item_name_to_remove = remainder
            supabase.table("items") \
                .delete() \
                .eq("category", "tv") \
                .eq("name", item_name_to_remove) \
                .execute()
            return f"Removed TV item: {item_name_to_remove}"

    # 3) RECOMMEND TV
    if "recommend tv" in lower_text:
        return (
            "Here are a few TV recommendations:\n"
            "- Breaking Bad\n"
            "- The Office\n"
            "- Stranger Things\n"
        )

    # If no known command matched
    return (
        "Not sure what you want to do with TV.\n"
        "You can say:\n"
        "  'list tv shows' (to list everything),\n"
        "  'remove tv' (remove all TV items),\n"
        "  'remove tv [show]' (remove a single item), or\n"
        "  'recommend tv' for recommendations."
    )

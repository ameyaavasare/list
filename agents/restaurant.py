from supabase import Client

def handle_restaurant_request(body_text: str, user_id: str, supabase: Client) -> str:
    """
    Processes restaurant-related requests, mirroring grocery.py logic:
      1) 'list' -> lists ALL restaurant items (from ALL users).
      2) 'remove restaurant' -> deletes ALL restaurant items.
      3) 'remove restaurant [name]' -> deletes a single restaurant item by matching [name].
      4) 'recommend ...' -> naive placeholder to search for keywords in 'notes' (case-insensitive).
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

    # 3) RECOMMEND
    if "recommend" in lower_text:
        # Look for known keywords like 'fancy', 'quiet', 'relaxed'.
        keywords = []
        if "fancy" in lower_text:
            keywords.append("fancy")
        if "quiet" in lower_text:
            keywords.append("quiet")
        if "relaxed" in lower_text:
            keywords.append("relaxed")

        if not keywords:
            return (
                "We need a preference to recommend a restaurant. "
                "For example: 'recommend a fancy place'."
            )

        recommended_items = []
        for kw in keywords:
            # Use .ilike(...) for case-insensitive matching
            results = supabase.table("items") \
                .select("*") \
                .eq("category", "restaurant") \
                .ilike("notes", f"%{kw}%") \
                .execute().data
            if results:
                recommended_items.extend(results)

        if recommended_items:
            response_lines = [
                f"Recommended restaurants (found {len(recommended_items)} matches):"
            ]
            for i, item in enumerate(recommended_items, start=1):
                notes = item.get("notes", "N/A")
                response_lines.append(f"{i}. {item['name']} (notes: {notes})")
            return "\n".join(response_lines)
        else:
            return f"No restaurants found matching your preference(s): {', '.join(keywords)}"

    # If none matched
    return (
        "Not sure what you want to do with restaurants.\n"
        "You can say:\n"
        "  'list restaurants' (to list everything),\n"
        "  'remove restaurant' (remove all items),\n"
        "  'remove restaurant [item]' (remove a single item),\n"
        "  or 'recommend a fancy place' for a naive recommendation."
    )

from supabase import Client

def handle_grocery_request(body_text: str, user_id: str, supabase: Client) -> str:
    """
    Processes grocery-related requests:
      1) 'list' -> lists ALL grocery items (from ALL users).
      2) 'remove grocery' -> deletes ALL grocery items from the database (ALL users).
      3) 'remove grocery [name]' -> deletes a single grocery item matching [name].
    """
    lower_text = body_text.lower()

    # 1) LIST all grocery items for all users
    if "list" in lower_text:
        items = supabase.table("items") \
            .select("*") \
            .eq("category", "grocery") \
            .execute().data

        if not items:
            return "No grocery items found for anyone."

        response_lines = ["All grocery items (all users):"]
        for i, item in enumerate(items, start=1):
            response_lines.append(f"{i}. {item['name']} (User: {item['user_id']})")
        return "\n".join(response_lines)

    # 2) REMOVE logic
    if "remove grocery" in lower_text:
        # We'll split on "remove grocery" and see if there's an item name after
        remainder = lower_text.split("remove grocery", 1)[1].strip()

        if not remainder:
            # If there's nothing after, remove ALL grocery items for ALL users
            supabase.table("items") \
                .delete() \
                .eq("category", "grocery") \
                .execute()
            return "All grocery items removed for all users!"
        else:
            # e.g. "remove grocery bananas"
            # We'll do an exact match on the 'name' column
            item_name_to_remove = remainder
            supabase.table("items") \
                .delete() \
                .eq("category", "grocery") \
                .eq("name", item_name_to_remove) \
                .execute()
            return f"Removed grocery item: {item_name_to_remove}"

    # If we reach here, we didn't match any known commands
    return (
        "Not sure what you want to do with groceries.\n"
        "You can say:\n"
        "  'list groceries' (to list everything for all users),\n"
        "  'remove grocery' (to remove all grocery items),\n"
        "  or 'remove grocery [item]' (to remove a single item)."
    )

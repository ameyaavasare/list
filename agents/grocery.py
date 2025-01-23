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
            .eq("category", "Grocery") \
            .execute().data

        if not items:
            return "No grocery items found for anyone."

        response_lines = ["All grocery items (all users):"]
        for i, item in enumerate(items, start=1):
            response_lines.append(f"{i}. {item['name']} (User: {item['user_id']})")
        return "\n".join(response_lines)

    # 2) REMOVE logic
    # Check if user typed exactly "remove grocery" or "remove grocery something..."
    if "remove grocery" in lower_text:
        # Try to parse an item after "remove grocery"
        # e.g. "remove grocery bananas"
        # We'll split on "remove grocery" and see what's left
        remainder = lower_text.split("remove grocery", 1)[1].strip()  # text after 'remove grocery'
        
        if not remainder:
            # If there's nothing after, remove ALL grocery items (all users)
            supabase.table("items") \
                .delete() \
                .eq("category", "Grocery") \
                .execute()
            return "All grocery items removed for all users!"
        else:
            # There's some text after "remove grocery"
            # We'll treat that as the name of the item to remove
            item_name_to_remove = remainder  # e.g. "bananas"
            # The original item name stored in the DB is case-sensitive
            # We do an exact match for simplicity
            supabase.table("items") \
                .delete() \
                .eq("category", "Grocery") \
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

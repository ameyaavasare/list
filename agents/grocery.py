from supabase import Client

def handle_grocery_request(body_text: str, user_id: str, supabase: Client) -> str:
    """
    Processes grocery-related requests:
      1) 'list' -> lists ALL grocery items (from ALL users), showing just item names.
      2) 'remove grocery' -> deletes ALL grocery items for ALL users.
      3) 'remove grocery [name]' -> deletes a single grocery item by matching [name].
    """
    lower_text = body_text.lower()

    # 1) LIST all grocery items for all users
    if "list" in lower_text:
        items = supabase.table("items") \
            .select("*") \
            .eq("category", "grocery") \
            .execute().data

        if not items:
            return "No grocery items found."

        response_lines = ["All grocery items:"]
        for i, item in enumerate(items, start=1):
            # Only show the item name, not the user
            response_lines.append(f"{i}. {item['name']}")
        return "\n".join(response_lines)

    # 2) REMOVE logic
    if "remove grocery" in lower_text:
        remainder = lower_text.split("remove grocery", 1)[1].strip()

        if not remainder:
            # If there's nothing after, remove ALL grocery items
            result = supabase.table("items") \
                .delete() \
                .eq("category", "grocery") \
                .execute()
            return "All grocery items removed!"
        else:
            # There's some text after "remove grocery"
            # First get the item with case-insensitive search
            items = supabase.table("items") \
                .select("*") \
                .eq("category", "grocery") \
                .ilike("name", remainder) \
                .execute()
            
            if items.data:
                # If we found matching items, delete them
                supabase.table("items") \
                    .delete() \
                    .eq("category", "grocery") \
                    .ilike("name", remainder) \
                    .execute()
                return f"Removed grocery item: {remainder}"
            else:
                return f"No grocery item found matching: {remainder}"

    # If we reach here, we didn't match any known commands
    return (
        "Not sure what you want to do with groceries.\n"
        "You can say:\n"
        "  'list groceries' (to list everything),\n"
        "  'remove grocery' (remove all items),\n"
        "  or 'remove grocery [item]' (remove a single item)."
    )

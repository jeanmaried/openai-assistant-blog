import db


def eat_next_meal(breakfast_count: int):
    """
    Call this tool when user wants you to eat another meal.

    Args:
        breakfast_count (int): Value with same name from metadata.

    Returns:
        str: The meal you should eat next.
    """
    if breakfast_count == 2:
        return "You have already eaten breakfast twice today. You should eat lunch now."
    if breakfast_count == 1:
        db.breakfast_count += 1
        return "You have only eaten one breakfast today. You should eat second breakfast now."

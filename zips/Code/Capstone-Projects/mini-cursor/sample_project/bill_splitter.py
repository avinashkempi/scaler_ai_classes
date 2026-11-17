"""
bill_splitter.py - split a restaurant bill between friends.

Author: Shivank Agrawal
Project: Mini Cursor sample workspace - Future with Shivank
"""


def split_bill(total: float, people: int, tip_percent: float = 10) -> float:
    """Return how much each person pays, tip included, rounded to 2 decimals.

    Example: a Rs 1,000 dinner for 4 friends with a 10% tip -> 275.0 each.
    """
    if people <= 0:
        raise ValueError("people must be at least 1")
    tip = total * tip_percent
    return round((total + tip) / people, 2)

import re


def convert_to_ref(price_string, key_ref_price):
    """
    Convert a Backpack.tf listing price into refined metal.

    Examples:
        "2 keys, 28.11 ref"
        "1 key"
        "58 ref"
        "3 keys, 0.33 ref"
    """

    if price_string is None:
        return None

    price_string = price_string.lower().strip()

    total_ref = 0.0

    # ----------------------------
    # Keys
    # ----------------------------
    key_match = re.search(r"(\d+(?:\.\d+)?)\s*keys?", price_string)

    if key_match:
        num_keys = float(key_match.group(1))
        total_ref += num_keys * key_ref_price

    # ----------------------------
    # Refined Metal
    # ----------------------------
    ref_match = re.search(r"(\d+(?:\.\d+)?)\s*ref", price_string)

    if ref_match:
        num_ref = float(ref_match.group(1))
        total_ref += num_ref

    # ----------------------------
    # Future support
    # ----------------------------
    # Reclaimed Metal
    # Scrap Metal

    return round(total_ref, 2)


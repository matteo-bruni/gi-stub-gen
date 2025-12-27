from gi.repository import Gst


def get_fraction_value(obj):
    """Get the fraction value from a Gst.Fraction object."""
    try:
        if not isinstance(obj, Gst.Fraction):
            return None
        return f"Gst.Fraction(num={obj.num}, denom={obj.denom})"
    except Exception:
        return None

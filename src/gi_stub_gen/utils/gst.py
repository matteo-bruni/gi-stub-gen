import gi

gi.require_version("Gst", "1.0")


def get_fraction_value(obj):
    """Get the fraction value from a Gst.Fraction object."""
    from gi.repository import Gst

    try:
        if not isinstance(obj, Gst.Fraction):
            return None
        return f"Gst.Fraction(num={obj.num}, denom={obj.denom})"
    except Exception:
        return None

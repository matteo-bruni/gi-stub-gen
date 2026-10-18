"""Type-check against the regenerated stubs; run only with initialized Gst."""

from typing import assert_type

import gi

gi.require_version("Gst", "1.0")
from gi.repository import Gst  # noqa: E402

Gst.init(None)
fraction = Gst.Fraction(num=3, denom=4)
assert_type(fraction, Gst.Fraction)
assert_type(Gst.Fraction(3), Gst.Fraction)
assert_type(fraction.num, int)
assert_type(fraction.denom, int)
assert_type(fraction * 2, Gst.Fraction)
assert_type(2 * fraction, Gst.Fraction)
assert_type(fraction * Gst.Fraction(2, 3), Gst.Fraction)
assert_type(fraction / 2, Gst.Fraction)
assert_type(fraction / Gst.Fraction(2, 3), Gst.Fraction)
assert_type(2 / fraction, Gst.Fraction)
assert_type(float(fraction), float)

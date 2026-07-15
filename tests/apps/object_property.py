import gi
from typing import TYPE_CHECKING, assert_type

gi.require_version("GObject", "2.0")
from gi.repository import GObject


class TestObject(GObject.Object):
    def set_int_prop(self, value: int) -> None:
        self._int_prop = value

    @GObject.Property(
        type=int,
        default=100,
        setter=set_int_prop,
        blurb="An integer property",
    )
    def int_prop(self) -> int:
        return self._int_prop

    @GObject.Property(
        type=str,
        default="default-string",
        blurb="A string property",
    )
    def str_prop(self) -> str:
        return self._str_prop

    @str_prop.setter
    def str_prop(self, value: str) -> None:
        self._str_prop = value

    def __init__(self) -> None:
        super().__init__()
        # Inizializziamo i valori interni
        self._int_prop = 100
        self._str_prop = "Ciao Mondo"


class PropertyTypingCases(GObject.Object):
    _weight = 0.5

    def set_weight(self, value: float) -> None:
        self._weight = value

    @GObject.Property(
        type=float,
        nick="weight",
        blurb="Inference weight",
        default=0.5,
        minimum=0.0,
        maximum=1.0,
        flags=GObject.ParamFlags.READWRITE,
        setter=set_weight,
    )
    def weight(self) -> float:
        return self._weight

    @GObject.Property
    def direct(self) -> int:
        return 1

    @GObject.Property()
    def empty(self) -> str:
        return "value"

    assigned = GObject.Property(type=float, default=0.0)

    @GObject.Property(type=int)
    def chained(self) -> int:
        return 1

    @chained.setter
    def chained(self, value: int) -> None:
        pass

    def check_types(self) -> None:
        assert_type(self.weight, float)
        assert_type(self.direct, int)
        assert_type(self.empty, str)
        assert_type(self.assigned, float)
        self.weight = 0.75
        consume_float(self.weight)


def consume_float(value: float) -> None:
    pass


if TYPE_CHECKING:
    assert_type(PropertyTypingCases.weight, GObject.Property[float])


if __name__ == "__main__":
    obj = TestObject()
    print(f"--- Test on object: {obj} ---")
    val_int = obj.get_property("int-prop")
    val_str = obj.get_property("str-prop")

    print("\n1. Call: obj.get_property('int-prop')")
    print(f"   Result: {val_int} (Type: {type(val_int)})")

    print("\n2. Call: obj.get_property('str-prop')")
    print(f"   Result: '{val_str}' (Type: {type(val_str)})")
    print("\n3. Setting new values using obj.set_property()")
    obj.set_property("int-prop", 250)
    obj.set_property("str-prop", "New Value")
    print("   New values set.")
    val_int_new = obj.get_property("int-prop")
    val_str_new = obj.get_property("str-prop")
    print(f"   Updated int-prop: {val_int_new} (Type: {type(val_int_new)})")
    print(f"   Updated str-prop: '{val_str_new}' (Type: {type(val_str_new)})")

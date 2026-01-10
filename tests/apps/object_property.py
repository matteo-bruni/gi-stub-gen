import gi

gi.require_version("GObject", "2.0")
from gi.repository import GObject


class TestObject(GObject.Object):
    def set_int_prop(self, value):
        self._int_prop = value

    @GObject.Property(
        type=int,
        default=100,
        setter=set_int_prop,
        blurb="An integer property",
    )
    def int_prop(self):
        return self._int_prop

    @GObject.Property(
        type=str,
        default="default-string",
        blurb="A string property",
    )
    def str_prop(self):
        return self._str_prop

    @str_prop.setter
    def str_prop(self, value):
        self._str_prop = value

    def __init__(self):
        super().__init__()
        # Inizializziamo i valori interni
        self._int_prop = 100
        self._str_prop = "Ciao Mondo"


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

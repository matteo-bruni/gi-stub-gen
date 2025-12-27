import sys
import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk  # noqa: E402


class TestAppWindow(Gtk.ApplicationWindow):
    """
    Gtk.ApplicationWindow -> Gtk.Window -> Gtk.Widget -> GObject.InitiallyUnowned
    """

    def __init__(self, app: Gtk.Application):
        super().__init__(
            application=app,
            title="GTK4 Stub Test",
            default_width=400,
            default_height=200,
        )

        self.box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        self.set_child(self.box)

        self.btn_simple = Gtk.Button(label="Callback Semplice")
        self.box.append(self.btn_simple)

        self.btn_data = Gtk.Button(label="Callback con Dati")
        self.box.append(self.btn_data)

        self.btn_simple.connect("clicked", self.on_click_simple)
        self.btn_data.connect("clicked", self.on_click_with_data, "DatoSegreto")
        self.btn_simple.connect("clicked", lambda w: print("Lambda click"))

    # --- DEFINIZIONE CALLBACK ---

    def on_click_simple(self, button: Gtk.Button) -> None:
        """
        signature: (widget) -> None
        """
        print(f"Simple click on {button}")

    def on_click_with_data(self, button: Gtk.Button, data: str) -> None:
        """
        signature: (widget, data) -> None
        chdeck varargs (*user_data).
        """
        print(f"Click with data: {data}")


def on_activate(app: Gtk.Application) -> None:
    win = TestAppWindow(app)
    win.present()


def main():
    app = Gtk.Application(application_id="com.example.stubtest")
    app.connect("activate", on_activate)

    if __name__ == "__main__":
        app.run(sys.argv)


if __name__ == "__main__":
    main()

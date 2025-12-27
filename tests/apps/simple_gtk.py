import sys
import gi

# Richiediamo esplicitamente GTK 4.0
gi.require_version("Gtk", "4.0")
from gi.repository import Gtk, GLib, Gio  # noqa: E402


class TestAppWindow(Gtk.ApplicationWindow):
    """
    Testiamo l'ereditarietà in GTK4:
    Gtk.ApplicationWindow -> Gtk.Window -> Gtk.Widget -> GObject.InitiallyUnowned
    """

    def __init__(self, app: Gtk.Application):
        # 1. TEST COSTRUTTORE E KWARGS
        # GTK4 richiede spesso la property 'application' nel costruttore
        super().__init__(
            application=app,
            title="GTK4 Stub Test",
            default_width=400,
            default_height=200,
        )

        self.box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        self.set_child(self.box)

        # 3. TEST WIDGET E METODI NUOVI
        # In GTK4 Box usa .append(), non pack_start
        self.btn_simple = Gtk.Button(label="Callback Semplice")
        self.box.append(self.btn_simple)

        self.btn_data = Gtk.Button(label="Callback con Dati")
        self.box.append(self.btn_data)

        # --- TEST CRITICO: connect e Union Trick ---
        # Questo verifica che il tuo stub di `connect` accetti sia
        # callback rigorose (Protocol) che funzioni python normali (Callable)

        # CASO A: Callback Semplice (Input: solo widget)
        # Deve matchare Callable[..., None]
        self.btn_simple.connect("clicked", self.on_click_simple)

        # CASO B: Callback con User Data (Input: widget + str)
        # Deve matchare Callable[..., None] e gestire *user_data nello stub
        self.btn_data.connect("clicked", self.on_click_with_data, "DatoSegreto")

        # CASO C: Lambda (Input: widget)
        # Testiamo se accetta funzioni anonime
        self.btn_simple.connect("clicked", lambda w: print("Lambda click"))

    # --- DEFINIZIONE CALLBACK ---

    def on_click_simple(self, button: Gtk.Button) -> None:
        """
        Firma: (widget) -> None
        Se lo stub richiedesse rigorosamente *args, qui Pylance darebbe errore.
        Con l'Union Trick, questo è valido.
        """
        print(f"Click semplice su {button}")

    def on_click_with_data(self, button: Gtk.Button, data: str) -> None:
        """
        Firma: (widget, data) -> None
        Verifica che lo stub di connect supporti i varargs (*user_data).
        """
        print(f"Click con dati: {data}")


def on_activate(app: Gtk.Application) -> None:
    win = TestAppWindow(app)
    # GTK4 usa present(), show_all() non esiste più
    win.present()


def main():
    # GTK4 incoraggia l'uso di Gtk.Application
    app = Gtk.Application(application_id="com.example.stubtest")
    app.connect("activate", on_activate)

    # Esecuzione (per static analysis basta che il codice sia raggiungibile)
    if __name__ == "__main__":
        app.run(sys.argv)


if __name__ == "__main__":
    main()

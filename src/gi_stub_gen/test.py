import gi

gi.require_version("GObject", "2.0")
gi.require_version("Gst", "1.0")
gi.require_version("GioUnix", "2.0")
gi.require_version("GIRepository", "3.0")
from gi.repository import Gst
from gi.repository import GObject
from gi.repository import GIRepository

# Gst.init()


# from gi._gi import Repository

# repo = Repository.get_default()


repo = GIRepository.Repository.new()
# Caricamento
repo.require("Gst", "1.0", GIRepository.RepositoryLoadFlags.NONE)
# Cerca per nome
# info = repo.find_by_name("Gtk", "Button")


print(repo.find_by_name("GObject", "boxed_copy"))
print(repo.find_by_name("Gst", "AllocationParams"))
# print(repo.find_by_name("Gst", "AllocationParams.align"))
# print(repo.find_by_name("Gst", "AllocationParams.align"))

# repo.find_by_gtype(GI.Boxed.__gtype__)

# GIRepository.Repository.new().find_by_gtype(GI.Boxed.__gtype__)

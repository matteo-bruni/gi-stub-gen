from __future__ import annotations

import gi
import gi._gi as GI  # type: ignore
from gi._gi import Repository  # type: ignore

repository = Repository.get_default()

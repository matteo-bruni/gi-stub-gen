from __future__ import annotations

import re
import logging


logger = logging.getLogger(__name__)


def translate_docstring(raw_text: str | None, namespace: str) -> str:
    """
    Complete pipeline for processing docstrings:
    1. Semantic translation from C/GObject conventions to Python (e.g., NULL -> None).
    2. Syntactic sanitization to ensure valid Python syntax in .pyi files.

    Args:
        raw_text: The raw documentation string extracted from the GIR/XML.
        namespace: The current namespace (e.g., "Gst", "GLib") used to resolve references.

    Returns:
        A cleaned, Python-friendly docstring ready to be written to the stub file.
    """
    if not raw_text:
        return ""

    # --- PHASE 1: Semantic Translation (C -> Python) ---
    # We modify the content to look "Pythonic" before escaping special characters.

    # 1. Decode common XML entities (since lxml might leave some encoded)
    text = raw_text.replace("&lt;", "<").replace("&gt;", ">").replace("&amp;", "&")

    # 2. Translate fundamental values
    # Use word boundaries (\b) to avoid replacing substrings (e.g., ANULL -> ANone is wrong)
    text = re.sub(r"\bNULL\b", "None", text)
    text = re.sub(r"\bTRUE\b", "True", text)
    text = re.sub(r"\bFALSE\b", "False", text)

    # 3. Parameters: Convert @param_name to `param_name`
    # C conventions use @ for parameters; Python usually uses backticks.
    text = re.sub(r"@(\w+)", r"`\1`", text)

    # 4. Class References: Convert #GstBin to Gst.Bin or Bin
    # The pattern matches #NamespaceClass.
    def replace_class_ref(match):
        full_name = match.group(1)  # e.g., "GstBin"

        # Check if the class belongs to the current namespace
        if full_name.startswith(namespace):
            # Remove the namespace prefix (GstBin -> Bin)
            # This makes the docstring cleaner when reading inside the Gst module.
            return f"{namespace}.{full_name[len(namespace) :]}"

        # If it belongs to another namespace, keep the full name or add logic here
        return full_name

    text = re.sub(r"#([A-Z][a-zA-Z0-9]+)", replace_class_ref, text)

    # 5. Constants: Convert %GST_STATE_PLAYING to Gst.State.PLAYING
    # Heuristic: If it starts with the uppercase Namespace, allow pythonizing it.
    ns_upper = namespace.upper() + "_"

    def replace_constant(match):
        const_name = match.group(1)  # e.g., "GST_STATE_PLAYING"

        if const_name.startswith(ns_upper):
            # Strip the prefix: GST_STATE_PLAYING -> STATE_PLAYING
            # (Refining this to 'State.PLAYING' requires enum introspection,
            # so keeping it simple is safer for now).
            return f"{namespace}.{const_name[len(ns_upper) :]}"
        return const_name

    text = re.sub(r"%([A-Z0-9_]+)", replace_constant, text)

    # 6. Functions: Convert gst_element_link() to `Gst.element_link`
    # We explicitly keep the Namespace prefix to avoid ambiguity and ensure
    # the link points to the valid procedural function in the module.
    c_prefix = namespace.lower() + "_"  # e.g., "gst_"

    def replace_func_call(match):
        func_name = match.group(1)  # e.g., "gst_debug_add_ring_buffer_logger"

        # Check if it starts with the standard C prefix
        if func_name.startswith(c_prefix):
            # Remove "gst_" -> "debug_add_ring_buffer_logger"
            suffix = func_name[len(c_prefix) :]

            # Reconstruct as "Gst.debug_add_ring_buffer_logger"
            return f"`{namespace}.{suffix}`"

        # If it's a system function (e.g. printf) or unknown prefix, leave it as is
        return f"`{func_name}`"

    text = re.sub(r"\b(\w+)\(\)", replace_func_call, text)

    # --- PHASE 2: Syntactic Sanitization ---
    # Now we ensure the string doesn't break the Python file syntax.

    # 7. Remove "orphan" backslashes
    # Finds a backslash NOT followed by a letter, number, or another backslash.
    # This cleans up typos in C docs like "function\()" -> "function()".
    text = re.sub(r"\\(?=[^a-zA-Z0-9\\])", "", text)

    # 8. Escape backslashes
    # We double the backslashes to ensure they are treated as literal characters
    # inside the Python string (e.g., C:\Path -> C:\\Path).
    text = text.replace("\\", "\\\\")

    # 9. Escape triple quotes
    # Prevents the docstring from closing prematurely if the text contains """.
    text = text.replace('"""', r"\"\"\"")

    return text.strip()


def make_safe_docstring(text: str | None) -> str:
    """
    Cleans up the raw docstring from GIR to make it safe for Python.
    Escapes backslashes and handles quotes.
    """
    if not text:
        return ""

    # Find a backslash not followed by a letter, number or another backslash
    # Transform "function\()" -> "function()"
    # Transform "set_\*"    -> "set_*"
    # Ignore    "C:\User"
    text = re.sub(r"\\(?=[^a-zA-Z0-9\\])", "", text)

    # "C:\user" -> "C:\\user"
    text = text.replace("\\", "\\\\")

    # '''triple quotes''' -> '\"\"\"triple quotes\"\"\"'
    text = text.replace('"""', r"\"\"\"")

    return text

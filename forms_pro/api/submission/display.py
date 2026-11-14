"""Display values for answers, shared by the answers table (C5) and the lead note (C2).

Rules: Multiselect as a comma list, Check/Switch/Checkbox as Yes/No, Attach as the
file name (never a URL), empty as "".
"""

import json
from typing import Any

_YES_NO_TYPES = ("Check", "Checkbox", "Switch")


def file_name_of(value: Any) -> str:
    """Last path segment of a stored file URL or name (never the public/private URL itself)."""
    text = str(value or "").strip()
    return text.rsplit("/", 1)[-1] if text else ""


def display_value(fieldtype: str, value: Any) -> str:
    if value is None or value == "" or value == []:
        return ""
    if fieldtype in _YES_NO_TYPES:
        return "Yes" if str(value).strip().lower() in ("1", "true", "yes") else "No"
    if fieldtype == "Attach":
        return file_name_of(value)
    if fieldtype == "Multiselect":
        items = value
        if isinstance(value, str):
            try:
                items = json.loads(value)
            except (json.JSONDecodeError, TypeError):
                items = [value]
        if isinstance(items, (list, tuple)):
            return ", ".join(str(i) for i in items if i not in (None, ""))
        return str(items)
    return str(value)

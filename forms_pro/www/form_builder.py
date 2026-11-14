import re

import frappe

# The www page name must stay form_builder.py (underscore): Frappe loads a page's Python file
# under the underscore name of form-builder.html (see ROUTE-CHANGES.md, correction 2026-11-14).

no_cache = 1

SCRIPT_TAG_PATTERN = re.compile(r"\<script[^<]*\</script\>")
CLOSING_SCRIPT_TAG_PATTERN = re.compile(r"</script\>")

PUBLIC_FORM_PREFIX = "/f/"
EDIT_MARKER = "/edit/"
NOT_FOUND_TEMPLATE = "forms_pro/templates/form_not_found.html"


def get_context(context):
    csrf_token = frappe.sessions.get_csrf_token()
    frappe.db.commit()  # nosemgrep: frappe-semgrep-rules.rules.frappe-manual-commit - required to persist CSRF token before page render
    # developer mode
    context.is_developer_mode = frappe.conf.developer_mode
    context.csrf_token = csrf_token

    # /f/<form route> for a form that does not exist (or is not published) is a real 404 with
    # a friendly page, not the app shell with HTTP 200.
    path = _request_path()
    if path.startswith(PUBLIC_FORM_PREFIX) and not public_form_exists(path):
        context.http_status_code = 404
        context.template = NOT_FOUND_TEMPLATE


def _request_path() -> str:
    request = getattr(frappe.local, "request", None)
    return (getattr(request, "path", "") or "").split("?", 1)[0]


def public_form_exists(path: str) -> bool:
    """True when `path` (/f/<route> or /f/<route>/edit/<submission>) names a published Form."""
    rest = path[len(PUBLIC_FORM_PREFIX) :].strip("/")
    if not rest:
        return False
    candidates = [rest]
    if EDIT_MARKER in f"/{rest}/":
        # /f/<route>/edit/<submissionName>: the route is everything before the last /edit/
        candidates.append(rest.rsplit("/edit/", 1)[0])
    return any(frappe.db.exists("Form", {"route": route, "is_published": 1}) for route in candidates if route)

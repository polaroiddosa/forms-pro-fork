"""Lead bridge: a Submitted response becomes a CRM Lead (contract C2).

DOCUMENTED CONTRACT (the rule, no builder control)
==================================================
Automatic field mapping, by question TYPE, never by fieldname:
  * the first Phone question          -> CRM Lead `mobile_no`
  * the first Email question          -> CRM Lead `email`
  * the first Short answer (Data) question whose label contains "name"
    (case-insensitive)                -> CRM Lead `first_name`
  * if no such question or no answer  -> `first_name` is the form title
  * every other answer appears ONLY in the response note.
Fields a visitor could tamper with are never read from the payload: `status`,
`lead_owner`, consent and `source` are set here only.
Set on every lead (academy intake script, ported):
  consent_status = "Given", consent_date = now, consent_source = "Web Form: <title>",
  source = "Website form" (always), status = "New" only if empty,
  campaign = form title only if empty, lead_owner cleared so the CRM's existing
  round-robin assignment rule assigns a counsellor.
After the lead: duplicate flag (exact `mobile_no` match, comment on both leads),
a note "Form answers: <title>" with every question and answer (HTML-escaped),
private files attached to the lead plus a comment per file.

Sources: academy Server Scripts saved in crm-kit/webform-archive/server-scripts/
(TA_Web_Form_lead_intake.py, _duplicate_flag.py, _response_note.py, _files.py,
_file_comment.py).
"""

import html

import frappe

from forms_pro.forms_pro.doctype.form_field.form_field import _DISPLAY_ONLY_FIELDTYPES

from .display import display_value
from .uploads import ParsedUpload, store_private_file

LEAD_DOCTYPE = "CRM Lead"
SOURCE_VALUE = "Website form"


def bridge_available() -> bool:
    return bool(frappe.db.exists("DocType", LEAD_DOCTYPE))


def _has_value(value) -> bool:
    return value is not None and value != "" and value != []


def map_lead_fields(form, answers: dict) -> dict:
    """Apply the documented mapping. `answers` is {fieldname: value} (already whitelisted)."""
    mapped: dict = {}
    phone_done = email_done = name_done = False
    for field in form.fields:
        label = (field.label or "").lower()
        value = answers.get(field.fieldname)
        text = str(value).strip() if _has_value(value) and not isinstance(value, (list, dict)) else ""
        if field.fieldtype == "Phone" and not phone_done:
            phone_done = True
            if text:
                mapped["mobile_no"] = text
        elif field.fieldtype == "Email" and not email_done:
            email_done = True
            if text:
                mapped["email"] = text
        elif field.fieldtype == "Data" and "name" in label and not name_done:
            name_done = True
            if text:
                mapped["first_name"] = text
    if not mapped.get("first_name"):
        mapped["first_name"] = str(form.title or form.name)[:140]
    return mapped


def _esc(text) -> str:
    # unescape first so an already-escaped value is not escaped twice (academy behaviour)
    return html.escape(html.unescape(str(text)), quote=False)


def build_response_note(form, answers: dict, uploads: dict[str, ParsedUpload]) -> str:
    """HTML paragraphs, one per answered question, in form order."""
    lines = []
    for field in form.fields:
        if field.fieldtype in _DISPLAY_ONLY_FIELDTYPES:
            continue
        if field.fieldtype == "Attach":
            upload = uploads.get(field.fieldname)
            shown = upload.file_name if upload else ""
        else:
            shown = display_value(field.fieldtype, answers.get(field.fieldname))
        if shown == "":
            continue
        lines.append(f"<p><b>{_esc(field.label or field.fieldname)}</b><br>{_esc(shown)}</p>")
    return "".join(lines)


def _ensure_source() -> None:
    if not frappe.db.exists("CRM Lead Source", SOURCE_VALUE):
        frappe.get_doc({"doctype": "CRM Lead Source", "source_name": SOURCE_VALUE}).insert(
            ignore_permissions=True
        )


def _add_comment(lead_name: str, content: str) -> None:
    frappe.get_doc(
        {
            "doctype": "Comment",
            "comment_type": "Info",
            "reference_doctype": LEAD_DOCTYPE,
            "reference_name": lead_name,
            "content": content,
        }
    ).insert(ignore_permissions=True)


def phone_digits(value) -> str:
    """Only the digits of a phone number, so spaces, dashes and brackets do not matter
    ("+91 90000 00002", "+91-9000000002" and "+919000000002" are the same number)."""
    return "".join(ch for ch in str(value or "") if ch.isdigit())


def flag_duplicates(lead, form_title: str) -> list[str]:
    """Same phone (digits only: spaces, dashes and brackets are ignored) as another lead.

    Changed 2026-11-14 (to-do from the staging test): it used to compare the exact typed text, so
    "+91 9000000002" and "+919000000002" were not seen as the same number. A number with no
    digits, or with fewer than 7, is never matched. The country code still counts ("91..." and
    "..." differ), because the form's phone box always adds one. Nothing is deleted.
    """
    digits = phone_digits(lead.get("mobile_no"))
    if len(digits) < 7:
        return []
    others = frappe.db.sql(
        f"select name from `tab{LEAD_DOCTYPE}` where name != %s and mobile_no is not null and mobile_no != '' "
        "and REGEXP_REPLACE(mobile_no, '[^0-9]', '') = %s order by creation limit 3",
        (lead.name, digits),
        pluck="name",
    )
    if not others:
        return []
    form_title = str(form_title or "web-form")
    _add_comment(
        lead.name, "Possible duplicate of " + ", ".join(others) + " (same phone, Web Form " + form_title + ")."
    )
    for other in others:
        _add_comment(
            other,
            "Re-enquiry: the same phone enquired again through Web Form "
            + form_title
            + " (lead "
            + lead.name
            + "). Call back.",
        )
    return others


def create_lead(form, answers: dict, uploads: dict[str, ParsedUpload]) -> tuple:
    """Create the lead, its files, duplicate flags and note. Returns (lead_doc, {fieldname: file_url})."""
    meta = frappe.get_meta(LEAD_DOCTYPE)
    _ensure_source()

    lead = frappe.new_doc(LEAD_DOCTYPE)
    for key, value in map_lead_fields(form, answers).items():
        lead.set(key, value)

    # Never from the payload: set here only.
    consent_values = {
        "consent_status": "Given",
        "consent_date": frappe.utils.now_datetime(),
        "consent_source": "Web Form: " + str(form.title),
        "web_consent": 1,
    }
    for key, value in consent_values.items():
        if meta.has_field(key):
            lead.set(key, value)
        elif key != "web_consent":
            frappe.log_error(
                title="forms_pro lead bridge: consent field missing on CRM Lead",
                message=f"CRM Lead has no field {key}; consent was NOT stored on the lead.",
            )
    if not lead.get("status"):
        lead.status = "New"
    lead.source = SOURCE_VALUE
    if meta.has_field("campaign") and not lead.get("campaign"):
        lead.campaign = str(form.title)
    lead.lead_owner = ""  # "" not None: Frappe fills None from a field default; "" stays empty

    lead.insert(ignore_permissions=True)

    file_urls: dict[str, str] = {}
    for fieldname, upload in uploads.items():
        file_doc = store_private_file(upload, LEAD_DOCTYPE, lead.name)
        file_urls[fieldname] = file_doc.file_url
        _add_comment(
            lead.name,
            "The visitor uploaded the file "
            + upload.file_name
            + " through Web Form "
            + str(form.title)
            + ". Private. It is archived to Google Drive and removed from the CRM after 6 months.",
        )

    flag_duplicates(lead, form.title)

    note = build_response_note(form, answers, uploads)
    if note:
        frappe.get_doc(
            {
                "doctype": "FCRM Note",
                "title": "Form answers: " + str(form.title or form.name)[:100],
                "content": note,
                "reference_doctype": LEAD_DOCTYPE,
                "reference_docname": lead.name,
            }
        ).insert(ignore_permissions=True)

    return lead, file_urls


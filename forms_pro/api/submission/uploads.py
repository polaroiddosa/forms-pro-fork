"""Private guest uploads (contract C3).

Wire format for an Attach answer in the submit payload (same as the academy forms):

    "<filename>,data:<mime>;base64,<data>"

Everything is re-checked here (extension, real size after decoding, magic bytes, at
most 3 files per form) before anything is written. Files are stored PRIVATE
(is_private=1) by system permissions; no site-wide guest-upload setting is needed
and a guest cannot fetch the file URL (Frappe answers 403 for /private/files/*).
Error texts are the academy texts.
"""

import base64
import binascii
import re
from dataclasses import dataclass

import frappe
from frappe import _

ALLOWED_EXTENSIONS = ("pdf", "jpg", "jpeg", "png", "webp", "doc", "docx")
MAX_FILE_BYTES = 5 * 1024 * 1024
MAX_FILES_PER_FORM = 3

MSG_TYPE = "This file type is not allowed. Please upload a PDF, JPG, PNG, WEBP, DOC or DOCX file."
MSG_SIZE = "The file is too large. The limit is 5 MB."
MSG_UNREADABLE = "The uploaded file could not be read. Please choose the file again."
MSG_TOO_MANY = "You can upload at most 3 files."


@dataclass
class ParsedUpload:
    fieldname: str
    file_name: str
    content: bytes


def _magic_ok(ext: str, data: bytes) -> bool:
    if ext in ("jpg", "jpeg"):
        return data.startswith(b"\xff\xd8\xff")
    if ext == "png":
        return data.startswith(b"\x89PNG\r\n\x1a\n")
    if ext == "pdf":
        return b"%PDF-" in data[:1024]
    if ext == "webp":
        return data[:4] == b"RIFF" and data[8:12] == b"WEBP"
    if ext == "doc":
        return data.startswith(b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1")
    if ext == "docx":
        return data.startswith(b"PK\x03\x04")
    return False


def _clean_file_name(raw: str) -> str:
    name = raw.replace("\\", "/").rsplit("/", 1)[-1]
    name = re.sub(r"[\x00-\x1f\x7f<>:\"|?*]", "", name).strip().strip(".")
    return name[:140]


def _refuse(message: str) -> None:
    frappe.throw(_(message), frappe.ValidationError)


def parse_attachment_value(fieldname: str, value) -> ParsedUpload:
    """Parse and fully check one Attach answer. Raises frappe.ValidationError (HTTP 417)."""
    if not isinstance(value, str) or ",data:" not in value[:600] or ";base64," not in value[:800]:
        _refuse(MSG_UNREADABLE)

    head, rest = value.split(",data:", 1)
    file_name = _clean_file_name(head)
    if not file_name or "." not in file_name:
        _refuse(MSG_TYPE)
    ext = file_name.lower().rsplit(".", 1)[-1]
    if ext not in ALLOWED_EXTENSIONS:
        _refuse(MSG_TYPE)

    b64 = rest.split(";base64,", 1)[1]
    # cheap guard before decoding anything large
    if len(b64) > (MAX_FILE_BYTES * 4) // 3 + 8:
        _refuse(MSG_SIZE)
    try:
        data = base64.b64decode(b64, validate=True)
    except (binascii.Error, ValueError):
        _refuse(MSG_UNREADABLE)
    if len(data) > MAX_FILE_BYTES:
        _refuse(MSG_SIZE)
    if not data or not _magic_ok(ext, data):
        _refuse(MSG_UNREADABLE)
    return ParsedUpload(fieldname=fieldname, file_name=file_name, content=data)


def parse_attachments(form, form_data: dict) -> dict[str, ParsedUpload]:
    """Parse every non-empty Attach answer of the form. Returns {fieldname: ParsedUpload}."""
    parsed: dict[str, ParsedUpload] = {}
    for field in form.fields:
        if field.fieldtype != "Attach":
            continue
        value = form_data.get(field.fieldname)
        if value is None or value == "":
            continue
        parsed[field.fieldname] = parse_attachment_value(field.fieldname, value)
    if len(parsed) > MAX_FILES_PER_FORM:
        _refuse(MSG_TOO_MANY)
    return parsed


def store_private_file(upload: ParsedUpload, attached_to_doctype: str, attached_to_name: str):
    """Create a private File attached to the given document, with system permissions."""
    file_doc = frappe.get_doc(
        {
            "doctype": "File",
            "file_name": upload.file_name,
            "attached_to_doctype": attached_to_doctype,
            "attached_to_name": attached_to_name,
            "content": upload.content,
            "is_private": 1,
        }
    )
    file_doc.insert(ignore_permissions=True)
    return file_doc

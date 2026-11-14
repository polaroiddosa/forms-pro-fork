import json
from typing import Any

import frappe
from frappe import _
from frappe.rate_limiter import rate_limit
from frappe.share import add_docshare

from forms_pro.forms_pro.doctype.form.form import Form
from forms_pro.forms_pro.doctype.form_field.form_field import _DISPLAY_ONLY_FIELDTYPES
from forms_pro.utils.form_generator import SubmissionStatus
from forms_pro.utils.permissions import require_permission

from . import lead_bridge
from .consent import CONSENT_REFUSAL_MESSAGE, is_consent_given
from .display import display_value
from .schema import UserSubmissionResponse
from .uploads import parse_attachments, store_private_file

_SELECT_LIKE_FIELDTYPES = ("Select", "Single Choice")


def _coerce_field_value(value: Any, fieldtype: str) -> Any:
    """Coerce a submitted value to its comparable type, matching frontend conditionals.ts logic."""
    if value is None or value == "":
        return None
    # Matches isBoolean types in the frontend registry (Switch, Checkbox)
    if fieldtype in ("Switch", "Checkbox"):
        return bool(value)
    if fieldtype == "Number":
        try:
            return float(value)
        except (TypeError, ValueError):
            return None
    return str(value)


def _chosen_options(value: Any) -> list[str]:
    if value is None or value == "":
        return []
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except (json.JSONDecodeError, TypeError):
            value = [value]
    if not isinstance(value, (list, tuple)):
        value = [value]
    return [str(v) for v in value if v not in (None, "")]


def _multiselect_condition_met(operator: str, value: Any, expected: Any) -> bool:
    chosen = _chosen_options(value)
    if operator == "Is":
        return str(expected) in chosen
    if operator == "Is Not":
        return str(expected) not in chosen
    if operator == "Is Empty":
        return not chosen
    if operator == "Is Not Empty":
        return bool(chosen)
    return True


def _evaluate_conditions(conditions: list[dict], form_data: dict, field_map: dict) -> bool:
    """Evaluate AND-joined conditions against submitted form data."""
    for condition in conditions:
        fieldname = condition.get("fieldname")
        operator = condition.get("operator")
        expected = condition.get("value")
        field = field_map.get(fieldname)
        if not field:
            return False
        if field.fieldtype == "Multiselect":
            # Multi-select: EXACT membership of the chosen options, never substring ("Art" is not in "Artisan").
            if not _multiselect_condition_met(operator, form_data.get(fieldname), expected):
                return False
            continue
        actual = _coerce_field_value(form_data.get(fieldname), field.fieldtype)
        # Coerce the condition's expected value through the same function so
        # types match — avoids str(True)=="True" vs "true" mismatches and
        # str(3.0)=="3.0" vs "3" mismatches for Number fields.
        expected_coerced = _coerce_field_value(expected, field.fieldtype)
        if operator == "Is" and actual != expected_coerced:
            return False
        if operator == "Is Not" and actual == expected_coerced:
            return False
        if operator == "Is Empty" and actual is not None and actual != "":
            return False
        if operator == "Is Not Empty" and (actual is None or actual == ""):
            return False
    return True


def _is_show_field_target(form: "Form", fieldname: str) -> bool:
    """True if any field carries a Show Field rule whose target_field is `fieldname`."""
    for other in form.fields:
        if not other.conditional_logic:
            continue
        try:
            logic = json.loads(other.conditional_logic)
        except (json.JSONDecodeError, TypeError):
            continue
        if logic.get("target_field") == fieldname and logic.get("action") == "Show Field":
            return True
    return False


def _validate_form_response(form: "Form", form_data: dict) -> None:
    """
    Validate required and conditionally-required fields server-side.

    Mirrors the shouldFieldBeVisible / shouldFieldBeRequired logic in
    frontend/src/utils/conditionals.ts so that direct API calls cannot
    bypass frontend validation.
    """
    field_map = {f.fieldname: f for f in form.fields}
    errors: list[str] = []

    for field in form.fields:
        if field.fieldtype in _DISPLAY_ONLY_FIELDTYPES:
            continue
        # A Show Field target is hidden until its rule is met, even if its own
        # Hidden box is not ticked (same rule as shouldFieldBeVisible in the frontend).
        is_show_target = _is_show_field_target(form, field.fieldname)
        is_visible = not field.hidden and not is_show_target
        is_required = bool(field.reqd)

        for other in form.fields:
            if not other.conditional_logic:
                continue
            try:
                logic = json.loads(other.conditional_logic)
            except (json.JSONDecodeError, TypeError):
                continue

            if logic.get("target_field") != field.fieldname:
                continue

            conditions_met = _evaluate_conditions(logic.get("conditions", []), form_data, field_map)
            if conditions_met:
                action = logic.get("action")
                if action == "Show Field":
                    is_visible = True
                elif action == "Hide Field":
                    is_visible = False
                elif action == "Require Answer":
                    is_required = True

        if not is_visible:
            continue

        value = form_data.get(field.fieldname)
        is_empty = value is None or value == "" or value == []
        if is_required and is_empty:
            errors.append(_("{0} is required").format(field.label))
        elif field.fieldtype in _SELECT_LIKE_FIELDTYPES and not is_empty:
            options = [o.strip() for o in (getattr(field, "options", None) or "").split("\n") if o.strip()]
            if options and str(value) not in options:
                errors.append(_("{0}: please choose one of the listed answers").format(field.label))

    if errors:
        frappe.throw("\n".join(errors), frappe.ValidationError)


# Rate limit: 10 submissions per minute per visitor IP per form, using Frappe's own limiter (frappe.rate_limiter.rate_limit)
# (`rl:<cmd>:<ip>:<form_id>` in redis). The IP is `frappe.local.request_ip`, which behind a
# proxy comes from the forwarded header: the proxy must pass the real visitor address
# (the academy Caddy sets X-Forwarded-For from CF-Connecting-IP). If it does not, every
# visitor shares one key. Over the limit Frappe answers HTTP 429.
@frappe.whitelist(allow_guest=True)  # nosemgrep: frappe-semgrep-rules.rules.security.guest-whitelisted-method
@rate_limit(key="form_id", limit=10, seconds=60)
def submit_form_response(
    form_id: str,
    form_data: list[dict],
    submission_status: str = SubmissionStatus.SUBMITTED.value,
    consent: int | str = 0,
) -> str:
    """
    Submit a form response

    Args:
        form_id: The ID of the form
        form_data: The data of the form
        submission_status: The status of the submission: Default is `Submitted`
        consent: 1 when the visitor ticked the fixed consent box (required for Submitted)

    Returns:
        The name of the submission
    """
    try:
        status = SubmissionStatus(submission_status)
    except ValueError:
        frappe.throw(
            _("Invalid submission status: {0}").format(submission_status),
            frappe.ValidationError,
        )

    if status == SubmissionStatus.DRAFT and frappe.session.user == "Guest":
        frappe.throw(_("Drafts are not accepted from visitors."), frappe.ValidationError)

    form: Form = frappe.get_doc("Form", form_id)
    linked_doctype = form.linked_doctype

    if not form.is_published:
        frappe.throw(
            _("This form is un-published, so responses are no longer being collected."),
            frappe.PermissionError,
        )

    if status == SubmissionStatus.SUBMITTED and not is_consent_given(consent):
        frappe.throw(_(CONSENT_REFUSAL_MESSAGE), frappe.ValidationError)

    form_data_dict = {item["fieldname"]: item["value"] for item in form_data}

    # Whitelist to declared form fields only — prevents injecting system fields
    # like owner, docstatus, etc. into the linked DocType (and status, lead_owner,
    # consent, source into the lead: the lead bridge never reads those from here).
    allowed_fieldnames = {f.fieldname for f in form.fields}
    form_data_dict = {k: v for k, v in form_data_dict.items() if k in allowed_fieldnames}

    if status == SubmissionStatus.SUBMITTED:
        _validate_form_response(form, form_data_dict)

    # Check every file BEFORE anything is written (type, size, magic bytes, max 3).
    uploads = parse_attachments(form, form_data_dict)
    for fieldname in uploads:
        form_data_dict[fieldname] = ""  # replaced by the private file URL below

    # Multiselect answers live in a JSON column: a blank answer (the public page sends "" when
    # nothing is ticked) must be stored as NULL, because the column refuses an empty string
    # (MariaDB error 4025 -> HTTP 500). Found 2026-11-14 in the integrated browser test.
    multiselect_fields = {f.fieldname for f in form.fields if f.fieldtype == "Multiselect"}

    submission = frappe.new_doc(linked_doctype)
    for fieldname, value in form_data_dict.items():
        # JSON fields (e.g. Multiselect) must be stored as a JSON string,
        # but Frappe deserializes request body arrays into Python lists before
        # we get here — serialize them back.
        if fieldname in multiselect_fields and (
            value is None or (isinstance(value, str) and not value.strip()) or value == []
        ):
            value = None
        elif isinstance(value, list):
            value = json.dumps(value)
        submission.set(fieldname, value)

    submission.fp_linked_form = form_id
    submission.fp_submission_status = status.value
    submission.insert(ignore_permissions=True, ignore_mandatory=True)

    # Share the submission with the owner
    add_docshare(
        doctype=linked_doctype,
        name=submission.name,
        user=frappe.session.user,
        read=1,
        write=1,
        flags={
            "ignore_share_permission": True,
        },
    )

    file_urls: dict[str, str] = {}
    if status == SubmissionStatus.SUBMITTED and lead_bridge.bridge_available():
        # Forms Pro's own submission row stays; the lead is added next to it.
        # (`fp_lead` on the submission is deliberately not added: no migration-safe way in this track.)
        _lead, file_urls = lead_bridge.create_lead(form, form_data_dict, uploads)
    else:
        for fieldname, upload in uploads.items():
            file_urls[fieldname] = store_private_file(upload, linked_doctype, submission.name).file_url

    for fieldname, url in file_urls.items():
        frappe.db.set_value(linked_doctype, submission.name, fieldname, url, update_modified=False)

    return submission.name


@frappe.whitelist()
@require_permission("Form", "read", param="form_id")
def get_user_submissions(form_id: str) -> list[UserSubmissionResponse]:
    """
    Get the submissions for a user

    Args:
        form_id: The ID of the form

    Returns:
        A list of submissions for the user
    """
    form: Form = frappe.get_doc("Form", form_id)
    linked_doctype = form.linked_doctype

    submissions = frappe.get_all(
        doctype=linked_doctype,
        filters={"owner": frappe.session.user},
        fields=["name", "creation", "modified", "fp_submission_status", "owner"],
        order_by="creation",
    )

    return [UserSubmissionResponse.model_validate(submission).model_dump() for submission in submissions]


@frappe.whitelist()
def get_submission_response(submission_id: str, doctype: str) -> dict[str, Any]:
    """
    Get a full submission response by ID.
    This API checks if the user is the team member / the form is shared with the user.

    Args:
        submission_id: The name/ID of the submission document
        doctype: The submission's doctype (linked_doctype of the form)

    Returns:
        The submission document as a dict
    """
    linked_form = frappe.db.get_value(doctype, submission_id, "fp_linked_form")
    if not linked_form:
        frappe.throw(_("Submission not found."), frappe.DoesNotExistError)

    form_data = frappe.db.get_value("Form", linked_form, ["linked_team_id", "linked_doctype"], as_dict=True)

    if form_data.linked_doctype != doctype:
        frappe.throw(_("Invalid doctype for this submission."), frappe.PermissionError)

    if not frappe.has_permission(
        doctype="FP Team", ptype="write", doc=form_data.linked_team_id, user=frappe.session.user
    ):
        frappe.throw(
            _("You do not have permission to read this form's submissions."),
            frappe.PermissionError,
        )

    submission = frappe.get_doc(form_data.linked_doctype, submission_id)
    return submission.as_dict()


@frappe.whitelist()
def get_submission(submission_doctype: str, submission_name: str) -> dict[str, Any]:
    """
    Get a submission by name. Used usually by the form owner to view the submission details.

    Args:
        submission_name: The name of the submission

    Returns:
        The submission
    """
    submission = frappe.get_doc(submission_doctype, submission_name)

    if not frappe.has_permission(doctype=submission.doctype, ptype="read", doc=submission.name):
        frappe.throw(
            _("You do not have permission to read this submission."),
            frappe.PermissionError,
        )

    return submission.as_dict()


@frappe.whitelist()
@require_permission("Form", "read", param="form_id")
def get_all_submissions(form_id: str) -> list[UserSubmissionResponse]:
    """
    Get all submissions for a form

    Args:
        form_id: The ID of the form

    Returns:
        A list of submissions for the form
    """
    form: Form = frappe.get_doc("Form", form_id)
    linked_doctype = form.linked_doctype

    submissions = frappe.get_all(
        doctype=linked_doctype,
        fields=["name", "creation", "modified", "fp_submission_status", "owner"],
        filters={"fp_submission_status": "Submitted"},
        order_by="creation",
    )

    return [UserSubmissionResponse.model_validate(submission).model_dump() for submission in submissions]


@frappe.whitelist()
@require_permission("Form", "read", param="form_id")
def get_submission_table(form_id: str) -> dict[str, Any]:
    """
    Answers table for a form: one column per question, one display value per answer.

    Returns:
        {"columns": [{"fieldname", "label", "fieldtype"}],
         "rows": [{"name", "creation", "owner", "fp_submission_status", "answers": {fieldname: display}}]}

    Same columns as `export_submissions` (every field that stores a value, in form order).
    Only Submitted rows, like `get_all_submissions`.
    """
    form: Form = frappe.get_doc("Form", form_id)
    linked_doctype = form.linked_doctype
    columns = [
        {"fieldname": f.fieldname, "label": f.label, "fieldtype": f.fieldtype}
        for f in form.fields
        if f.stores_value
    ]
    fieldtypes = {c["fieldname"]: c["fieldtype"] for c in columns}
    db_columns = {df.fieldname for df in frappe.get_meta(linked_doctype).fields}
    answer_fields = [name for name in fieldtypes if name in db_columns]

    records = frappe.get_all(
        doctype=linked_doctype,
        fields=["name", "creation", "owner", "fp_submission_status", *answer_fields],
        filters={"fp_linked_form": form_id, "fp_submission_status": "Submitted"},
        order_by="creation",
    )
    rows = [
        {
            "name": rec["name"],
            "creation": rec["creation"],
            "owner": rec["owner"],
            "fp_submission_status": rec["fp_submission_status"],
            "answers": {
                name: display_value(fieldtypes[name], rec.get(name)) if name in answer_fields else ""
                for name in fieldtypes
            },
        }
        for rec in records
    ]
    return {"columns": columns, "rows": rows}

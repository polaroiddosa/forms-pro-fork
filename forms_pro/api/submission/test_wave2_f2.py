"""Wave 2 track F2 tests: consent, lead bridge, uploads, rate limit, answers table, visibility.

Plain frappe APIs only (the frappe_factory_bot app is not installed on the local test
stack). Everything created here is named F2TEST... and removed in tearDown.
"""

import base64
import json
import random
import struct
import zlib
from types import SimpleNamespace

import frappe
import requests
from frappe.tests import IntegrationTestCase

from forms_pro.api.export import export_submissions
from forms_pro.api.form import get_form
from forms_pro.api.settings.endpoints import get_website_settings
from forms_pro.api.submission import get_submission_table, submit_form_response
from forms_pro.api.submission.consent import CONSENT_LABEL, CONSENT_TEXT
from forms_pro.api.submission.endpoints import _validate_form_response

PREFIX = "F2TEST"
CONSENT_REFUSAL = "Please tick the consent box so that we may contact you."


def _png_bytes() -> bytes:
    def chunk(kind: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)

    raw = b"\x00\xff\x00\x00"  # one red pixel
    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(raw))
        + chunk(b"IEND", b"")
    )


def _data_url(name: str, content: bytes, mime: str = "image/png") -> str:
    return f"{name},data:{mime};base64,{base64.b64encode(content).decode()}"


def _payload(**values) -> list[dict]:
    return [{"fieldname": k, "value": v} for k, v in values.items()]


def _phone() -> str:
    return "+919" + "".join(random.choice("0123456789") for _ in range(9))


BASIC_FIELDS = [
    {"label": "Your name", "fieldname": "your_name", "fieldtype": "Data", "reqd": 1},
    {"label": "Mobile", "fieldname": "mobile", "fieldtype": "Phone", "reqd": 1},
    {"label": "Email", "fieldname": "email_addr", "fieldtype": "Email"},
]


class F2TestBase(IntegrationTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls._created_custom_fields = []
        frappe.set_user("Administrator")
        wanted = {
            "consent_status": "Data",
            "consent_date": "Datetime",
            "consent_source": "Data",
            "campaign": "Data",
            "web_consent": "Check",
        }
        for fieldname, fieldtype in wanted.items():
            if not frappe.db.exists("Custom Field", {"dt": "CRM Lead", "fieldname": fieldname}) and not any(
                df.fieldname == fieldname for df in frappe.get_meta("CRM Lead").fields
            ):
                cf = frappe.get_doc(
                    {
                        "doctype": "Custom Field",
                        "dt": "CRM Lead",
                        "fieldname": fieldname,
                        "label": fieldname.replace("_", " ").title(),
                        "fieldtype": fieldtype,
                    }
                ).insert(ignore_permissions=True)
                cls._created_custom_fields.append(cf.name)
        # make lead_owner default to a user, so the "owner cleared" test can detect a missing clear
        cls._ps = frappe.get_doc(
            {
                "doctype": "Property Setter",
                "doctype_or_field": "DocField",
                "doc_type": "CRM Lead",
                "field_name": "lead_owner",
                "property": "default",
                "property_type": "Text",
                "value": "Administrator",
            }
        ).insert(ignore_permissions=True)
        frappe.clear_cache(doctype="CRM Lead")

    @classmethod
    def tearDownClass(cls):
        frappe.set_user("Administrator")
        frappe.delete_doc("Property Setter", cls._ps.name, force=True, ignore_permissions=True)
        for name in cls._created_custom_fields:
            frappe.delete_doc("Custom Field", name, force=True, ignore_permissions=True)
        frappe.db.commit()
        frappe.clear_cache(doctype="CRM Lead")
        super().tearDownClass()

    def setUp(self):
        frappe.set_user("Administrator")
        self._forms = []
        self._doctypes = []
        self._teams = []
        self._extra_files = []
        self._extra_users = []

    def tearDown(self):
        frappe.set_user("Administrator")
        frappe.local.request = None
        frappe.local.conf.pop("forms_pro_source_url", None)
        frappe.db.rollback()
        leads = frappe.get_all(
            "CRM Lead",
            or_filters={"consent_source": ["like", f"Web Form: {PREFIX}%"], "first_name": ["like", f"{PREFIX}%"]},
            pluck="name",
        )
        for lead in leads:
            for dt, field in (("FCRM Note", "reference_docname"), ("Comment", "reference_name"), ("File", "attached_to_name")):
                for n in frappe.get_all(dt, filters={field: lead}, pluck="name"):
                    frappe.delete_doc(dt, n, force=True, ignore_permissions=True)
            frappe.delete_doc("CRM Lead", lead, force=True, ignore_permissions=True)
        for name in self._extra_files:
            if frappe.db.exists("File", name):
                frappe.delete_doc("File", name, force=True, ignore_permissions=True)
        for name in self._extra_users:
            if frappe.db.exists("User", name):
                frappe.delete_doc("User", name, force=True, ignore_permissions=True)
        for name in self._forms:
            if frappe.db.exists("Form", name):
                frappe.delete_doc("Form", name, force=True, ignore_permissions=True)
        for name in self._doctypes:
            if frappe.db.exists("DocType", name):
                frappe.delete_doc("DocType", name, force=True, ignore_permissions=True)
        for name in self._teams:
            if frappe.db.exists("FP Team", name):
                frappe.delete_doc("FP Team", name, force=True, ignore_permissions=True)
        frappe.db.commit()

    # helpers -----------------------------------------------------------------
    def make_form(self, fields=None, published=True, title=None, **extra):
        from forms_pro.utils.form_generator import LINKED_FORM_FIELDOPTIONS, SUBMISSION_STATUS_FIELDOPTIONS

        team = frappe.get_doc({"doctype": "FP Team", "team_name": f"{PREFIX} team {frappe.generate_hash(length=5)}"}).insert(
            ignore_permissions=True
        )
        self._teams.append(team.name)
        dt = frappe.get_doc(
            {
                "doctype": "DocType",
                "name": f"formspro_f2t_{frappe.generate_hash(length=6).lower()}",
                "module": "User Forms" if frappe.db.exists("Module Def", "User Forms") else "Forms Pro",
                "custom": 1,
                "fields": [{"fieldtype": "Section Break"}, SUBMISSION_STATUS_FIELDOPTIONS, LINKED_FORM_FIELDOPTIONS],
                "permissions": [{"role": "System Manager", "read": 1, "write": 1, "create": 1}],
            }
        ).insert(ignore_permissions=True)
        self._doctypes.append(dt.name)
        form = frappe.get_doc(
            {
                "doctype": "Form",
                "title": title or f"{PREFIX} form {frappe.generate_hash(length=5)}",
                "linked_doctype": dt.name,
                "linked_team_id": team.name,
                "fields": [dict(f) for f in (fields or BASIC_FIELDS)],
                **extra,
            }
        ).insert(ignore_permissions=True)
        self._forms.append(form.name)
        if published:
            form.is_published = 1
            form.save(ignore_permissions=True)
        return form

    def submit(self, form, consent=1, as_guest=True, **values):
        if as_guest:
            frappe.set_user("Guest")
        try:
            return submit_form_response(form_id=form.name, form_data=_payload(**values), consent=consent)
        finally:
            frappe.set_user("Administrator")

    def lead_names(self):
        return frappe.get_all("CRM Lead", filters={"consent_source": ["like", f"Web Form: {PREFIX}%"]}, pluck="name")

    def rows(self, form):
        return frappe.get_all(form.linked_doctype, pluck="name")

    def good(self, **over):
        values = {"your_name": f"{PREFIX} Asha", "mobile": _phone(), "email_addr": "asha@example.com"}
        values.update(over)
        return values


class TestConsent(F2TestBase):
    def test_constants_are_the_academy_wording(self):
        self.assertLess(len(CONSENT_LABEL), 140)
        self.assertEqual(len(CONSENT_TEXT), 172)
        self.assertTrue(CONSENT_LABEL.startswith("I agree to be contacted by Transparent Academy"))
        self.assertIn("by phone, WhatsApp and email about courses and admissions", CONSENT_TEXT)

    def test_no_consent_is_refused_and_creates_nothing(self):
        form = self.make_form()
        for consent in (0, "0", ""):
            with self.assertRaises(frappe.ValidationError) as ctx:
                self.submit(form, consent=consent, **self.good())
            self.assertIn(CONSENT_REFUSAL, str(ctx.exception))
            self.assertEqual(ctx.exception.http_status_code, 417)
        self.assertEqual(self.lead_names(), [])
        self.assertEqual(self.rows(form), [])

    def test_guest_draft_is_refused(self):
        form = self.make_form(allow_incomplete=1)
        frappe.set_user("Guest")
        try:
            with self.assertRaises(frappe.ValidationError):
                submit_form_response(
                    form_id=form.name, form_data=_payload(**self.good()), submission_status="Draft", consent=1
                )
        finally:
            frappe.set_user("Administrator")
        self.assertEqual(self.lead_names(), [])
        self.assertEqual(self.rows(form), [])

    def test_form_api_returns_consent_keys(self):
        form = self.make_form()
        frappe.set_user("Guest")
        try:
            data = get_form(form.name)
        finally:
            frappe.set_user("Administrator")
        self.assertEqual(data["consent_label"], CONSENT_LABEL)
        self.assertEqual(data["consent_text"], CONSENT_TEXT)


class TestLeadBridge(F2TestBase):
    def test_consent_creates_lead_with_given_consent(self):
        form = self.make_form()
        values = self.good()
        sub = self.submit(form, **values)
        self.assertTrue(frappe.db.exists(form.linked_doctype, sub))  # Forms Pro's own row is kept
        leads = self.lead_names()
        self.assertEqual(len(leads), 1)
        lead = frappe.get_doc("CRM Lead", leads[0])
        self.assertEqual(lead.consent_status, "Given")
        self.assertTrue(lead.consent_date)
        self.assertEqual(lead.consent_source, "Web Form: " + form.title)
        self.assertEqual(lead.source, "Website form")
        self.assertEqual(lead.status, "New")
        self.assertEqual(lead.campaign, form.title)
        self.assertFalse(lead.lead_owner)
        self.assertEqual(lead.mobile_no, values["mobile"])
        self.assertEqual(lead.email, "asha@example.com")
        self.assertEqual(lead.first_name, f"{PREFIX} Asha")
        self.assertTrue(lead.web_consent)

    def test_first_name_falls_back_to_form_title(self):
        form = self.make_form(
            fields=[
                {"label": "Phone", "fieldname": "phone_q", "fieldtype": "Phone"},
                {"label": "Comment", "fieldname": "comment_q", "fieldtype": "Data"},
            ],
            title=f"{PREFIX} Open day",
        )
        self.submit(form, phone_q=_phone(), comment_q="hello")
        lead = frappe.get_doc("CRM Lead", self.lead_names()[0])
        self.assertEqual(lead.first_name, f"{PREFIX} Open day")

    def test_tampered_status_owner_consent_source_ignored(self):
        form = self.make_form(
            fields=BASIC_FIELDS
            + [
                {"label": "Status", "fieldname": "status", "fieldtype": "Data"},
                {"label": "Lead owner", "fieldname": "lead_owner", "fieldtype": "Data"},
                {"label": "Source", "fieldname": "source", "fieldtype": "Data"},
            ]
        )
        frappe.set_user("Guest")
        try:
            submit_form_response(
                form_id=form.name,
                form_data=_payload(
                    **self.good(),
                    status="Lost",
                    lead_owner="Administrator",
                    source="Facebook",
                    consent_status="Withdrawn",
                    consent_source="evil",
                    owner="Administrator",
                ),
                consent=1,
            )
        finally:
            frappe.set_user("Administrator")
        lead = frappe.get_doc("CRM Lead", self.lead_names()[0])
        self.assertEqual(lead.status, "New")
        self.assertFalse(lead.lead_owner)
        self.assertEqual(lead.source, "Website form")
        self.assertEqual(lead.consent_status, "Given")
        self.assertEqual(lead.consent_source, "Web Form: " + form.title)

    def test_same_phone_flags_both_leads(self):
        form = self.make_form()
        phone = _phone()
        self.submit(form, **self.good(mobile=phone))
        first = self.lead_names()[0]
        self.submit(form, **self.good(mobile=phone, your_name=f"{PREFIX} Again"))
        leads = self.lead_names()
        self.assertEqual(len(leads), 2)  # nothing deleted, both created
        second = [n for n in leads if n != first][0]
        c_second = frappe.get_all("Comment", filters={"reference_name": second, "comment_type": "Info"}, pluck="content")
        c_first = frappe.get_all("Comment", filters={"reference_name": first, "comment_type": "Info"}, pluck="content")
        self.assertTrue(any(c.startswith("Possible duplicate of " + first) for c in c_second), c_second)
        self.assertTrue(any(c.startswith("Re-enquiry: the same phone") and second in c for c in c_first), c_first)

    def test_different_phone_is_not_flagged(self):
        form = self.make_form()
        self.submit(form, **self.good(mobile="+919000000001"))
        self.submit(form, **self.good(mobile="+919000000002"))
        self.assertEqual(frappe.get_all("Comment", filters={"comment_type": "Info", "content": ["like", "%duplicate%"]}), [])

    def test_blank_multiselect_answer_is_stored_and_does_not_fail(self):
        """Regression (2026-11-14, found in the integrated browser test): the public page sends ""
        for a multiple-choice question nobody ticked; the JSON column refused it (MariaDB 4025) and
        the whole submit gave HTTP 500. A blank answer must be stored as NULL and the lead created."""
        form = self.make_form(
            fields=BASIC_FIELDS
            + [{"label": "Courses", "fieldname": "courses", "fieldtype": "Multiselect", "options": "A\nB\nC"}]
        )
        for blank in ("", None, [], "   "):
            with self.subTest(blank=blank):
                self.submit(form, **self.good(mobile="+919000000%03d" % (hash(str(blank)) % 1000)), courses=blank)
        rows = frappe.get_all(form.linked_doctype, fields=["courses"])
        self.assertEqual(len(rows), 4)
        self.assertTrue(all(r.courses in (None, "") for r in rows))

    def test_response_note_lists_every_answer_escaped(self):
        form = self.make_form(
            fields=BASIC_FIELDS
            + [
                {"label": "Terms & Conditions", "fieldname": "why", "fieldtype": "Textarea"},
                {"label": "Hostel", "fieldname": "hostel", "fieldtype": "Checkbox"},
                {"label": "Courses", "fieldname": "courses", "fieldtype": "Multiselect", "options": "A\nB\nC"},
                {"label": "CV", "fieldname": "cv", "fieldtype": "Attach"},
                {"label": "Skipped", "fieldname": "skipped", "fieldtype": "Data"},
            ]
        )
        self.submit(
            form,
            **self.good(),
            why="I want <b>coaching</b> & hostel",
            hostel=1,
            courses=["A", "C"],
            cv=_data_url("cv.png", _png_bytes()),
        )
        lead = self.lead_names()[0]
        notes = frappe.get_all("FCRM Note", filters={"reference_docname": lead}, fields=["title", "content"])
        self.assertEqual(len(notes), 1)
        self.assertEqual(notes[0].title, "Form answers: " + form.title)
        c = notes[0].content
        self.assertIn("I want &lt;b&gt;coaching&lt;/b&gt; &amp; hostel", c)
        self.assertNotIn("<b>coaching</b>", c)
        self.assertIn("<b>Terms &amp; Conditions</b>", c)
        self.assertIn("<b>Hostel</b><br>Yes", c)
        self.assertIn("A, C", c)
        self.assertIn("<b>CV</b><br>cv.png", c)
        self.assertNotIn("Skipped", c)
        self.assertNotIn("/private/files", c)


class TestUploads(F2TestBase):
    FIELDS = BASIC_FIELDS + [{"label": "Document", "fieldname": "doc1", "fieldtype": "Attach"}]

    def _expect_refused(self, value, fields=None, extra=None):
        form = self.make_form(fields=fields or self.FIELDS)
        payload = dict(self.good(), doc1=value, **(extra or {}))
        with self.assertRaises(frappe.ValidationError):
            self.submit(form, **payload)
        self.assertEqual(self.lead_names(), [])
        self.assertEqual(self.rows(form), [])
        self.assertEqual(frappe.get_all("File", filters={"file_name": ["like", "f2%"]}), [])

    def test_6mb_file_refused(self):
        self._expect_refused(_data_url("f2big.png", _png_bytes() + b"\0" * (6 * 1024 * 1024)))

    def test_exe_refused(self):
        self._expect_refused(_data_url("f2virus.exe", b"MZ\x90\x00", "application/octet-stream"))

    def test_html_refused(self):
        self._expect_refused(_data_url("f2page.html", b"<html><script>alert(1)</script>", "text/html"))

    def test_wrong_magic_bytes_refused(self):
        self._expect_refused(_data_url("f2fake.png", b"this is not a png at all"))

    def test_plain_url_instead_of_data_refused(self):
        self._expect_refused("/files/f2other.png")

    def test_more_than_three_files_refused(self):
        fields = BASIC_FIELDS + [
            {"label": f"File {i}", "fieldname": f"doc{i}", "fieldtype": "Attach"} for i in range(1, 5)
        ]
        form = self.make_form(fields=fields)
        files = {f"doc{i}": _data_url(f"f2f{i}.png", _png_bytes()) for i in range(1, 5)}
        with self.assertRaises(frappe.ValidationError):
            self.submit(form, **self.good(), **files)
        self.assertEqual(self.lead_names(), [])
        self.assertEqual(self.rows(form), [])

    def test_good_png_is_private_attached_to_lead_and_guest_gets_403(self):
        form = self.make_form(fields=self.FIELDS)
        sub = self.submit(form, **self.good(), doc1=_data_url("f2photo.png", _png_bytes()))
        lead = self.lead_names()[0]
        files = frappe.get_all(
            "File",
            filters={"attached_to_doctype": "CRM Lead", "attached_to_name": lead},
            fields=["name", "file_name", "file_url", "is_private"],
        )
        self.assertEqual(len(files), 1)
        self.assertEqual(files[0].is_private, 1)
        self.assertTrue(files[0].file_url.startswith("/private/files/"))
        self.assertEqual(frappe.db.get_value(form.linked_doctype, sub, "doc1"), files[0].file_url)
        self.assertTrue(
            frappe.db.exists(
                "Comment", {"reference_name": lead, "content": ["like", "The visitor uploaded the file f2photo.png%"]}
            )
        )
        # control: the SAME url with a logged-in user's API token is served (200), so the guest 403 means something
        user = frappe.get_doc(
            {
                "doctype": "User",
                "email": "f2test_reader@example.com",
                "first_name": PREFIX,
                "send_welcome_email": 0,
                "roles": [{"role": "System Manager"}],
            }
        ).insert(ignore_permissions=True)
        self._extra_users.append(user.name)
        from frappe.utils.password import update_password

        password = frappe.generate_hash(length=20)
        update_password(user.name, password)
        frappe.db.commit()  # the web server process must see the rows
        base = "http://127.0.0.1:8000"
        headers = {"Host": frappe.local.site}
        session = requests.Session()
        login = session.post(
            base + "/api/method/login", data={"usr": user.name, "pwd": password}, headers=headers, timeout=20
        )
        self.assertEqual(login.status_code, 200)
        control = session.get(base + files[0].file_url, headers=headers, timeout=20)
        self.assertEqual(control.status_code, 200)
        self.assertEqual(control.content[:8], b"\x89PNG\r\n\x1a\n")
        guest = requests.get(base + files[0].file_url, headers=headers, timeout=20)
        self.assertEqual(guest.status_code, 403)

    def test_unpublished_form_refuses_everything(self):
        form = self.make_form(fields=self.FIELDS, published=False)
        for consent in (1, 0):
            with self.assertRaises(frappe.PermissionError):
                self.submit(form, consent=consent, **self.good(), doc1=_data_url("f2photo.png", _png_bytes()))
        self.assertEqual(self.lead_names(), [])
        self.assertEqual(self.rows(form), [])
        self.assertEqual(frappe.get_all("File", filters={"file_name": ["like", "f2%"]}), [])


class TestRateLimit(F2TestBase):
    def test_11th_submission_in_a_minute_is_limited(self):
        form = self.make_form()
        frappe.local.request = SimpleNamespace(method="POST")
        frappe.local.request_ip = f"10.{random.randint(1, 250)}.{random.randint(1, 250)}.{random.randint(1, 250)}"
        frappe.form_dict.cmd = "forms_pro.api.submission.submit_form_response"
        frappe.form_dict.form_id = form.name
        for i in range(10):
            self.submit(form, **self.good(mobile=f"+9190000{i:05d}"))
        with self.assertRaises(frappe.RateLimitExceededError) as ctx:
            self.submit(form, **self.good(mobile="+919000099999"))
        self.assertEqual(ctx.exception.http_status_code, 429)
        self.assertEqual(len(self.lead_names()), 10)


class TestAnswersTable(F2TestBase):
    FIELDS = [
        {"label": "Heading", "fieldname": "h1", "fieldtype": "Heading 1"},
        {"label": "Your name", "fieldname": "your_name", "fieldtype": "Data"},
        {"label": "Mobile", "fieldname": "mobile", "fieldtype": "Phone"},
        {"label": "Hostel", "fieldname": "hostel", "fieldtype": "Checkbox"},
        {"label": "Courses", "fieldname": "courses", "fieldtype": "Multiselect", "options": "A\nB\nC"},
        {"label": "CV", "fieldname": "cv", "fieldtype": "Attach"},
        {"label": "Notes", "fieldname": "notes", "fieldtype": "Data"},
    ]

    def test_one_column_per_question_with_display_values(self):
        form = self.make_form(fields=self.FIELDS)
        sub = self.submit(
            form,
            your_name=f"{PREFIX} Asha",
            mobile=_phone(),
            hostel=1,
            courses=["A", "C"],
            cv=_data_url("cv.png", _png_bytes()),
        )
        result = get_submission_table(form_id=form.name)
        self.assertEqual(
            [c["fieldname"] for c in result["columns"]], ["your_name", "mobile", "hostel", "courses", "cv", "notes"]
        )
        self.assertEqual(set(result["columns"][0]), {"fieldname", "label", "fieldtype"})
        self.assertEqual(len(result["rows"]), 1)
        row = result["rows"][0]
        self.assertEqual(row["name"], sub)
        self.assertEqual(row["fp_submission_status"], "Submitted")
        self.assertEqual(set(row), {"name", "creation", "owner", "fp_submission_status", "answers"})
        a = row["answers"]
        self.assertEqual(a["hostel"], "Yes")
        self.assertEqual(a["courses"], "A, C")
        self.assertEqual(a["notes"], "")
        self.assertTrue(a["cv"].endswith(".png") and "/" not in a["cv"], a["cv"])
        self.assertEqual(set(a), {c["fieldname"] for c in result["columns"]})

    def test_export_has_the_same_columns(self):
        form = self.make_form(fields=self.FIELDS)
        self.submit(form, your_name=f"{PREFIX} Asha", mobile=_phone(), hostel=0)
        table = get_submission_table(form_id=form.name)
        export_submissions(form_id=form.name, file_type="CSV")
        import csv
        import io

        header = next(csv.reader(io.StringIO(frappe.response["result"])))
        self.assertEqual(header[0], "Column Labels:")
        self.assertEqual(header[1:5], ["ID", "Created On", "Created By", "Submission Status (Form)"])
        self.assertEqual(header[5:], [c["label"] for c in table["columns"]])  # same columns, same order
        self.assertNotIn("Heading", header)

    def test_export_over_http_is_a_csv_attachment(self):
        """Real HTTP GET (what the browser does) as a logged-in System Manager: status, type and
        Content-Disposition must make the browser save a file."""
        from frappe.utils.password import update_password

        form = self.make_form(fields=self.FIELDS)
        self.submit(form, your_name=f"{PREFIX} Asha", mobile=_phone())
        user = frappe.get_doc(
            {
                "doctype": "User",
                "email": "f2test_exporter@example.com",
                "first_name": PREFIX,
                "send_welcome_email": 0,
                "roles": [{"role": "System Manager"}],
            }
        ).insert(ignore_permissions=True)
        self._extra_users.append(user.name)
        password = frappe.generate_hash(length=20)
        update_password(user.name, password)
        frappe.db.commit()
        base = "http://127.0.0.1:8000"
        headers = {"Host": frappe.local.site}
        session = requests.Session()
        self.assertEqual(
            session.post(base + "/api/method/login", data={"usr": user.name, "pwd": password}, headers=headers).status_code,
            200,
        )
        res = session.get(
            base + "/api/method/forms_pro.api.export.export_submissions",
            params={"form_id": form.name, "file_type": "CSV"},
            headers=headers,
            timeout=30,
        )
        print("EXPORT-HTTP", res.status_code, res.headers.get("Content-Type"), res.headers.get("Content-Disposition"))
        self.assertEqual(res.status_code, 200)
        self.assertIn("text/csv", res.headers.get("Content-Type", ""))
        self.assertIn("attachment", res.headers.get("Content-Disposition", ""))
        self.assertIn("Submissions_", res.headers.get("Content-Disposition", ""))
        self.assertIn(f"{PREFIX} Asha", res.text)

    def test_table_needs_read_permission(self):
        form = self.make_form(fields=self.FIELDS)
        frappe.set_user("Guest")
        try:
            with self.assertRaises(frappe.PermissionError):
                get_submission_table(form_id=form.name)
        finally:
            frappe.set_user("Administrator")


def _stub(fieldname, fieldtype="Data", label=None, reqd=0, hidden=0, conditional_logic=None, options=None):
    return SimpleNamespace(
        fieldname=fieldname,
        fieldtype=fieldtype,
        label=label or fieldname,
        reqd=reqd,
        hidden=hidden,
        conditional_logic=conditional_logic,
        options=options,
    )


class TestVisibilityAndSingleChoice(F2TestBase):
    def _logic(self, action):
        return json.dumps(
            {
                "target_field": "target",
                "action": action,
                "conditions": [{"fieldname": "trigger", "operator": "Is", "value": "yes"}],
            }
        )

    def test_show_field_target_not_required_while_hidden(self):
        form = SimpleNamespace(
            fields=[
                _stub("trigger", "Data", conditional_logic=self._logic("Show Field")),
                _stub("target", "Data", reqd=1),  # its own Hidden box is NOT ticked
            ]
        )
        _validate_form_response(form, {"trigger": "no"})  # must not raise: target is hidden, rule not met
        with self.assertRaises(frappe.ValidationError):
            _validate_form_response(form, {"trigger": "yes"})  # rule met -> visible -> required

    def test_rule_carried_by_the_target_question_itself(self):
        # F3 stores the rule on the shown question, target_field = its own fieldname
        rule = json.dumps(
            {
                "target_field": "interests",
                "action": "Show Field",
                "conditions": [{"fieldname": "which_course", "operator": "Is", "value": "CA Inter"}],
            }
        )
        form = SimpleNamespace(
            fields=[
                _stub("which_course", "Single Choice", options="CA Inter\nCA Final"),
                _stub("interests", "Data", reqd=1, conditional_logic=rule),
            ]
        )
        _validate_form_response(form, {"which_course": "CA Final"})  # hidden, not required
        with self.assertRaises(frappe.ValidationError):
            _validate_form_response(form, {"which_course": "CA Inter"})  # shown, required

    def test_multiselect_condition_is_exact_membership_not_substring(self):
        rule = json.dumps(
            {
                "target_field": "extra",
                "action": "Show Field",
                "conditions": [{"fieldname": "courses", "operator": "Is", "value": "Art"}],
            }
        )
        form = SimpleNamespace(
            fields=[
                _stub("courses", "Multiselect", options="Art\nArtisan"),
                _stub("extra", "Data", reqd=1, conditional_logic=rule),
            ]
        )
        _validate_form_response(form, {"courses": ["Artisan"]})  # "Art" is inside "Artisan" but not chosen
        _validate_form_response(form, {"courses": json.dumps(["Artisan"])})
        with self.assertRaises(frappe.ValidationError):
            _validate_form_response(form, {"courses": ["Art", "Artisan"]})

    def test_hide_field_target_stays_visible_until_met(self):
        form = SimpleNamespace(
            fields=[
                _stub("trigger", "Data", conditional_logic=self._logic("Hide Field")),
                _stub("target", "Data", reqd=1),
            ]
        )
        with self.assertRaises(frappe.ValidationError):
            _validate_form_response(form, {"trigger": "no"})
        _validate_form_response(form, {"trigger": "yes"})  # met -> hidden -> not required

    def test_hidden_box_still_hides(self):
        form = SimpleNamespace(fields=[_stub("target", "Data", reqd=1, hidden=1)])
        _validate_form_response(form, {})

    def test_single_choice_must_be_one_of_the_options(self):
        form = SimpleNamespace(fields=[_stub("pick", "Single Choice", options="Red\nGreen\nBlue")])
        _validate_form_response(form, {"pick": "Green"})
        _validate_form_response(form, {"pick": ""})  # optional and empty
        with self.assertRaises(frappe.ValidationError):
            _validate_form_response(form, {"pick": "Purple"})

    def test_single_choice_required_when_empty(self):
        form = SimpleNamespace(fields=[_stub("pick", "Single Choice", reqd=1, options="Red\nGreen")])
        with self.assertRaises(frappe.ValidationError):
            _validate_form_response(form, {"pick": ""})

    def test_select_value_must_be_an_option(self):
        form = SimpleNamespace(fields=[_stub("pick", "Select", options="\nRed\nGreen")])
        with self.assertRaises(frappe.ValidationError):
            _validate_form_response(form, {"pick": "Purple"})


class TestSettingsSourceUrl(F2TestBase):
    def test_source_url_empty_when_unset_and_read_from_site_config(self):
        frappe.local.conf.pop("forms_pro_source_url", None)
        self.assertEqual(get_website_settings()["source_url"], "")
        frappe.local.conf["forms_pro_source_url"] = "https://example.invalid/src"
        self.assertEqual(get_website_settings()["source_url"], "https://example.invalid/src")

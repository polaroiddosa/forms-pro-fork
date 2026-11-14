"""Track F6 tests: who may use the form builder (found by a counsellor-account test on 2026-11-14).

A signed-in user holding only a CRM role (Sales User) must not get the builder page, must not
list a team's forms, and must not read a draft form. Team members, System Managers and
visitors for published forms keep working.
Plain frappe APIs on the F2 test base, like test_f2 and test_f5, because frappe_factory_bot is not installed on the local test stack
(the fork guidance prefers factories; move these fixtures over once the package is available).
Run: bench --site <site> run-tests --module forms_pro.tests.test_f6
"""

import frappe
from frappe.utils import set_request
from frappe.website.serve import get_response

from forms_pro.api.form import get_form
from forms_pro.api.submission import test_wave2_f2 as f2
from forms_pro.api.team import get_team_forms


class BuilderAccessBase(f2.F2TestBase):
    def make_user(self, roles, tag):
        email = f"f6-{tag}-{frappe.generate_hash(length=5)}@ta-crm.internal"
        user = frappe.get_doc(
            {
                "doctype": "User",
                "email": email,
                "first_name": f"F6 {tag}",
                "send_welcome_email": 0,
                "enabled": 1,
                "user_type": "System User",
                "roles": [{"role": r} for r in roles],
            }
        ).insert(ignore_permissions=True)
        self._extra_users.append(user.name)
        return user.name

    def as_user(self, user, fn, *args, **kwargs):
        frappe.set_user(user)
        try:
            return fn(*args, **kwargs)
        finally:
            frappe.set_user("Administrator")

    def get_page(self, user, path):
        frappe.set_user(user)
        try:
            set_request(path=path, method="GET")
            return get_response(path)
        finally:
            frappe.set_user("Administrator")
            frappe.local.request = None


class TestTeamFormList(BuilderAccessBase):
    def test_sales_user_cannot_list_a_team_forms(self):
        form = self.make_form(published=False)
        sales = self.make_user(["Sales User"], "sales")
        with self.assertRaises(frappe.PermissionError):
            self.as_user(sales, get_team_forms, team_id=form.linked_team_id)

    def test_team_member_can_list(self):
        form = self.make_form(published=False)
        member = self.make_user(["Forms Pro User"], "member")
        team = frappe.get_doc("FP Team", form.linked_team_id)
        team.append("users", {"user": member})
        team.save(ignore_permissions=True)
        names = [c["name"] for c in self.as_user(member, get_team_forms, team_id=form.linked_team_id)]
        self.assertIn(form.name, names)

    def test_known_limit_any_forms_pro_user_can_list_any_team(self):
        """Documents upstream behaviour, not a wish: the Forms Pro User role has read on FP Team for
        every team (no per-team rule exists), so team membership is not a boundary between builder
        users. On the academy CRM all builder users share one team, so nothing is exposed today.
        If a per-team rule is ever added, flip this test to assertRaises(frappe.PermissionError)."""
        form = self.make_form(published=False)
        outsider = self.make_user(["Forms Pro User"], "outsider")
        names = [c["name"] for c in self.as_user(outsider, get_team_forms, team_id=form.linked_team_id)]
        self.assertIn(form.name, names)

    def test_system_manager_can_list(self):
        form = self.make_form(published=False)
        manager = self.make_user(["System Manager"], "manager")
        names = [c["name"] for c in self.as_user(manager, get_team_forms, team_id=form.linked_team_id)]
        self.assertIn(form.name, names)

    def test_unknown_team_is_not_found(self):
        with self.assertRaises(frappe.DoesNotExistError):
            get_team_forms(team_id="f6-no-such-team")


class TestDraftFormHidden(BuilderAccessBase):
    def test_guest_cannot_read_a_draft(self):
        form = self.make_form(published=False)
        with self.assertRaises(frappe.DoesNotExistError):
            self.as_user("Guest", get_form, form_id=form.name)

    def test_sales_user_cannot_read_a_draft(self):
        form = self.make_form(published=False)
        sales = self.make_user(["Sales User"], "sales2")
        with self.assertRaises(frappe.DoesNotExistError):
            self.as_user(sales, get_form, form_id=form.name)

    def test_guest_can_still_read_a_published_form(self):
        form = self.make_form(published=True)
        data = self.as_user("Guest", get_form, form_id=form.name)
        self.assertEqual(data["name"], form.name)
        self.assertTrue(data["is_published"])

    def test_administrator_can_read_a_draft(self):
        form = self.make_form(published=False)
        self.assertEqual(get_form(form_id=form.name)["name"], form.name)


class TestBuilderPage(BuilderAccessBase):
    def test_sales_user_gets_the_no_access_page(self):
        sales = self.make_user(["Sales User"], "sales3")
        res = self.get_page(sales, "/form-builder")
        self.assertEqual(res.status_code, 403)
        self.assertIn(b"do not have access to the form builder", res.data)
        self.assertNotIn(b'<div id="app">', res.data)

    def test_sales_user_gets_no_access_on_a_builder_subpage_too(self):
        sales = self.make_user(["Sales User"], "sales4")
        self.assertEqual(self.get_page(sales, "/form-builder/edit-form/abc").status_code, 403)

    def test_forms_pro_user_gets_the_builder(self):
        member = self.make_user(["Forms Pro User"], "builder")
        res = self.get_page(member, "/form-builder")
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"<title>Forms Pro</title>", res.data)

    def test_system_manager_gets_the_builder(self):
        manager = self.make_user(["System Manager"], "builder2")
        self.assertEqual(self.get_page(manager, "/form-builder").status_code, 200)

    def test_visitor_not_signed_in_keeps_the_old_behaviour(self):
        res = self.get_page("Guest", "/form-builder")
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"<title>Forms Pro</title>", res.data)

    def test_public_form_page_is_not_affected_for_a_sales_user(self):
        form = self.make_form(published=True)
        sales = self.make_user(["Sales User"], "sales5")
        self.assertEqual(self.get_page(sales, f"/f/{form.route}").status_code, 200)


class TestDuplicatePhoneDigitsOnly(f2.F2TestBase):
    """The duplicate-phone flag compares digits only (found on staging 2026-11-14: three spellings of
    one number made three unflagged leads)."""

    def _flags(self, lead_name):
        return frappe.get_all(
            "Comment", filters={"reference_name": lead_name, "comment_type": "Info"}, pluck="content"
        )

    def _two_leads(self, first_phone, second_phone):
        form = self.make_form()
        before = set(self.lead_names())
        self.submit(form, **self.good(mobile=first_phone))
        first = (set(self.lead_names()) - before).pop()
        before = set(self.lead_names())
        self.submit(form, **self.good(mobile=second_phone, your_name=f"{f2.PREFIX} Again"))
        second = (set(self.lead_names()) - before).pop()
        return first, second

    def _assert_flagged(self, first, second):
        self.assertTrue(any(c.startswith("Possible duplicate of " + first) for c in self._flags(second)), self._flags(second))
        self.assertTrue(any(c.startswith("Re-enquiry") and second in c for c in self._flags(first)), self._flags(first))

    def test_spaces_in_the_number_are_ignored(self):
        self._assert_flagged(*self._two_leads("+919123456701", "+91 91234 56701"))

    def test_dashes_in_the_number_are_ignored(self):
        self._assert_flagged(*self._two_leads("+919123456702", "+91-9123456702"))

    def test_brackets_and_dashes_are_ignored(self):
        self._assert_flagged(*self._two_leads("+919123456703", "+91 (912) 345-6703"))

    def test_different_numbers_are_still_not_flagged(self):
        first, second = self._two_leads("+919123456704", "+919123456705")
        self.assertFalse(any("duplicate" in c.lower() for c in self._flags(second)))
        self.assertFalse(any("Re-enquiry" in c for c in self._flags(first)))

    def test_same_digits_but_different_country_code_is_not_flagged(self):
        first, second = self._two_leads("+919123456706", "+449123456706")
        self.assertFalse(any("duplicate" in c.lower() for c in self._flags(second)))

    def test_phone_digits_helper(self):
        from forms_pro.api.submission.lead_bridge import phone_digits

        self.assertEqual(phone_digits("+91 90000-00002"), "919000000002")
        self.assertEqual(phone_digits(None), "")
        self.assertEqual(phone_digits("abc"), "")


class TestPublicEndpointsClosed(BuilderAccessBase):
    """Found 2026-11-14: get_link_field_options and get_doctype_fields were open to visitors, and
    the first read any record type without permission checks (lead, user and call-log names)."""

    def test_visitor_cannot_call_either_endpoint(self):
        from forms_pro.api.form import endpoints

        frappe.set_user("Guest")
        try:
            for fn in (endpoints.get_link_field_options, endpoints.get_doctype_fields):
                with self.subTest(fn=fn.__name__), self.assertRaises(frappe.PermissionError):
                    frappe.is_whitelisted(fn)
        finally:
            frappe.set_user("Administrator")

    def test_signed_in_user_without_read_permission_is_refused(self):
        from forms_pro.api.form import get_link_field_options

        sales = self.make_user(["Sales User"], "linkopts")
        with self.assertRaises(frappe.PermissionError):
            self.as_user(sales, get_link_field_options, doctype="Error Log")

    def test_system_manager_still_gets_options(self):
        from forms_pro.api.form import get_link_field_options

        manager = self.make_user(["System Manager"], "linkopts2")
        rows = self.as_user(manager, get_link_field_options, doctype="Role", page_length=5)
        self.assertTrue(rows and set(rows[0]) == {"value", "label"})

    def test_page_length_is_capped(self):
        from forms_pro.api.form import get_link_field_options
        from forms_pro.api.form.endpoints import MAX_LINK_OPTIONS

        rows = get_link_field_options(doctype="DocType", page_length=999999)
        self.assertLessEqual(len(rows), MAX_LINK_OPTIONS)

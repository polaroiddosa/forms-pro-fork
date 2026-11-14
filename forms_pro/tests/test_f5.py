"""Track F5 tests: /f/<name> status codes, and the submission count on My forms cards.

Plain frappe APIs only (frappe_factory_bot is not installed on the local test stack), built
on the F2 test base so forms, doctypes and teams are created and removed the same way.
Run: bench --site <site> run-tests --module forms_pro.tests.test_f5
"""

import frappe
from frappe.utils import set_request
from frappe.website.serve import get_response

from forms_pro.api.submission import test_wave2_f2 as f2
from forms_pro.api.team import get_team_forms


class TestPublicFormStatus(f2.F2TestBase):
    def _get(self, path: str):
        frappe.set_user("Guest")
        try:
            set_request(path=path, method="GET")
            return get_response(path)
        finally:
            frappe.set_user("Administrator")
            frappe.local.request = None

    def test_published_form_is_200(self):
        form = self.make_form(published=True)
        res = self._get(f"/f/{form.route}")
        self.assertEqual(res.status_code, 200)
        # still the fork's app page, with its real csrf token
        self.assertIn(b"<title>Forms Pro</title>", res.data)
        self.assertNotIn(b"{{ csrf_token }}", res.data)

    def test_unknown_form_is_404_with_friendly_page(self):
        res = self._get("/f/f5test-no-such-form")
        self.assertEqual(res.status_code, 404)
        self.assertIn(b"This form is not available", res.data)
        # the 404 page is not the app shell
        self.assertNotIn(b'<div id="app">', res.data)

    def test_unpublished_form_is_404(self):
        form = self.make_form(published=False)
        res = self._get(f"/f/{form.route}")
        self.assertEqual(res.status_code, 404)
        self.assertIn(b"This form is not available", res.data)

    def test_edit_page_of_published_form_is_200_and_of_unknown_form_404(self):
        form = self.make_form(published=True)
        self.assertEqual(self._get(f"/f/{form.route}/edit/SUB-0001").status_code, 200)
        self.assertEqual(self._get("/f/f5test-no-such-form/edit/SUB-0001").status_code, 404)

    def test_form_builder_page_is_untouched(self):
        res = self._get("/form-builder")
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"<title>Forms Pro</title>", res.data)

    def test_trailing_slash_and_empty_route(self):
        form = self.make_form(published=True)
        self.assertEqual(self._get(f"/f/{form.route}/").status_code, 200)
        self.assertEqual(self._get("/f/").status_code, 404)


class TestSubmissionCount(f2.F2TestBase):
    FIELDS = f2.BASIC_FIELDS

    def _card(self, form):
        cards = get_team_forms(team_id=form.linked_team_id)
        return next(c for c in cards if c["name"] == form.name)

    def test_zero_before_any_answer(self):
        form = self.make_form()
        self.assertEqual(self._card(form)["submission_count"], 0)

    def test_counts_only_submitted_answers_of_this_form(self):
        form = self.make_form()
        other = self.make_form()
        for i in range(2):
            self.submit(form, your_name=f"{f2.PREFIX} count {i}", mobile=f2._phone())
        self.submit(other, your_name=f"{f2.PREFIX} other", mobile=f2._phone())
        self.assertEqual(self._card(form)["submission_count"], 2)
        self.assertEqual(self._card(other)["submission_count"], 1)

    def test_draft_rows_are_not_counted(self):
        from forms_pro.utils.teams import count_submissions

        form = self.make_form()
        row = frappe.get_doc({"doctype": form.linked_doctype, "fp_linked_form": form.name, "fp_submission_status": "Draft"})
        row.insert(ignore_permissions=True, ignore_mandatory=True)
        self.assertEqual(count_submissions(form.linked_doctype, form.name), 0)

    def test_missing_doctype_counts_zero(self):
        from forms_pro.utils.teams import count_submissions

        self.assertEqual(count_submissions("No Such DocType F5", "x"), 0)
        self.assertEqual(count_submissions(None, "x"), 0)

    def test_card_carries_route_for_the_copy_link_button(self):
        form = self.make_form()
        self.assertTrue(self._card(form)["route"])

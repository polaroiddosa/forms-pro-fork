# CHANGES-F2 (backend track, 2026-11-14)

Edited only under `app/forms_pro/api/`. Paths below are relative to that folder.

## Files
| File | Change |
|---|---|
| `submission/consent.py` (new) | `CONSENT_LABEL`, `CONSENT_TEXT` (academy wording, source quoted in the docstring), refusal message, `is_consent_given`. |
| `submission/lead_bridge.py` (new) | C2: documented mapping contract at the top; creates the CRM Lead (consent Given, source "Website form" always, status New if empty, campaign = form title if empty, `lead_owner` cleared with `""`), ensures the CRM Lead Source "Website form" exists, duplicate flag (exact `mobile_no`, comment on both leads), note "Form answers: <title>" (HTML-escaped), private files attached to the lead plus a comment per file. |
| `submission/uploads.py` (new) | C3: parse `"<name>,data:<mime>;base64,<data>"`; extension (pdf, jpg, jpeg, png, webp, doc, docx), real decoded size max 5 MB, magic bytes, max 3 files; creates PRIVATE File. Academy error texts. |
| `submission/display.py` (new) | Display values shared by the answers table and the note. |
| `submission/endpoints.py` | `submit_form_response(..., consent=0)`: rate limit (10/min per IP per form, `frappe.rate_limiter.rate_limit`; real IP depends on the proxy passing the visitor address), guest drafts refused, unpublished form refuses everything before anything is read, consent required for Submitted, files checked before any write, submission row kept, lead bridge called. `_validate_form_response`: Show Field target hidden until met, Single Choice and Select value must be an option, Multiselect conditions use exact membership. New `get_submission_table(form_id)`. |
| `submission/__init__.py` | exports `get_submission_table`. |
| `form/endpoints.py` | `get_form` returns `consent_label`, `consent_text` (so also the builder views). |
| `settings/endpoints.py` | `source_url` from site config `forms_pro_source_url` ("" if unset). |
| `submission/test_wave2_f2.py` (new) | 32 tests. |
| `export/endpoints.py` | NOT changed: the CSV already has exactly the same columns, labels and order as `get_submission_table` (test `test_export_has_the_same_columns`). |

## The four alignment points from the coordinator (F3)
1. Rule looked up by `target_field == this field`, whichever question carries it: `test_rule_carried_by_the_target_question_itself` (rule on the shown question) and `test_show_field_target_not_required_while_hidden` (rule on the trigger question).
2. Show Field target hidden until met even with Hidden unticked; Hide Field target visible until met: `test_show_field_target_not_required_while_hidden`, `test_hide_field_target_stays_visible_until_met`, `test_hidden_box_still_hides`.
3. Multiselect comparison is exact membership (list or JSON string): `test_multiselect_condition_is_exact_membership_not_substring`.
4. Single Choice validated like a select (and plain Select too): `test_single_choice_must_be_one_of_the_options`, `test_single_choice_required_when_empty`, `test_select_value_must_be_an_option`.

## Tests, how to run
Plain frappe APIs (frappe_factory_bot is NOT installed on the test stack, so the old `test_export.py` and other factory tests cannot run there; not touched).
Needed `bench --site fp-fork.localhost set-config allow_tests true` (I set it on the throwaway test site).
```
docker cp <files> fp-fork-backend-1:/home/frappe/frappe-bench/apps/forms_pro/forms_pro/api/...
bench --site fp-fork.localhost run-tests --module forms_pro.api.submission.test_wave2_f2
```
Result: Ran 32 tests, OK. `test_submission_validation` (existing, 35 tests): OK. Tests create `F2TEST` data and remove it; checked afterwards: 0 leads, 0 test doctypes, 0 test users/files/custom fields/property setters left (the one remaining Form is F1's "Fork Route Test Form").

## Fails-without-the-change proof
Each change was removed in turn in the container copy and the matching test re-run (script in the session scratchpad, log `mutation-log.txt`); every one failed, then the real file was restored. Mutations: consent check, lead call, payload-tamper (status/owner/source taken from the payload), `lead_owner` clear, duplicate flag, note escaping, 5 MB limit, extension allow-list plus magic check together, magic check alone, private flag, unpublished check, rate-limit decorator, table columns, table display values, Show Field rule, Single Choice check, guest draft, consent keys, `source_url`, Multiselect substring.
Two honest notes: (a) removing the extension allow-list alone does NOT fail `.exe`/`.html` tests, because the magic-byte check also refuses them (two layers); removing both fails them. (b) Removing the `lead_owner` clear only fails the test because the test site gives `lead_owner` a default via a Property Setter; on a site with no default the line has no visible effect.

## Findings / differences from the plan
- `fp_lead` on the submission row: SKIPPED (needs a change in `utils/form_generator.py`, not mine).
- Phone questions: Frappe's own check requires a country code ("+91..."); a number typed without one is refused with Frappe's message. F4's phone input should add the code.
- Duplicate wording uses the form title where the academy script used the form route.
- Mapping uses the first Phone/Email question literally; if that question is left empty the lead has no phone/email even if a later one is filled.
- Missing consent custom fields on CRM Lead: lead is still created and an error log entry is written (production has them).
- Draft saves for logged-in users keep working; their files are attached to the submission row instead of a lead.
- `get_form` (guest) still returns unpublished forms' definitions (upstream behaviour, not changed); submit refuses them.
- Export download: tested over real HTTP as a logged-in System Manager: 200, `text/csv`, `Content-Disposition: attachment; filename=Submissions_...csv`, and an empty form also returns a header-only CSV. Cause of a missing download in the backend: NOT FOUND. Likely causes are outside this track: a user without Form write permission gets a JSON error, which a `window.location.href` jump would show as a page (F4 already moved to fetch).

## NOT proven
- Rate limit tested only with a faked request IP in-process; real proxy header (Cloudflare to Caddy) not tested.
- Guest 403 on the file URL proven on the local gunicorn (with a logged-in control returning 200); not behind the academy Caddy/Cloudflare.
- Round-robin assignment itself (no Assignment Rule on the test site); only that the owner is left empty.
- Real academy CRM Lead custom fields (types may differ from the Data/Datetime/Check I created in test setup); not run against staging or live.
- Real Word/PDF files with real parsers; only magic-byte sniffing and a real PNG tested.
- Old factory-based tests (`test_export.py`, `test_submission.py`, form tests) not run (missing app).

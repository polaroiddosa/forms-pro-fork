# F6: who may use the form builder (2026-11-14)

Found by testing with a user who holds only a CRM role (Sales User).

## Problems found (live, Verified)
1. The builder page opened for any signed-in staff member, including counsellors.
2. `get_team_forms` listed a team's forms (title, link name, published flag, answer count) to any signed-in user who knew the team id (it used `frappe.get_all` with no permission check).
3. `get_form` (public on purpose, so published forms render for visitors) also returned an unpublished form's title and questions to anyone who knew the form id.
Answers, members and the manage screens were already refused (403). A counsellor could not create a form or a team.

## Changes
| File | Change |
|---|---|
| `forms_pro/api/team/endpoints.py` | `get_team_forms` now has `@require_permission("FP Team", "read", param="team_id")`, like `get_team_members` and `get_team_for_manage`: 403 without read on the team, 404 for an unknown team |
| `forms_pro/api/form/endpoints.py` | `get_form` (and so `get_form_by_route`) returns an unpublished form only to a user who may read it; everyone else gets "Form not found" (404). Published forms are unchanged for visitors |
| `forms_pro/www/form_builder.py` | A signed-in user without `Forms Pro User` or `System Manager` who opens `/form-builder` or a sub-page gets HTTP 403 and a plain page; visitors who are not signed in and `/f/...` public pages are unchanged |
| `forms_pro/templates/form_no_access.html` | New page: "You do not have access to the form builder ... please ask your administrator" (same brand look as `form_not_found.html`) |
| `forms_pro/tests/test_f6.py` | 15 tests; 6 behaviour tests fail on the previous code (fa2e412) and all 15 pass now |

## Added in the same build: duplicate phone check ignores spaces and dashes (2026-11-14)
Found on staging: "+91 9000000002", "+91-9000000002" and "+919000000002" made three leads and none was flagged as a duplicate, because `flag_duplicates` compared the exact typed text.

| File | Change |
|---|---|
| `forms_pro/api/submission/lead_bridge.py` | New `phone_digits()`; `flag_duplicates` now compares digits only (SQL `REGEXP_REPLACE(mobile_no, '[^0-9]', '')`). Fewer than 7 digits never matches. The country code still counts ("+44..." and "+91..." with the same last digits are different numbers). Nothing is merged or deleted; the same "Possible duplicate" and "Re-enquiry" comments are added |
| `forms_pro/tests/test_f6.py` | 6 more tests (21 in total); 4 of the new ones fail on the previous code |

## Also changed in the same build: two endpoints no longer open to visitors
`get_link_field_options` and `get_doctype_fields` were callable without signing in, and the first read records with `frappe.get_all` (no permission check). Both now need a signed-in user; `get_link_field_options` also needs read permission on the record type, reads with `frappe.get_list` (permission-checked) and caps the result size at 200. Tests in `forms_pro/tests/test_f6.py`.

## Known limit (upstream design, not changed)
The `Forms Pro User` role has read on `FP Team` for **every** team; there is no per-team rule. So anyone given that role can list any team's forms and members. In a deployment where every builder user is in one team, nothing is exposed. `test_known_limit_any_forms_pro_user_can_list_any_team` documents this. Do not give the role to someone who must not see the academy's forms.

## Not changed
`get_doctype_fields` and `get_link_field_options` are public (guest) endpoints in the upstream code; not reviewed here.

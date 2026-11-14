# Track F5 changes (My forms cards, duplicate-question wording, real 404 for /f/<unknown>)

Date 2026-11-14, to-do #2622. Target image tag `ta-crm:v1.87.0-wa2-fp3` (NOT built, see "Image"). Nothing committed or deployed. Paths relative to `app/` unless noted.

## 1. My forms cards: Copy link button and answers count
| File | Change |
|---|---|
| forms_pro/utils/teams.py | `get_team_forms` now also returns `submission_count` per form (new `count_submissions()`): rows of the form's own doctype with `fp_linked_form = form` and `fp_submission_status = "Submitted"` (the same rows the answers table lists; drafts not counted). A missing doctype counts 0. Schema `GetTeamFormsResponseSchema` gets `submission_count: int = 0`. |
| frontend/src/utils/publicLink.ts (new) | `publicFormLink(route, origin)` = `<origin>/f/<route>`, `copyText()` (Clipboard API with textarea fallback), `answersLabel()` ("No answers yet", "1 answer", "N answers"). |
| frontend/src/components/dashboard/FormPreviewCard.vue | Shows the answers label (`data-form-card-answers`) and a "Copy link" button (`data-form-card-copy-link`, turns to "Copied" for 2 s, toast). Button uses `@click.stop` so the click does not open the form. The link uses the form's `route` (the public URL is `/f/<route>`, e.g. `/f/forms_pro_ab12cd34`; the form `name` is not the public path). |

Note: the button shows for every form that has a route, drafts too. A draft's link is a 404 until the form is published (change 3). If a draft should not offer the button, add `props.form.is_published &&` to the `v-if` (one word; left as is because the task said per-form).

## 2. Duplicate question dialog wording
| File | Change |
|---|---|
| frontend/src/utils/duplicateQuestions.ts (new) | `findDuplicateQuestions()` (moved unchanged from the store) and `duplicateQuestionDialog()`. Title "Two questions look the same". Message: "These questions have the same text, or nearly the same: <b>...</b>. Please change the question text of one of them so that each question is different." No mention of Fieldname, no stored name in brackets; each question text listed once, HTML-escaped. |
| frontend/src/stores/editForm.ts | `save()` uses the two helpers; the old inline function and the old message ("set a unique fieldname") are removed. |

## 3. /f/<unknown> returns a real 404
| File | Change |
|---|---|
| forms_pro/www/form_builder.py | Name kept (underscore rule, ROUTE-CHANGES.md correction). `get_context` now checks `request.path`: for `/f/<route>` and `/f/<route>/edit/<submission>` it looks for a Form with that `route` and `is_published = 1` (`public_form_exists`). If none: `context.http_status_code = 404` and `context.template = forms_pro/templates/form_not_found.html`. `/form-builder/...` and a published `/f/<route>` are untouched (200, real csrf token). Empty `/f/` is 404. |
| forms_pro/templates/form_not_found.html (new) | Standalone friendly page in the academy brand (cream background, Fraunces heading, logo, phone-first), "This form is not available", `noindex`. Assets from `/assets/forms_pro/frontend/brand/` (the path the image copies to bench/assets; `/assets/forms_pro/brand/` is NOT copied by the Dockerfile). |

Behaviour change to know: an UNPUBLISHED form's `/f/<route>` was the app shell with 200 (the SPA then showed its own message); it is now the 404 page. Owners cannot preview a draft through `/f/`.

## Tests
| File | What |
|---|---|
| forms_pro/tests/test_f5.py (new, 11 tests) | 404 for unknown and unpublished, 200 for published (fork title, real csrf token), edit URL cases, `/form-builder` unchanged, trailing slash and empty route; submission count 0 / only this form's Submitted rows / drafts not counted / missing doctype. Run: `bench --site <site> run-tests --module forms_pro.tests.test_f5`. |
| frontend/src/utils/duplicateQuestions.test.ts, publicLink.test.ts (new, 8 tests) | Wording has no "fieldname", says "change the question text", escapes HTML; link and count label helpers. Run: `npx vitest run` in `frontend/`. |
| frontend/e2e/specs/form-card.spec.ts, public-form-404.spec.ts (new) | Playwright specs for the card and the 404/200 statuses. NOT RUN (no browser, no bench here). |
| tests/route_check.sh, tests/route_check_setup.py | New checks (f1, f1b, f2, f3, f3b) and `make_unpublished_form`. Setup for f3: run `make_unpublished_form` once in the container like the other two. |

## Proof the 404 test fails on the old code
Old `form_builder.py`/`teams.py` copy in the local test stack container (`fp-fork-backend-1`): `test_f5` Ran 11, FAILED (failures=3, errors=4): `test_unknown_form_is_404_with_friendly_page`, `test_unpublished_form_is_404`, `test_edit_page_of_published_form_is_200_and_of_unknown_form_404` all `AssertionError: 200 != 404`. Over real HTTP the same old code gave `route_check.sh` `(f1)(f1b)(f3)(f3b)` FAIL with `http=200`. After the change: `test_f5` Ran 11 OK; `route_check.sh` RESULT pass=14 fail=0 (after restarting the container's gunicorn so it loaded the new Python).

## Image
`ta-crm:v1.87.0-wa2-fp3` NOT built locally: the base `ta-crm:v1.87.0-wa2` exists only on the academy server (local has `ta-crm:v1.87.0` without the wa2 changes; building on it and tagging fp3 would be a wrong image). Build on the server by the runbook method, from `crm-kit/forms-pro-fork/`:
`docker build -f image/Dockerfile --build-arg BASE_IMAGE=ta-crm:v1.87.0-wa2 -t ta-crm:v1.87.0-wa2-fp3 .`
Then the runbook's post-switch steps (clear-website-cache, clear-cache, check csrf on `/form-builder`). The frontend itself builds locally (`vite build` OK in a scratch bench layout).

## Not proven
- Browser behaviour of the card (clipboard, button not opening the form, layout at phone width): no browser here; e2e specs written, not run.
- Caddy: the live `@crmforms` block must pass `/f/*` through unchanged (it already does for 200); a 404 status from the backend passes through, but not tested through Caddy/Cloudflare.
- Existing `test_wave2_f2` has 1 failure in the local stack (`test_different_phone_is_not_flagged`): a leftover "Possible duplicate of CRM-LEAD-2026-00001" Comment from 13:23 IST, before this track, matches its global `%duplicate%` query. Not caused by F5 (the test stack was not otherwise cleaned).
- The local stack's container also carries the older `consent.py` (differs from the repo copy); F5 did not touch it.

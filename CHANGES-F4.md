# Track F4 changes (visitor page, brand, answers screen)

Date 2026-11-14. Paths relative to `app/`. Nothing committed. Frontend only.

## Files
| File | Change | Why |
|---|---|---|
| frontend/src/pages/SubmissionPage.vue | Rewritten. Own brand header with academy logo (replaces `PageHeader`, which showed the placeholder box and a Login button), `.ta-brand` wrapper, no "Built on Forms Pro" badge, footer, consent, own Submit (see "Submit call site"), phone-first layout (full-width buttons, stacked on phones). No "Save as draft" button (C1: guests cannot draft). | C1, C7, C8 |
| frontend/src/components/fields/ConsentCheckbox.vue | New. Fixed consent tick: label from `consent_label`, help text from `consent_text`. | C1 |
| frontend/src/components/fields/PublicFooter.vue | New. "Enquiries are handled by Transparent Academy." plus "Source code" link only when `source_url` is non-empty. | C7, C8 |
| frontend/src/components/fields/attachment.ts | New helper: type check (pdf, jpg, jpeg, png, webp, doc, docx), 5 MB check, builds `name,data:<mime>;base64,<data>` (mime from extension, comma in name replaced by `_`), 3-file limit helper. | C3 |
| frontend/src/components/fields/attachment.test.ts | New vitest tests (23). | C3 |
| frontend/src/components/fields/Attachment.vue | FileUploader removed. Plain hidden file input + "Choose file" button, chosen name and size, Remove button, error text. Never calls `upload_file`. | C3 |
| frontend/src/components/form/submissions/SubmissionList.vue | Table from `get_submission_table`: Date, Status, one column per question. One "Download CSV" button (Excel button removed). CSV is fetched with the session cookie and saved through a temporary link. Row click opens a drawer. | C5 |
| frontend/src/components/form/submissions/SubmissionDetails.vue | Rewritten: shows one answer in full from the table row (no second API call). Files shown as names only, no links. | Screen list 6 |
| frontend/src/components/form/submissions/answers.ts, answers.test.ts | New: column and row building, CSV file name. 3 tests. | C5 |
| frontend/src/components/form/submissions/SubmissionFieldValue.vue | Not changed. Now unused (kept so a later merge does not conflict). | |
| frontend/src/assets/Logo.vue | Now renders the academy logo image (was the text "Forms Pro" in `font-instrument`). Used by `FormBuilderHeader.vue` (F3's file) too, so the builder header shows the academy logo. | C8 |
| frontend/src/index.css | Removed the Google Fonts import and the missing Instrument Serif `@font-face`. Added Fraunces and Source Sans 3 `@font-face` (from `/brand/`, local files) and the `.ta-brand` theme class (palette as CSS variables, overrides frappe-ui colour variables inside the wrapper). | C8 |
| forms_pro/public/brand/{logo.svg,font-display.woff2,font-body.woff2} | Copied unchanged from `projects/transparent-academy-crm/brand/`. | C8 |
| frontend/public/brand/ (same 3 files) | Same copy. Needed because the frontend build empties `forms_pro/public/frontend/` and Vite copies `public/` into it; CSS and the logo point at `/assets/forms_pro/frontend/brand/...`. The `forms_pro/public/brand/` copy is served at `/assets/forms_pro/brand/...` for other users (e.g. F2 emails). | C8 |

Not changed: `utils/form_fields.ts` (not needed), `tailwind.config.ts` (not mine; its `instrument` font family is now unused and can be removed by whoever owns it).

## Submit call site (consent): file outside my list
The stock submit is `app/frontend/src/stores/submissionForm.ts`, function `submitForm`, `makeParams()` at about lines 168-179 (the object with `form_id`, `form_data`, `submission_status`). It sends no `consent`. I did not edit it. Instead `SubmissionPage.vue` passes its own buttons through `FormRenderer`'s existing `actions` slot and sends the call itself with `consent: 1` (via frappe-ui `call`), then sets `store.inSuccessState`. If the main agent prefers the store path: add `consent: 1` (or a ref) to that `makeParams` object and make the Submit button call `store.submitForm()`; the page's `submit()` function can then be deleted. Do both only if the page's own `submit()` is removed, otherwise there is no harm but duplicate logic.
Known difference from the store path: the store also writes/clears a localStorage draft (`draft_submission_data_<id>`); the page's submit does not clear it. No code in the store writes it except through `useStorage` on load, so visitors on a shared phone could see an old draft merged in. The main agent may want `clearDraft()` exposed.

## CSV export: cause
Cause of the old behaviour (found by reading, not reproduced): the button did `window.location.href = /api/method/...export_submissions`, a plain navigation. On any server error or permission refusal the browser replaces the page with Frappe's JSON/HTML error and no file is saved; a browser cannot show the error nicely. The new code fetches with `credentials: "include"`, refuses to save a JSON/HTML reply and shows the server's message in a toast, otherwise downloads a Blob via a temporary `<a download>` (file name from `Content-Disposition`, else `<form title>.csv`). Whether the backend itself returns a correct CSV is F2's part and NOT proven here.

## Assumptions about F2's API (check when merging)
- Form API (`get_form_by_route`) returns `consent_label` and `consent_text` at the top level of `data`.
- Settings key `source_url` is read from `forms_pro.api.settings.get_website_settings` (the one guest settings function that exists today). If F2 puts it elsewhere, change the `createResource` url at the top of `SubmissionPage.vue`.
- `get_submission_table` returns `{columns:[{fieldname,label,fieldtype}], rows:[{name,creation,owner,fp_submission_status,answers:{}}]}` exactly as C5.
- If the form API lacks `consent_label`, the page shows no tick, keeps Submit disabled and shows "This form cannot be sent right now." (fails closed; I did not invent consent wording).

## Tests and build (in `.build-F4/frontend`, scratch copy of `app/frontend`)
- `yarn install --frozen-lockfile` needed yarn classic 1.22 (the laptop's yarn is 4.x and refuses the v1 lockfile): used `npx yarn@1.22.22 ... --cache-folder ../yarn-cache`.
- The build needs the bench layout (`src/socket.ts` imports `../../../../sites/common_site_config.json`), so `.build-F4/frontend` is a symlink to `.build-F4/bench/apps/forms_pro/frontend` with a dummy `bench/sites/common_site_config.json`. No source change.
- `yarn build`: succeeds. `vitest run`: 31 passed (23 attachment, 3 answers, 5 existing form_steps). Without `attachment.ts` the attachment test file fails to load; with the type and size checks removed, 8 tests fail.
- `vue-tsc --noEmit --ignoreDeprecations 6.0`: no errors in my files; 3 other errors (css side-effect imports in App.vue, ImageUploader.vue, main.ts) are not from this track.
- The scratch copy was last synced from `app/` before F3's later edits: only F3 files differ (`FormBuilderHeader.vue`, `BaseLayout.vue`, `Dashboard.vue`, `sidebarItems.ts`, `router.ts`); all F4 files are identical.

## Not proven (no browser, no backend)
- Nothing was looked at on screen. Colours via frappe-ui variable overrides are untested visually (inputs, focus rings, badge, success section, dark mode ignored: `color-scheme: light` is set).
- Font files load only if the built assets are served from `/assets/forms_pro/frontend/brand/`; the CSS URL was confirmed in the build output only.
- Uploaded base64 in the submit payload: size of the request (3 files x 5 MB x 1.33 = about 20 MB) against the proxy body limit (Caddy/Cloudflare) is untested. Cloudflare's default request limit is 100 MB but the Frappe `max_file_size`/site limits are unchecked.
- The 3-file limit state is module-level in `attachment.ts` (not per form instance); it resets on page reload only.
- The unused `SubmissionFieldValue.vue` still references old behaviour.

## Browser checklist for the main agent (phone width 390 px first, then desktop)
Public form `/f/<route>` (published form):
1. Header shows the academy logo (not a box, no "Forms Pro"); page background cream, text navy, headings in Fraunces, body in Source Sans 3 (DevTools, Network: both woff2 files return 200, no request to fonts.googleapis.com, no 404 for Instrument Serif).
2. No "Built on Forms Pro" badge anywhere. Footer reads "Enquiries are handled by Transparent Academy." No "Source code" link while `source_url` is empty; with `forms_pro_source_url` set the link appears and opens in a new tab.
3. At 390 px: no sideways scroll, card padding small, Submit full width, tap targets at least 44 px.
4. Consent: a box at the bottom with the API wording; Submit is greyed out until ticked; ticking enables it. Untick: disabled again. The red border on the consent box appears only after a click attempt.
5. Network tab on Submit: the `submit_form_response` request body contains `"consent": 1` and `submission_status: "Submitted"`. Server refusal text shows in red under the fields.
6. Multi-step form: consent and Submit only on the last step; Back and Next work; no "Save as draft".
7. Success state shows the builder's success message inside the branded page.
8. Unpublished form shows the "unpublished" card (the `FormUnpublishedState` component is global; not changed).
File field:
9. "Choose file" opens the picker limited to pdf/jpg/png/webp/doc/docx. Choosing a .exe or .gif (use "All files") shows the red refusal; a 6 MB file shows the 5 MB message; a good file shows its name, size and Remove; Remove clears it. A fourth file in a form with four upload questions is refused with the 3-file message. Network tab: no request to `upload_file`; the submit payload value is `name,data:<mime>;base64,...`.
Answers screen (`/form-builder/manage/<id>/submissions`, signed in):
10. Table has Date, Status, then one column per question (labels as the builder wrote them); empty answers blank; checkbox shows Yes/No; file column shows names only. Scrolls sideways on a phone inside the table, not the page.
11. "Download CSV" saves a `.csv` file with the same columns; with an expired session or no permission a red toast appears and the page stays put.
12. Click a row: drawer opens with reference, date, status, every question with its full answer (long text wraps), files as names with the note "open it from the CRM lead". Empty answers say "No answer".
13. Empty form: "No answers yet" empty state.
Builder header: the logo now is the academy logo image (check it is not oversized next to the title).

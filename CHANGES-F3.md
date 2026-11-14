# CHANGES-F3 (builder screens, Forms Pro fork)

Track F3, 2026-11-14. Contract C6 and SCREEN-LIST-DRAFT sections 1 and 2. Paths relative to `app/`.

## Files changed
| File | What and why |
|---|---|
| `forms_pro/forms_pro/doctype/form_field/form_field.json` | `Single Choice` added to the Fieldtype options (after Multiselect). Needs `bench migrate` on a live site. |
| `forms_pro/forms_pro/doctype/form_field/form_field.py` | `Single Choice` in the auto-generated `DF.Literal` and `FORM_TO_FRAPPE_FIELDTYPE` (`{"fieldtype": "Select"}`), so `to_frappe_field` gives a Frappe Select with the same options. |
| `frontend/src/types/FormsPro/form_field.types.ts` | `Fieldtype.SINGLE_CHOICE = "Single Choice"`. |
| `frontend/src/config/fieldTypes.ts` | Registry entry for Single Choice (radio component, Select mapping, reuses the Multiselect "Add Option" builder extra). New `PALETTE_ORDER` (the 10 types plus Section heading, with plain names) and `getPaletteLabel()`. Registry otherwise intact. |
| `frontend/src/components/builder/fields/SingleChoice.vue` (new) | Radio-button renderer, used by the builder canvas and the public form (both go through the registry and `RenderField.vue`). Reads choices from `field.options` itself, so `utils/selectOptions.ts` (not mine) did not need a change. Edit mode shows an x per choice like Multiselect. |
| `frontend/src/components/builder/sidebar/AddFieldsSection.vue` | Palette is "Add a question": only the 10 types plus Section heading, in order, via `PALETTE_ORDER`; Password, Link, Table, Date Time, Date Range, Time Picker, Text Editor, Switch, Checkbox, Rating, Heading 1 and 3 (and Page Break) in `HIDDEN_FROM_SIDEBAR`. Section heading = Heading 2. |
| `frontend/src/components/builder/SectionNavBar.vue` | "Add Step" renamed "Add page" (label, aria-label, tooltip). |
| `frontend/src/components/builder/field-editor/FieldPropertiesForm.vue` | Panel shows Question text, Required, Choices (Dropdown, Single choice, Multiple choice only), Help text, folded "Show only if...". Fieldname, Fieldtype, Hidden, Default Value removed. Headings and page breaks show only their text. Shows the plain type name under the title. |
| `frontend/src/components/builder/field-editor/ConditionalLogicSection.vue` | Rewritten as "Show only if...": folded; pick an earlier question, a condition, then an answer from that question's choices (typed text for non-choice questions). The rule is stored on the question being edited (`target_field` = its own fieldname, action Show Field). One rule, one condition per question. Old-style rules that point at a different question are shown as a read-only note and kept. |
| `frontend/src/components/builder/field-editor/fieldnames.ts` (new) | `ensureFieldname()`: fieldnames are still generated from the label, but early and unique for the questions a rule refers to (a rule needs a fieldname before the first save). Never changes after set. |
| `frontend/src/utils/conditionals.ts` | C6 rule in `shouldFieldBeVisible`: the target of a Show Field rule is hidden until its conditions are met, even without Hidden; a Hide Field target stays visible until met. Also: Multiple choice answers (arrays) compare by exact membership (before, `"Art"` matched `"Artisan"` through the joined string). New helpers `getChoices`, `isChoiceFieldtype`, `getEarlierQuestions`. |
| `frontend/src/utils/conditionals.test.ts` (new) | 15 vitest cases. |
| `frontend/src/router.ts` | `/form-builder/team` route kept but redirects to the form list (`Dashboard`); unused `teamForManageResource` removed. |
| `frontend/src/pages/home/sidebarItems.ts` | Team entry removed; "All Forms" renamed "My forms". |
| `frontend/src/layouts/BaseLayout.vue` | Team switcher removed (plain "Form builder" title in its place). |
| `frontend/src/pages/home/Dashboard.vue` | Single "New form" button (no "Create from existing DocType" menu); titles "My forms". |
| `frontend/src/components/FormBuilderHeader.vue` | Link icon is now a "Copy link" button that copies `${origin}/f/${route}` (path built from the router record, so it follows router.ts), shows "Copied" for 2 s; has a textarea fallback for non-secure pages. NOTE: this file is in `components/`, not `components/builder/`; the task item (6) needs it, so I edited it. |

`EditForm.vue` was not changed (nothing needed).

## Tests and build (in `.build-F3`, laptop node v24.22.1, yarn 1.22.22 via npx)
- `yarn install --frozen-lockfile`: ok. (Yarn 4 on the laptop rewrites the v1 lockfile and fails `--frozen-lockfile`; use `npx yarn@1.22.22`.)
- `npx vitest run`: 4 files, 46 tests pass (15 are new).
- New tests on the OLD `conditionals.ts` (scratch copy, old code): 9 failed, 6 passed. Failing: Show Field target hidden without Hidden (2), unmet target dropped by `getVisibleFields`, "disappears again", rule stored on another question, array exact match, empty array, three helper tests (functions did not exist). Saved list: `.build-F3/old-code-test-result.txt`.
- `yarn build`: succeeds. `vue-tsc --noEmit`: 0 errors under `src/`.
- Build quirk: `src/socket.ts` imports `../../../../sites/common_site_config.json`, which only resolves inside a bench. So the scratch copy lives at `.build-F3/bench/apps/forms_pro/frontend` with a stub `.build-F3/bench/sites/common_site_config.json`; `.build-F3/frontend` is a symlink to it. Differences app vs scratch: only `src/assets/Logo.vue` (F4 changed it in `app/` after my copy) and the generated `components.d.ts`.

## Not proven / needs the main agent
- Nothing was run in a browser. Python side only syntax-checked (no Frappe here); `bench migrate` for the new Select option not run.
- The backend rule (F2, endpoints.py) must treat a rule stored on the target field the same way: it scans every field's `conditional_logic` for `target_field == this field`, as the frontend does. Also arrays: F2 should compare Multiple choice answers by membership.

## Things outside my files that the main agent / other tracks should know
1. `components/FormBuilderSidebar.vue` (not mine) still has tabs titled "Settings", "Add Fields" and "DocType Fields". The DocType Fields tab imports Frappe DocType fields (including Link, Password, Table); the screen list says builders see none of that. Hide it there.
2. `stores/editForm.ts` (not mine): new sections are labelled `Step N` (`labelFallback`), and the duplicate-fieldname dialog says "set a unique fieldname", which builders cannot do now (two questions with the same text). Suggest rewording to "give these questions different text".
3. `utils/selectOptions.ts` does not split options for Single Choice; harmless because SingleChoice.vue reads `field.options` itself. The public renderer needs no change: `FormRenderer.vue` renders through `RenderField.vue` and the registry.
4. Home list (screen list section 1): title, Draft/Published, date are shown by `components/dashboard/FormPreviewCard.vue` (not mine). Missing there: number of answers and a Copy link per form (answers count needs a backend value).

## Browser checklist (builder, `/form-builder/edit-form/<id>`)
Screens and states to look at, with a new draft form:
1. Left list "Add a question": exactly 11 entries in order: Short answer, Paragraph, Dropdown, Single choice, Multiple choice, Number, Email, Phone, Date, File upload, Section heading. Search box filters by those names. No Password, Link, Table, Date Time, Date Range, Time, Text Editor, Switch, Checkbox, Rating, Heading 1/3.
2. Top of the canvas: button reads "Add page" (also after a page is added: the row of page tabs ends with "Add page").
3. Add a Single choice question: canvas shows round radio buttons; with no choices it says "No choices yet"; "Add Option" below adds choices; the x on a choice removes it. Add a Dropdown and a Multiple choice question too.
4. Click a question, right panel: only "Edit question" with the type name, Question text, Required, Choices (only on Dropdown, Single choice, Multiple choice, one per line), Help text, and a folded "Show only if...". No Fieldname, Fieldtype, Hidden, Default Value. Click a Section heading: only "Heading text".
5. "Show only if..." on the 2nd or later question: first question: shows "Add a question above this one first". With an earlier Single choice question that has choices: open the fold, pick that question, the Answer menu lists its choices (no typing); pick Is Not and back. With an earlier Short answer question: Answer is a text box. "Remove this rule" clears it; collapsed fold shows "(set)" when a rule exists. Save, reload, check the rule persists and the Fieldname was generated.
6. Preview / public form `/f/<route>` (published): the question with a rule is hidden at first, appears when the chosen choice is picked, hides again when another choice is picked. A non-matching required question must not block submit.
7. Sidebar (left, home): only "My forms"; no Team entry, no team switcher at the top (plain "Form builder"). Open `/form-builder/team` by hand: lands on the form list.
8. Home screen: one "New form" button, no dropdown.
9. Builder header: a "Copy link" button (not the old external-link icon, and no bare `/route` text). Click: label becomes "Copied" for about 2 s; paste somewhere and confirm the text is `https://<site>/f/<route>`. Also check on plain http (fallback path) and with a route that has a slash.
10. Public form with a Single choice question: radio group works on a phone-width window; the chosen text is what lands in the answer.

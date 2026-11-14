# Route changes (track F1)

Upstream: builder `/forms`, public form `/forms/p/<route>`.
Fork: builder `/form-builder`, public form `/f/<route>`.
Router base is now `/` (was `/forms`), so every route path carries its own prefix.
Asset base `/assets/forms_pro/frontend/` is unchanged. Paths are relative to `app/`.

| File | Old | New |
|---|---|---|
| forms_pro/hooks.py (apps screen) | `"route": "/forms"` | `"route": "/form-builder"` |
| forms_pro/hooks.py (website_route_rules) | `/forms/<path:app_path>` -> `forms` | `/form-builder/<path:app_path>` -> `form-builder`, and `/f/<path:app_path>` -> `form-builder` |
| forms_pro/www/forms.py | file name `forms.py` | renamed `form-builder.py` (so `/forms` no longer serves the app) |
| frontend/package.json `copy-html-entry` | `../forms_pro/www/forms.html` | `../forms_pro/www/form-builder.html` |
| .gitignore | `/forms_pro/www/forms.html` | `/forms_pro/www/form-builder.html` |
| forms_pro/api/team/endpoints.py:157 | `location = "/forms"` | `"/form-builder"` |
| forms_pro/overrides/invitations.py:13,32,34 | `/forms` | `/form-builder` |
| frontend/src/router.ts | `createWebHistory("/forms")` | `createWebHistory("/")` |
| frontend/src/router.ts | `path: "/"` (Home) | `/form-builder` (children `""`, `team` unchanged) |
| frontend/src/router.ts | `/manage/:id` | `/form-builder/manage/:id` |
| frontend/src/router.ts | `/edit-form/:id` | `/form-builder/edit-form/:id` |
| frontend/src/router.ts | `/p/:route(.*)` | `/f/:route(.*)` |
| frontend/src/router.ts | `/p/:route(.*)/edit/:submissionName` | `/f/:route(.*)/edit/:submissionName` |
| frontend/src/router.ts:95,127 | `redirect-to=/forms${to.fullPath}` | `redirect-to=${to.fullPath}` (fullPath is now absolute) |
| frontend/src/data/session.ts | logout `redirect-to=/forms`; login `router.replace(... \|\| "/")` | `/form-builder` for both |
| frontend/src/pages/manage/sidebarItems.ts | `router.replace("/")`, `/manage/<id>/overview`, `/manage/<id>/submissions` | `/form-builder`, `/form-builder/manage/...` |
| frontend/src/pages/manage/submissions/Submissions.vue, overview/Overview.vue | breadcrumb `/manage/<id>/overview` | `/form-builder/manage/<id>/overview` |
| frontend/src/components/RouteError.vue | `router.replace('/')` | `'/form-builder'` |
| frontend/src/components/submission/PreviousSubmissionSection.vue | `/p/<route>/edit/<name>` | `/f/<route>/edit/<name>` |
| frontend/src/pages/submission/PublicEdit.vue | `/p/<route>` | `/f/<route>` |
| frontend/src/pages/home/sidebarItems.ts | `/`, `/team` (to and isActive) | `/form-builder`, `/form-builder/team` |
| forms_pro/api/team/test_invitations.py, forms_pro/tests/factories/user_invitation_factory.py | `"/forms"` | `"/form-builder"` |
| frontend/e2e/helpers/{team,form-builder,dashboard,submission}.ts, specs/{route-perms,smoke,submission-steps,submission-view}.spec.ts | `/forms`, `/forms/team`, `/forms/manage/..`, `/forms/edit-form/..`, `/forms/p/..` | `/form-builder...`, `/f/...` |
| CLAUDE.md (upstream dev notes) | `/forms` text | updated wording |

Not changed: `frontend/src/components/submission/PageHeader.vue` (`redirect-to=${route.fullPath}`; correct with base `/`).
`FormBuilderHeader.vue` builds the public link from the route record, so it now yields `/f/<route>` with no edit.


## Correction 2026-11-14 (main agent): the www page's Python file must be named with an underscore
Frappe turns hyphens into underscores when it looks for a page's Python module (`frappe/website/page_renderers/template_page.py`, `set_pymodule`). `www/form-builder.html` therefore needs `www/form_builder.py`; the first rename to `form-builder.py` was never loaded, `get_context` did not run, and Frappe's DebugUndefined printed `{{ csrf_token }}` as literal text. Website Users still worked (their sessions have no stored CSRF token to check), but staff users (System User) got CSRFTokenError and a redirect loop between `/form-builder` and the login page. Found on staging with a throwaway user holding the shared login's role set.

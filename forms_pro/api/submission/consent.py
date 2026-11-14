"""Fixed consent wording for every public form in this fork (contract C1).

The wording is NOT editable by form builders: the public form API returns these
two constants and the visitor page renders one consent checkbox from them.

Source (copied word for word, 2026-11-14): the academy's existing enquiry Web Form
setup (CONSENT_LABEL, CONSENT_TEXT); the label stays under 140 characters because
that was the Frappe Web Form field-label limit. Another client's deployment edits
these two constants (or reads them from site config) and nothing else.
"""

CONSENT_LABEL = (
    "I agree to be contacted by Transparent Academy about courses and admissions (phone, WhatsApp, email)."
)

CONSENT_TEXT = (
    "I agree that Transparent Academy may contact me and my parent/guardian by phone, WhatsApp and email about "
    "courses and admissions, and store the details I have entered here."
)

CONSENT_REFUSAL_MESSAGE = "Please tick the consent box so that we may contact you."


def is_consent_given(consent) -> bool:
    """True only for a real tick: 1, True, "1", "true", "yes" (anything else, including 0, "0", "", None, is no)."""
    if isinstance(consent, str):
        return consent.strip().lower() in ("1", "true", "yes", "on")
    return bool(consent)

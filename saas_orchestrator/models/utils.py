"""Helpers shared by saas_orchestrator models.

Slug sanitization rules MUST stay aligned with the orchestrator API
validation regex defined in `orchestrator/app/models/instance.py` and
documented in `orchestrator/API_REFERENCE.md` section 3.

If the API regex changes, update `sanitize_slug()` and its tests.
"""
import re
import unicodedata

# Mirror of the orchestrator API regex (instance_id, tenant_id, plan_id)
SLUG_REGEX = re.compile(r'^[a-z0-9][a-z0-9-]*[a-z0-9]$')
SLUG_MIN_LENGTH = 3
SLUG_MAX_LENGTH = 63


def sanitize_slug(text, fallback='item'):
    """Convert arbitrary text into a slug accepted by the orchestrator API.

    Rules enforced:
    - lowercase ASCII letters, digits, hyphen only
    - must start and end with [a-z0-9]
    - no consecutive hyphens
    - length 3-63

    :param text: source text (may contain accents, spaces, special chars, etc.)
    :param fallback: value used if the result would be empty or shorter than min length
    :return: sanitized slug guaranteed to match the API regex
    """
    if not text:
        text = fallback
    # Normalize accents (NFKD) and drop combining marks
    normalized = unicodedata.normalize('NFKD', str(text))
    ascii_text = normalized.encode('ascii', 'ignore').decode('ascii')
    # Lowercase
    ascii_text = ascii_text.lower()
    # Replace any run of non-allowed chars with a single hyphen
    slug = re.sub(r'[^a-z0-9]+', '-', ascii_text)
    # Strip leading/trailing hyphens
    slug = slug.strip('-')
    # Pad to min length if too short (use fallback)
    if len(slug) < SLUG_MIN_LENGTH:
        slug = (slug + '-' + fallback).strip('-')
        if len(slug) < SLUG_MIN_LENGTH:
            slug = fallback
    # Trim to max length, then strip trailing hyphen if any
    if len(slug) > SLUG_MAX_LENGTH:
        slug = slug[:SLUG_MAX_LENGTH].rstrip('-')
    return slug


def build_instance_name(partner_name, blueprint_name, order_id):
    """Build a valid instance_id from order/partner/blueprint data.

    Format: `{partner_slug}-{blueprint_slug}-{order_id}`, capped at 63 chars.
    Guarantees the result matches the orchestrator API regex.
    """
    partner_slug = sanitize_slug(partner_name, fallback='customer')
    blueprint_slug = sanitize_slug(blueprint_name, fallback='product')
    suffix = f"-{blueprint_slug}-{order_id}"
    # Reserve room for the suffix so we don't blow past 63 chars
    max_partner = SLUG_MAX_LENGTH - len(suffix)
    if max_partner < SLUG_MIN_LENGTH:
        # Suffix alone is too long; degrade gracefully
        partner_slug = ''
    else:
        partner_slug = partner_slug[:max_partner].rstrip('-')
    candidate = f"{partner_slug}{suffix}".lstrip('-')
    # Final safety: re-sanitize to collapse any double hyphens introduced by truncation
    return sanitize_slug(candidate, fallback=f"instance-{order_id}")

"""Token helpers — generate random single-use tokens, store only their hashes."""

import hashlib
import secrets


def generate_token():
    """Return a URL-safe random token (plaintext is given to the user once)."""
    return secrets.token_urlsafe(32)


def hash_token(token):
    """SHA-256 hash of the token — what we persist in the database."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()

"""Validate that an email address is well-formed AND that its domain
can actually receive email (MX or A record).

Two layers:

1. Format check (regex + obvious-typo TLD blocklist).
2. DNS check: resolve MX, fall back to A (RFC 5321 §5).

If DNS is unreachable (timeout, server error), we accept the address
to avoid blocking signup on a transient DNS issue. The format check
still catches the everyday typos like .cim/.con/.cmo.
"""
from __future__ import annotations

import asyncio
import logging
import re
from dataclasses import dataclass

import dns.exception
import dns.resolver

logger = logging.getLogger(__name__)


# RFC-ish email regex. Not perfect (RFC 5322 is a mess) but rejects the
# common garbage: spaces, missing @, double @, trailing dots, etc.
_EMAIL_RE = re.compile(
    r"^[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,24}$"
)


# TLDs that are almost always typos of .com / .net / .org. We block them
# at the format stage so we don't even waste a DNS lookup, and so the
# user gets a precise error message.
_TYPO_TLDS = {
    "cim", "con", "cmo", "cpm", "coom", "comm", "om",
    "nett", "ne", "ent",
    "ogr", "rg", "orgg",
    "fr.", "fra", "frr",
}


@dataclass
class EmailValidationResult:
    is_valid: bool
    reason: str | None = None  # None on success
    domain: str | None = None


def _dns_resolve_sync(domain: str, timeout: float) -> bool:
    """Run the actual DNS query synchronously. Wrapped by the async API.

    Returns True if the domain has an MX or A record (i.e. can receive mail
    or at least exists). Returns False if NXDOMAIN or empty answer.
    Raises on timeout / server-fail so the caller can decide policy.
    """
    resolver = dns.resolver.Resolver()
    resolver.lifetime = timeout
    resolver.timeout = timeout

    try:
        answers = resolver.resolve(domain, "MX")
        if len(answers) > 0:
            return True
    except dns.resolver.NoAnswer:
        # No MX. Fall through to A record check (RFC 5321 §5).
        pass
    except dns.resolver.NXDOMAIN:
        return False

    try:
        answers = resolver.resolve(domain, "A")
        return len(answers) > 0
    except (dns.resolver.NoAnswer, dns.resolver.NXDOMAIN):
        return False


async def _dns_resolve(domain: str, timeout: float = 3.0) -> bool | None:
    """Async wrapper around the blocking DNS lookup.

    Returns True/False if we got a definitive answer, None if DNS failed
    transiently — caller treats None as 'accept, do not block signup'.
    """
    loop = asyncio.get_running_loop()
    try:
        return await loop.run_in_executor(
            None, _dns_resolve_sync, domain, timeout
        )
    except (dns.exception.Timeout, dns.resolver.NoNameservers, dns.resolver.LifetimeTimeout):
        logger.warning(f"DNS check timed out for {domain}, accepting by default")
        return None
    except Exception as e:
        logger.warning(f"DNS check failed for {domain} ({e}), accepting by default")
        return None


async def validate_email_address(email: str, *, check_dns: bool = True) -> EmailValidationResult:
    """Validate an email address. Returns an EmailValidationResult.

    Set check_dns=False in tests / scripts where DNS is unwanted.
    """
    email = (email or "").strip().lower()

    if not email:
        return EmailValidationResult(False, "empty")

    if not _EMAIL_RE.match(email):
        return EmailValidationResult(False, "format")

    domain = email.rsplit("@", 1)[1]
    tld = domain.rsplit(".", 1)[-1]

    if tld in _TYPO_TLDS:
        return EmailValidationResult(False, "typo_tld", domain=domain)

    if not check_dns:
        return EmailValidationResult(True, domain=domain)

    resolves = await _dns_resolve(domain)
    if resolves is False:
        return EmailValidationResult(False, "no_mx", domain=domain)

    # True or None (transient DNS failure) → accept.
    return EmailValidationResult(True, domain=domain)

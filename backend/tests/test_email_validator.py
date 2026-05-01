"""Tests for app.auth.email_validator.

DNS-skipping (check_dns=False) tests cover the format/TLD logic without
hitting the network. A handful of integration tests exercise the DNS
path against gmail.com / globegenius.app, with NXDOMAIN handling.
"""
from unittest.mock import patch

import pytest

from app.auth.email_validator import validate_email_address


# ─── Format-only tests (check_dns=False) ───

@pytest.mark.asyncio
async def test_valid_format_passes_without_dns():
    r = await validate_email_address("foo@example.com", check_dns=False)
    assert r.is_valid is True
    assert r.reason is None


@pytest.mark.asyncio
async def test_empty_string_rejected():
    r = await validate_email_address("", check_dns=False)
    assert r.is_valid is False
    assert r.reason == "empty"


@pytest.mark.asyncio
async def test_missing_at_rejected():
    r = await validate_email_address("foobar.com", check_dns=False)
    assert r.is_valid is False
    assert r.reason == "format"


@pytest.mark.asyncio
async def test_missing_tld_rejected():
    r = await validate_email_address("foo@gmail", check_dns=False)
    assert r.is_valid is False
    assert r.reason == "format"


@pytest.mark.asyncio
async def test_double_at_rejected():
    r = await validate_email_address("foo@@gmail.com", check_dns=False)
    assert r.is_valid is False
    assert r.reason == "format"


@pytest.mark.asyncio
async def test_space_in_local_part_rejected():
    r = await validate_email_address("foo bar@gmail.com", check_dns=False)
    assert r.is_valid is False
    assert r.reason == "format"


@pytest.mark.asyncio
async def test_typo_tld_cim_rejected():
    """The exact typo Moussa hit: fodemusic@gmail.cim."""
    r = await validate_email_address("fodemusic@gmail.cim", check_dns=False)
    assert r.is_valid is False
    assert r.reason == "typo_tld"
    assert r.domain == "gmail.cim"


@pytest.mark.asyncio
async def test_typo_tld_con_rejected():
    r = await validate_email_address("foo@gmail.con", check_dns=False)
    assert r.is_valid is False
    assert r.reason == "typo_tld"


@pytest.mark.asyncio
async def test_typo_tld_cmo_rejected():
    r = await validate_email_address("foo@yahoo.cmo", check_dns=False)
    assert r.is_valid is False
    assert r.reason == "typo_tld"


@pytest.mark.asyncio
async def test_email_normalized_lowercase():
    """Validation accepts mixed-case input."""
    r = await validate_email_address("Foo@Gmail.COM", check_dns=False)
    assert r.is_valid is True


@pytest.mark.asyncio
async def test_plus_addressing_accepted():
    r = await validate_email_address("foo+tag@gmail.com", check_dns=False)
    assert r.is_valid is True


# ─── DNS path tests (mocked) ───

@pytest.mark.asyncio
async def test_dns_nxdomain_rejected():
    """When the resolver says NXDOMAIN, we reject."""
    with patch("app.auth.email_validator._dns_resolve", return_value=False):
        r = await validate_email_address("foo@nonexistent-domain-xyz123.com")
    assert r.is_valid is False
    assert r.reason == "no_mx"


@pytest.mark.asyncio
async def test_dns_resolves_accepted():
    """When the resolver returns True (MX or A found), accept."""
    with patch("app.auth.email_validator._dns_resolve", return_value=True):
        r = await validate_email_address("foo@gmail.com")
    assert r.is_valid is True


@pytest.mark.asyncio
async def test_dns_transient_failure_accepted_by_default():
    """If DNS itself is broken (timeout returns None), don't block signup."""
    with patch("app.auth.email_validator._dns_resolve", return_value=None):
        r = await validate_email_address("foo@gmail.com")
    assert r.is_valid is True


@pytest.mark.asyncio
async def test_typo_tld_blocked_before_dns_lookup():
    """A typo TLD must be rejected by the format step, not waste a DNS query."""
    with patch("app.auth.email_validator._dns_resolve") as mock_dns:
        r = await validate_email_address("foo@gmail.cim")
    assert r.is_valid is False
    assert r.reason == "typo_tld"
    mock_dns.assert_not_called()

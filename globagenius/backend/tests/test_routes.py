from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_status():
    with patch("app.api.routes.db") as mock_db:
        mock_db.table.return_value.select.return_value.order.return_value.limit.return_value.execute.return_value = MagicMock(data=[])
        mock_db.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(data=[], count=0)

        response = client.get("/api/status")
        assert response.status_code == 200


def _fake_qi_free():
    return [{
        "id": "qi-1",
        "item_id": "flight-1",
        "tier": "free",
        "price": 150.0,
        "baseline_price": 220.0,
        "discount_pct": 31.8,
        "score": 48,
        "created_at": "2026-04-14T08:00:00+00:00",
    }]


def _fake_qi_premium():
    return [{
        "id": "qi-2",
        "item_id": "flight-2",
        "tier": "premium",
        "price": 90.0,
        "baseline_price": 180.0,
        "discount_pct": 50.0,
        "score": 59,
        "created_at": "2026-04-14T08:00:00+00:00",
    }]


def _fake_flights_free():
    return [{
        "id": "flight-1",
        "origin": "CDG",
        "destination": "BCN",
        "departure_date": "2026-05-12",
        "return_date": "2026-05-17",
        "airline": "VY",
        "stops": 0,
        "source_url": "https://www.aviasales.com/search/CDG1205BCN17051",
        "trip_duration_days": 5,
        "duration_minutes": 105,
    }]


def _fake_flights_premium():
    return [{
        "id": "flight-2",
        "origin": "CDG",
        "destination": "TUN",
        "departure_date": "2026-06-01",
        "return_date": "2026-06-08",
        "airline": "AF",
        "stops": 0,
        "source_url": "https://www.aviasales.com/search/...",
        "trip_duration_days": 7,
        "duration_minutes": 150,
    }]


def _patch_db_for_packages(qi_data, rf_data):
    """Build a db mock matching the /api/packages query chain."""
    qi_table = MagicMock()
    # Anonymous + plan=free has the longest chain (lt at the end)
    qi_table.select.return_value.eq.return_value.eq.return_value.gte.return_value.gte.return_value.lt.return_value.order.return_value.limit.return_value.execute.return_value = MagicMock(data=qi_data)
    # Premium plan has gte instead of lt at the end
    qi_table.select.return_value.eq.return_value.eq.return_value.gte.return_value.gte.return_value.order.return_value.limit.return_value.execute.return_value = MagicMock(data=qi_data)

    rf_table = MagicMock()
    rf_table.select.return_value.in_.return_value.execute.return_value = MagicMock(data=rf_data)

    return lambda name: {
        "qualified_items": qi_table,
        "raw_flights": rf_table,
    }[name]


def test_packages_list_free_anonymous_locks_sensitive_fields():
    """Anonymous caller (no JWT) gets visible route info but locked
    price/baseline_price/source_url, regardless of tier."""
    with patch("app.api.routes.db") as mock_db:
        mock_db.table.side_effect = _patch_db_for_packages(_fake_qi_free(), _fake_flights_free())
        response = client.get("/api/packages?plan=free")
        assert response.status_code == 200
        body = response.json()
        assert body["plan"] == "free"
        assert len(body["items"]) == 1
        item = body["items"][0]
        # Always visible
        assert item["origin"] == "CDG"
        assert item["destination"] == "BCN"
        assert item["airline"] == "VY"
        assert item["tier"] == "free"
        assert item["discount_pct"] == 31.8
        # Sensitive — locked for anonymous
        assert item["price"] is None
        assert item["baseline_price"] is None
        assert item["source_url"] is None
        assert item["locked"] is True


def test_packages_list_free_authenticated_unlocks_free_tier():
    """A logged-in non-premium user sees free deals fully unlocked."""
    from app.api import routes as routes_module
    fake_user = {"user_id": "user-1", "email": "test@example.com"}

    async def fake_optional_user():
        return fake_user

    # Patch _is_premium_user to return False (not premium)
    with patch("app.api.routes.db") as mock_db, \
         patch("app.api.routes._is_premium_user", return_value=False):
        mock_db.table.side_effect = _patch_db_for_packages(_fake_qi_free(), _fake_flights_free())
        # Override the dependency
        from app.main import app
        app.dependency_overrides[routes_module.get_optional_user] = fake_optional_user
        try:
            response = client.get("/api/packages?plan=free")
        finally:
            app.dependency_overrides.clear()

        assert response.status_code == 200
        item = response.json()["items"][0]
        assert item["price"] == 150.0
        assert item["baseline_price"] == 220.0
        assert item["source_url"].startswith("https://www.aviasales.com")
        assert item["locked"] is False


def test_packages_list_premium_authenticated_non_premium_locked():
    """A logged-in non-premium user sees premium deals LOCKED."""
    from app.api import routes as routes_module
    fake_user = {"user_id": "user-1", "email": "test@example.com"}

    async def fake_optional_user():
        return fake_user

    with patch("app.api.routes.db") as mock_db, \
         patch("app.api.routes._is_premium_user", return_value=False):
        mock_db.table.side_effect = _patch_db_for_packages(_fake_qi_premium(), _fake_flights_premium())
        from app.main import app
        app.dependency_overrides[routes_module.get_optional_user] = fake_optional_user
        try:
            response = client.get("/api/packages?plan=premium")
        finally:
            app.dependency_overrides.clear()

        assert response.status_code == 200
        item = response.json()["items"][0]
        assert item["origin"] == "CDG"
        assert item["destination"] == "TUN"
        assert item["tier"] == "premium"
        # Premium deal locked for non-premium user
        assert item["price"] is None
        assert item["baseline_price"] is None
        assert item["source_url"] is None
        assert item["locked"] is True


def test_packages_list_premium_user_unlocks_everything():
    """A premium user sees all deals fully unlocked, free and premium."""
    from app.api import routes as routes_module
    fake_user = {"user_id": "user-1", "email": "test@example.com"}

    async def fake_optional_user():
        return fake_user

    with patch("app.api.routes.db") as mock_db, \
         patch("app.api.routes._is_premium_user", return_value=True):
        mock_db.table.side_effect = _patch_db_for_packages(_fake_qi_premium(), _fake_flights_premium())
        from app.main import app
        app.dependency_overrides[routes_module.get_optional_user] = fake_optional_user
        try:
            response = client.get("/api/packages?plan=premium")
        finally:
            app.dependency_overrides.clear()

        assert response.status_code == 200
        item = response.json()["items"][0]
        assert item["price"] == 90.0
        assert item["baseline_price"] == 180.0
        assert item["source_url"] == "https://www.aviasales.com/search/..."
        assert item["locked"] is False


def test_packages_list_premium_same_enrichment_path():
    """plan=premium uses the same enrichment path with a gte 30 filter."""
    fake_qi = [{
        "id": "qi-2",
        "item_id": "flight-2",
        "tier": "premium",
        "price": 90.0,
        "baseline_price": 180.0,
        "discount_pct": 50.0,
        "score": 59,
        "created_at": "2026-04-14T08:00:00+00:00",
    }]
    fake_flights = [{
        "id": "flight-2",
        "origin": "CDG",
        "destination": "TUN",
        "departure_date": "2026-06-01",
        "return_date": "2026-06-08",
        "airline": "AF",
        "stops": 0,
        "source_url": "https://www.aviasales.com/search/...",
        "trip_duration_days": 7,
        "duration_minutes": 150,
    }]

    qi_table = MagicMock()
    qi_table.select.return_value.eq.return_value.eq.return_value.gte.return_value.gte.return_value.order.return_value.limit.return_value.execute.return_value = MagicMock(data=fake_qi)

    rf_table = MagicMock()
    rf_table.select.return_value.in_.return_value.execute.return_value = MagicMock(data=fake_flights)

    with patch("app.api.routes.db") as mock_db:
        mock_db.table.side_effect = lambda name: {
            "qualified_items": qi_table,
            "raw_flights": rf_table,
        }[name]
        response = client.get("/api/packages?plan=premium")
        assert response.status_code == 200
        body = response.json()
        assert body["plan"] == "premium"
        assert len(body["items"]) == 1
        assert body["items"][0]["tier"] == "premium"
        assert body["items"][0]["discount_pct"] == 50.0


def test_packages_list_empty_returns_no_items():
    qi_table = MagicMock()
    qi_table.select.return_value.eq.return_value.eq.return_value.gte.return_value.gte.return_value.lt.return_value.order.return_value.limit.return_value.execute.return_value = MagicMock(data=[])

    with patch("app.api.routes.db") as mock_db:
        mock_db.table.side_effect = lambda name: {"qualified_items": qi_table}[name]
        response = client.get("/api/packages?plan=free")
        assert response.status_code == 200
        assert response.json() == {"items": [], "plan": "free"}


def test_packages_detail_not_found():
    with patch("app.api.routes.db") as mock_db:
        mock_db.table.return_value.select.return_value.eq.return_value.execute.return_value = MagicMock(data=[])
        response = client.get("/api/packages/nonexistent-id")
        assert response.status_code == 404


# ─── Phase 2: min_discount validation & tier capping ───

def _patch_db_for_update_preferences(stored_min_discount: int):
    """Build a db mock matching the /api/users/{id}/preferences PUT chain."""
    prefs_table = MagicMock()

    def _update_side_effect(update_data):
        # Echo the update payload back so the route can return it
        update_chain = MagicMock()
        update_chain.eq.return_value.execute.return_value = MagicMock(
            data=[{
                "user_id": "user-1",
                "airport_codes": update_data.get("airport_codes", []),
                "offer_types": update_data.get("offer_types", []),
                "min_discount": update_data.get("min_discount"),
                "max_budget": update_data.get("max_budget"),
                "preferred_destinations": update_data.get("preferred_destinations", []),
                "updated_at": update_data.get("updated_at"),
            }]
        )
        return update_chain

    prefs_table.update.side_effect = _update_side_effect
    return lambda name: {"user_preferences": prefs_table}[name]


def _auth_override():
    from app.api import routes as routes_module
    from app.main import app

    async def fake_current_user():
        return {"user_id": "user-1", "sub": "user-1", "email": "test@example.com"}

    app.dependency_overrides[routes_module.get_current_user] = fake_current_user


def _clear_overrides():
    from app.main import app
    app.dependency_overrides.clear()


def test_update_preferences_min_discount_valid_palette():
    """Premium user: all values in {20,30,40,50,60} accepted, stored as-is, capped=False."""
    _auth_override()
    try:
        for value in (20, 30, 40, 50, 60):
            with patch("app.api.routes.db") as mock_db, \
                 patch("app.api.routes._get_user_tier", return_value="premium"):
                mock_db.table.side_effect = _patch_db_for_update_preferences(value)
                response = client.put(
                    "/api/users/user-1/preferences",
                    json={
                        "airport_codes": ["CDG"],
                        "offer_types": ["flight"],
                        "min_discount": value,
                    },
                )
                assert response.status_code == 200, f"value={value} body={response.text}"
                body = response.json()
                assert body["min_discount"] == value, f"value={value}: got {body['min_discount']}"
                # capped should be False (or absent)
                assert body.get("capped", False) is False, f"value={value}: capped={body.get('capped')}"
    finally:
        _clear_overrides()


def test_update_preferences_min_discount_invalid_value():
    """min_discount=25 is not in the palette → Pydantic 422."""
    _auth_override()
    try:
        with patch("app.api.routes.db") as mock_db, \
             patch("app.api.routes._get_user_tier", return_value="premium"):
            mock_db.table.side_effect = _patch_db_for_update_preferences(25)
            response = client.put(
                "/api/users/user-1/preferences",
                json={
                    "airport_codes": ["CDG"],
                    "offer_types": ["flight"],
                    "min_discount": 25,
                },
            )
            assert response.status_code == 422, f"expected 422, got {response.status_code}: {response.text}"
    finally:
        _clear_overrides()


def test_update_preferences_min_discount_free_user_capped():
    """Free user with min_discount=50 should be capped to 29 and capped=True."""
    _auth_override()
    try:
        with patch("app.api.routes.db") as mock_db, \
             patch("app.api.routes._get_user_tier", return_value="free"):
            mock_db.table.side_effect = _patch_db_for_update_preferences(29)
            response = client.put(
                "/api/users/user-1/preferences",
                json={
                    "airport_codes": ["CDG"],
                    "offer_types": ["flight"],
                    "min_discount": 50,
                },
            )
            assert response.status_code == 200, response.text
            body = response.json()
            assert body["min_discount"] == 29, f"expected stored 29, got {body['min_discount']}"
            assert body.get("capped") is True, f"expected capped=True, got {body.get('capped')}"
    finally:
        _clear_overrides()


def test_update_preferences_min_discount_premium_user_not_capped():
    """Premium user with min_discount=60 keeps 60 and capped=False."""
    _auth_override()
    try:
        with patch("app.api.routes.db") as mock_db, \
             patch("app.api.routes._get_user_tier", return_value="premium"):
            mock_db.table.side_effect = _patch_db_for_update_preferences(60)
            response = client.put(
                "/api/users/user-1/preferences",
                json={
                    "airport_codes": ["CDG"],
                    "offer_types": ["flight"],
                    "min_discount": 60,
                },
            )
            assert response.status_code == 200, response.text
            body = response.json()
            assert body["min_discount"] == 60
            assert body.get("capped", False) is False
    finally:
        _clear_overrides()


def test_list_packages_with_min_discount_param():
    """GET /api/packages?min_discount=40&plan=free must apply gte(40)
    even though plan=free would normally floor at 20."""
    fake_qi = [{
        "id": "qi-3",
        "item_id": "flight-3",
        "tier": "free",
        "price": 100.0,
        "baseline_price": 180.0,
        "discount_pct": 44.0,
        "score": 55,
        "created_at": "2026-04-14T08:00:00+00:00",
    }]
    fake_flights = [{
        "id": "flight-3",
        "origin": "CDG",
        "destination": "LIS",
        "departure_date": "2026-05-20",
        "return_date": "2026-05-25",
        "airline": "TP",
        "stops": 0,
        "source_url": "https://www.aviasales.com/search/CDG2005LIS25051",
        "trip_duration_days": 5,
        "duration_minutes": 150,
    }]

    # Track calls to gte on the qualified_items chain
    gte_calls = []

    qi_table = MagicMock()

    # Build a programmable chain that records gte() arguments
    class _Chain:
        def __init__(self, data):
            self._data = data

        def select(self, *a, **kw):
            return self

        def eq(self, *a, **kw):
            return self

        def gte(self, col, val):
            gte_calls.append((col, val))
            return self

        def lt(self, *a, **kw):
            return self

        def order(self, *a, **kw):
            return self

        def limit(self, *a, **kw):
            return self

        def execute(self):
            return MagicMock(data=self._data)

    qi_chain = _Chain(fake_qi)

    rf_table = MagicMock()
    rf_table.select.return_value.in_.return_value.execute.return_value = MagicMock(data=fake_flights)

    with patch("app.api.routes.db") as mock_db:
        def _table(name):
            if name == "qualified_items":
                return qi_chain
            if name == "raw_flights":
                return rf_table
            raise KeyError(name)

        mock_db.table.side_effect = _table
        response = client.get("/api/packages?plan=free&min_discount=40")
        assert response.status_code == 200, response.text
        # Must have applied gte(discount_pct, 40) — the larger of
        # (min_discount=40, plan_floor=20)
        discount_gte = [v for col, v in gte_calls if col == "discount_pct"]
        assert 40 in discount_gte, f"expected gte(discount_pct, 40), got gte calls: {gte_calls}"


# ---------- Phase D1 — _get_user_tier with premium_grants ----------

def _build_tier_db_mock(grants_data=None, prefs_data=None, grants_raises=False):
    """Build a db mock that routes .table() calls to different chains.
    grants_data: list of dicts returned by premium_grants select
    prefs_data: list of dicts returned by user_preferences select
    grants_raises: if True, premium_grants.execute() raises Exception
    """
    from unittest.mock import MagicMock
    db_mock = MagicMock()

    # premium_grants chain
    grants_table = MagicMock()
    if grants_raises:
        grants_table.select.return_value.eq.return_value.eq.return_value.limit.return_value.execute.side_effect = Exception("db fail")
    else:
        grants_table.select.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value = MagicMock(data=grants_data or [])

    # user_preferences chain
    prefs_table = MagicMock()
    prefs_table.select.return_value.eq.return_value.execute.return_value = MagicMock(data=prefs_data or [])

    def table_router(name):
        if name == "premium_grants":
            return grants_table
        elif name == "user_preferences":
            return prefs_table
        return MagicMock()

    db_mock.table.side_effect = table_router
    return db_mock


def test_get_user_tier_reads_active_grant_no_expiry():
    from app.api import routes
    from unittest.mock import patch
    db_mock = _build_tier_db_mock(grants_data=[{"expires_at": None, "revoked": False}])
    with patch.object(routes, "db", db_mock):
        assert routes._get_user_tier("u1") == "premium"


def test_get_user_tier_reads_grant_with_future_expiry():
    from app.api import routes
    from unittest.mock import patch
    db_mock = _build_tier_db_mock(grants_data=[{"expires_at": "2099-01-01T00:00:00+00:00", "revoked": False}])
    with patch.object(routes, "db", db_mock):
        assert routes._get_user_tier("u1") == "premium"


def test_get_user_tier_ignores_expired_grant_falls_back_free():
    from app.api import routes
    from unittest.mock import patch
    # Expired grant + no stripe customer → free
    db_mock = _build_tier_db_mock(
        grants_data=[{"expires_at": "2020-01-01T00:00:00+00:00", "revoked": False}],
        prefs_data=[{"stripe_customer_id": None}],
    )
    with patch.object(routes, "db", db_mock):
        assert routes._get_user_tier("u1") == "free"


def test_get_user_tier_ignores_revoked_grant_falls_back_free():
    from app.api import routes
    from unittest.mock import patch
    # The eq("revoked", False) filter excludes revoked rows so the mock returns [] for grants
    db_mock = _build_tier_db_mock(grants_data=[], prefs_data=[{"stripe_customer_id": None}])
    with patch.object(routes, "db", db_mock):
        assert routes._get_user_tier("u1") == "free"


def test_get_user_tier_fallback_stripe_customer_id():
    from app.api import routes
    from unittest.mock import patch
    db_mock = _build_tier_db_mock(
        grants_data=[],
        prefs_data=[{"stripe_customer_id": "cus_123"}],
    )
    with patch.object(routes, "db", db_mock):
        assert routes._get_user_tier("u1") == "premium"


# ---------- Phase D3 — Admin console API ----------

def test_admin_list_users_requires_key(monkeypatch):
    from fastapi.testclient import TestClient
    from app.main import app
    from app.api import routes
    monkeypatch.setattr(routes.settings, "ADMIN_API_KEY", "secret-key")
    client = TestClient(app)
    r = client.get("/api/admin/users")
    assert r.status_code == 403


def test_admin_list_users_returns_items_with_tier(monkeypatch):
    from unittest.mock import patch, MagicMock
    from fastapi.testclient import TestClient
    from app.main import app
    from app.api import routes
    monkeypatch.setattr(routes.settings, "ADMIN_API_KEY", "secret-key")
    monkeypatch.setattr(routes.settings, "ADMIN_EMAILS", ["admin@example.com"])

    users_table = MagicMock()
    users_table.select.return_value.limit.return_value.execute.return_value = MagicMock(
        data=[
            {"id": "u1", "email": "admin@example.com", "created_at": "2026-01-01T00:00:00Z"},
            {"id": "u2", "email": "bob@example.com", "created_at": "2026-02-01T00:00:00Z"},
        ]
    )
    prefs_table = MagicMock()
    prefs_table.select.return_value.in_.return_value.execute.return_value = MagicMock(
        data=[
            {"user_id": "u1", "min_discount": 20, "stripe_customer_id": None, "telegram_connected": True, "telegram_chat_id": 111},
            {"user_id": "u2", "min_discount": 30, "stripe_customer_id": "cus_123", "telegram_connected": False, "telegram_chat_id": None},
        ]
    )
    grants_table_list = MagicMock()
    grants_table_list.select.return_value.in_.return_value.eq.return_value.execute.return_value = MagicMock(data=[])
    # For _get_user_tier's own queries (one per user)
    grants_table_tier = MagicMock()
    grants_table_tier.select.return_value.eq.return_value.eq.return_value.limit.return_value.execute.return_value = MagicMock(data=[])
    prefs_table_tier = MagicMock()
    prefs_table_tier.select.return_value.eq.return_value.execute.return_value = MagicMock(data=[{"stripe_customer_id": None}])

    call_count = {"premium_grants": 0, "user_preferences": 0}

    def table_router(name):
        if name == "users":
            return users_table
        elif name == "premium_grants":
            call_count["premium_grants"] += 1
            # First call = list bulk fetch; subsequent = _get_user_tier individual fetches
            if call_count["premium_grants"] == 1:
                return grants_table_list
            return grants_table_tier
        elif name == "user_preferences":
            call_count["user_preferences"] += 1
            if call_count["user_preferences"] == 1:
                return prefs_table
            return prefs_table_tier
        return MagicMock()

    db_mock = MagicMock()
    db_mock.table.side_effect = table_router

    with patch.object(routes, "db", db_mock):
        client = TestClient(app)
        r = client.get("/api/admin/users", headers={"X-Admin-Key": "secret-key"})
    assert r.status_code == 200
    body = r.json()
    assert body["count"] == 2
    emails = {it["email"] for it in body["items"]}
    assert emails == {"admin@example.com", "bob@example.com"}
    admin_item = next(it for it in body["items"] if it["email"] == "admin@example.com")
    assert admin_item["is_admin"] is True
    bob_item = next(it for it in body["items"] if it["email"] == "bob@example.com")
    assert bob_item["is_admin"] is False


def test_admin_grant_premium_upserts_row(monkeypatch):
    from unittest.mock import patch, MagicMock
    from fastapi.testclient import TestClient
    from app.main import app
    from app.api import routes
    monkeypatch.setattr(routes.settings, "ADMIN_API_KEY", "secret-key")

    upsert_spy = MagicMock(return_value=MagicMock(execute=MagicMock(return_value=MagicMock(data=[{"user_id": "u1", "revoked": False}]))))
    grants_table = MagicMock()
    grants_table.upsert = upsert_spy

    db_mock = MagicMock()
    db_mock.table.return_value = grants_table

    with patch.object(routes, "db", db_mock):
        client = TestClient(app)
        r = client.put(
            "/api/admin/users/u1/premium",
            headers={"X-Admin-Key": "secret-key"},
            json={"reason": "beta tester"},
        )
    assert r.status_code == 200
    assert r.json()["ok"] is True
    # Verify upsert was called with the right row
    args, kwargs = upsert_spy.call_args
    row = args[0]
    assert row["user_id"] == "u1"
    assert row["revoked"] is False
    assert row["reason"] == "beta tester"
    assert kwargs.get("on_conflict") == "user_id"


def test_admin_grant_premium_with_expires_at(monkeypatch):
    from unittest.mock import patch, MagicMock
    from fastapi.testclient import TestClient
    from app.main import app
    from app.api import routes
    monkeypatch.setattr(routes.settings, "ADMIN_API_KEY", "secret-key")

    upsert_spy = MagicMock(return_value=MagicMock(execute=MagicMock(return_value=MagicMock(data=[]))))
    grants_table = MagicMock()
    grants_table.upsert = upsert_spy
    db_mock = MagicMock()
    db_mock.table.return_value = grants_table

    with patch.object(routes, "db", db_mock):
        client = TestClient(app)
        r = client.put(
            "/api/admin/users/u1/premium",
            headers={"X-Admin-Key": "secret-key"},
            json={"expires_at": "2027-01-01T00:00:00Z", "reason": "trial"},
        )
    assert r.status_code == 200
    row = upsert_spy.call_args[0][0]
    assert row["expires_at"] == "2027-01-01T00:00:00Z"


def test_admin_revoke_premium_sets_revoked_true(monkeypatch):
    from unittest.mock import patch, MagicMock
    from fastapi.testclient import TestClient
    from app.main import app
    from app.api import routes
    monkeypatch.setattr(routes.settings, "ADMIN_API_KEY", "secret-key")

    update_spy = MagicMock(return_value=MagicMock(eq=MagicMock(return_value=MagicMock(execute=MagicMock(return_value=MagicMock(data=[{"id": "g1"}]))))))
    grants_table = MagicMock()
    grants_table.update = update_spy
    db_mock = MagicMock()
    db_mock.table.return_value = grants_table

    with patch.object(routes, "db", db_mock):
        client = TestClient(app)
        r = client.delete("/api/admin/users/u1/premium", headers={"X-Admin-Key": "secret-key"})
    assert r.status_code == 200
    update_args = update_spy.call_args[0][0]
    assert update_args["revoked"] is True
    assert "revoked_at" in update_args


def test_admin_update_min_discount_bypasses_cap(monkeypatch):
    from unittest.mock import patch, MagicMock
    from fastapi.testclient import TestClient
    from app.main import app
    from app.api import routes
    monkeypatch.setattr(routes.settings, "ADMIN_API_KEY", "secret-key")

    update_spy = MagicMock(return_value=MagicMock(eq=MagicMock(return_value=MagicMock(execute=MagicMock(return_value=MagicMock(data=[{"user_id": "u1", "min_discount": 50}]))))))
    prefs_table = MagicMock()
    prefs_table.update = update_spy
    db_mock = MagicMock()
    db_mock.table.return_value = prefs_table

    with patch.object(routes, "db", db_mock):
        client = TestClient(app)
        r = client.put(
            "/api/admin/users/u1/min_discount",
            headers={"X-Admin-Key": "secret-key"},
            json={"value": 50},
        )
    assert r.status_code == 200
    assert r.json()["min_discount"] == 50
    update_spy.assert_called_with({"min_discount": 50})


def test_admin_reset_prefs_resets_to_defaults(monkeypatch):
    from unittest.mock import patch, MagicMock
    from fastapi.testclient import TestClient
    from app.main import app
    from app.api import routes
    monkeypatch.setattr(routes.settings, "ADMIN_API_KEY", "secret-key")

    update_spy = MagicMock(return_value=MagicMock(eq=MagicMock(return_value=MagicMock(execute=MagicMock(return_value=MagicMock(data=[{"user_id": "u1"}]))))))
    prefs_table = MagicMock()
    prefs_table.update = update_spy
    db_mock = MagicMock()
    db_mock.table.return_value = prefs_table

    with patch.object(routes, "db", db_mock):
        client = TestClient(app)
        r = client.post("/api/admin/users/u1/reset_prefs", headers={"X-Admin-Key": "secret-key"})
    assert r.status_code == 200
    update_args = update_spy.call_args[0][0]
    assert update_args["min_discount"] == 20
    assert update_args["airport_codes"] == ["CDG"]


# ---------- Phase D4 — Free tier strict <30% ----------

def test_update_preferences_free_cap_at_29():
    """Free user requesting min_discount=50 -> stored as 29, capped=True."""
    _auth_override()
    try:
        with patch("app.api.routes.db") as mock_db, \
             patch("app.api.routes._get_user_tier", return_value="free"):
            # Echo whatever the route sends
            captured = {}

            def _table(name):
                prefs_table = MagicMock()

                def _update_side_effect(update_data):
                    captured["update_data"] = update_data
                    update_chain = MagicMock()
                    update_chain.eq.return_value.execute.return_value = MagicMock(
                        data=[{
                            "user_id": "user-1",
                            "airport_codes": update_data.get("airport_codes", []),
                            "offer_types": update_data.get("offer_types", []),
                            "min_discount": update_data.get("min_discount"),
                            "max_budget": update_data.get("max_budget"),
                            "preferred_destinations": update_data.get("preferred_destinations", []),
                            "updated_at": update_data.get("updated_at"),
                        }]
                    )
                    return update_chain

                prefs_table.update.side_effect = _update_side_effect
                return prefs_table

            mock_db.table.side_effect = _table
            response = client.put(
                "/api/users/user-1/preferences",
                json={
                    "airport_codes": ["CDG"],
                    "offer_types": ["flight"],
                    "min_discount": 50,
                },
            )
            assert response.status_code == 200, response.text
            body = response.json()
            assert body.get("capped") is True
            assert captured["update_data"]["min_discount"] == 29
            assert body["min_discount"] == 29
    finally:
        _clear_overrides()


def test_list_packages_free_excludes_30_percent_offer():
    """Free plan returns only discount_pct in [20, 30)."""
    calls = {"gte": [], "lt": []}

    class _Chain:
        def select(self, *a, **kw):
            return self

        def eq(self, *a, **kw):
            return self

        def gte(self, col, val):
            calls["gte"].append((col, val))
            return self

        def lt(self, col, val):
            calls["lt"].append((col, val))
            return self

        def order(self, *a, **kw):
            return self

        def limit(self, *a, **kw):
            return self

        def execute(self):
            return MagicMock(data=[])

    qi_chain = _Chain()

    with patch("app.api.routes.db") as mock_db:
        def _table(name):
            if name == "qualified_items":
                return qi_chain
            raise KeyError(name)

        mock_db.table.side_effect = _table
        response = client.get("/api/packages?plan=free&limit=5")
    assert response.status_code == 200
    # Free plan applies gte(20) and lt(30) — the free band
    assert ("discount_pct", 20) in calls["gte"]
    assert ("discount_pct", 30) in calls["lt"]


def test_list_packages_premium_includes_30_percent_offer():
    """Premium plan floor is 30 (not 40)."""
    calls = {"gte": []}

    class _Chain:
        def select(self, *a, **kw):
            return self

        def eq(self, *a, **kw):
            return self

        def gte(self, col, val):
            calls["gte"].append((col, val))
            return self

        def lt(self, *a, **kw):
            return self

        def order(self, *a, **kw):
            return self

        def limit(self, *a, **kw):
            return self

        def execute(self):
            return MagicMock(data=[])

    qi_chain = _Chain()

    with patch("app.api.routes.db") as mock_db:
        def _table(name):
            if name == "qualified_items":
                return qi_chain
            raise KeyError(name)

        mock_db.table.side_effect = _table
        response = client.get("/api/packages?plan=premium&limit=5")
    assert response.status_code == 200
    # Premium plan gte(30)
    assert ("discount_pct", 30) in calls["gte"]

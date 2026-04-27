# Telegram Alert Message Format — Before & After

## Redesign Complete (Apr 22, 2026)
**Commits**: ddf3f48, c0e0d8c

---

## BEFORE (Old Format)

```
🟠 BARCELONA — 3 offres à saisir

✈️ Paris → Barcelona

📅 Juin 2026 (3)
🟠 01 juin - 06 juin · 5j · 15€ (-75%){airline}
👉 [Consulter le deal](long_booking_url)
🏨 Hôtels Barcelona : long_hotel_booking_url

🟠 05 juin - 10 juin · 5j · 45€ (-60%){airline}
👉 [Consulter le deal](long_booking_url)
🏨 Hôtels Barcelona : long_hotel_booking_url

📅 Juillet 2026 (1)
🟡 12 juil - 19 juil · 7j · 120€ (-25%){airline}
👉 [Consulter le deal](long_booking_url)

+ 3 autres

👉 Toutes les offres : https://globegenius.app/home?dest=BCN
```

### Issues Identified
❌ **Information Hierarchy** — Destination buried after "offres à saisir", not scannable
❌ **Pricing Visibility** — Price mixed into single line: `15€ (-75%){airline}`
❌ **CTA Clarity** — Long URLs inline, unclear CTAs
❌ **No Deal Tiers** — Users can't distinguish EXCELLENT from CLASSIQUE
❌ **Missing Urgency** — No signals about scarcity or value
❌ **Poor Spacing** — Information crammed, hard to scan vertically
❌ **Inline URLs** — Booking URLs exposed, clunky markdown syntax

---

## AFTER (Redesigned Format)

```
🌍 BARCELONA
🟠 PROMO FLASH — 3 offres

📅 Juin 2026
01 juin – 06 juin  |  5j
💰 15€  ·  -75% (EXCELLENT)
✈️ Ryanair
🔗 Voir le vol
🏨 Voir les hôtels

05 juin – 10 juin  |  5j
💰 45€  ·  -60% (BON)
✈️ EasyJet
🔗 Voir le vol
🏨 Voir les hôtels

📅 Juillet 2026
12 juil – 19 juil  |  7j
💰 120€  ·  -25% (CLASSIQUE)
✈️ Air France
🔗 Voir le vol

👉 Voir toutes les offres → https://globegenius.app/home?dest=BCN
```

### Improvements Delivered

✅ **Information Hierarchy**
- Destination `🌍 BARCELONA` at top, immediately scannable
- Count and badge on second line
- Users see destination first, not buried after fluff

✅ **Pricing Visibility**
- Isolated `💰 15€` line, easy to scan
- Discount and qualification tag separate: `-75% (EXCELLENT)`
- Price stands out visually with emoji + currency symbol

✅ **CTA Clarity**
- Simplified CTAs: `🔗 Voir le vol` (no long URLs)
- Clear intent: "See the flight" (not "Consult the deal")
- Hotel CTA only shown for high-value deals (≥40%)

✅ **Deal Qualification**
- `EXCELLENT` (≥60%) — unmistakable value
- `BON` (≥40%) — solid deal
- `CLASSIQUE` (<40%) — standard pricing
- Users can prioritize without reading text

✅ **Urgency Signals**
- Badge classification remains (🔴 ERREUR / 🟠 PROMO / 🟡 BON)
- Deal qualification reinforces scarcity perception
- High-discount deals show hotel CTAs first

✅ **Visual Consistency**
- Blank lines between offers (better scannability)
- Monthly sections clearly demarcated with 📅
- Airline on own line (not inline noise)
- Uniform spacing throughout

✅ **Removed Friction**
- No inline URLs (cleaner visual flow)
- No markdown syntax (simpler copy/paste)
- CTAs use clear action language

---

## Technical Changes

### Function: `format_grouped_flight_alerts()`
**File**: `/backend/app/notifications/telegram.py` (lines 175-273)

**Signature** (unchanged):
```python
def format_grouped_flight_alerts(
    origin_city: str,
    dest_city: str,
    destination_iata: str,
    offers: list[dict],
    tier: str = "premium",
) -> str:
```

**Implementation Changes**:
1. **Header restructuring**: Destination first, then badge + count
2. **Per-offer layout**: Date line, price line (isolated), airline, CTAs
3. **Qualification tags**: Auto-classify based on discount percentage
4. **CTA simplification**: Emoji + plain text instead of markdown + URLs
5. **Spacing**: Added blank lines between offers for vertical scannability

### Tests Updated
**File**: `/backend/app/tests/test_telegram.py`

Updated assertions for:
- Monthly header format (no count suffix)
- Date format (en-dash instead of hyphen)
- Overflow indicator text

All functionality tests pass; only format assertions adjusted.

---

## Verification

### Backward Compatibility
✅ Function signature unchanged
✅ Input validation unchanged
✅ Output is still a string (no breaking changes)
✅ Free tier upsell still appended (same logic)

### Test Coverage
✅ Single offer test: passes
✅ Multiple months test: passes
✅ Same-month offers test: passes
✅ 10+ offers capping test: passes
✅ Badge color tests: pass (red, orange, yellow)
✅ Free tier upsell test: passes

### Deployment Ready
✅ No database migrations required
✅ No API changes
✅ No configuration changes
✅ Backward compatible with existing user preferences
✅ Fully tested and committed

---

## Next Steps (Optional)

Could further enhance with:
- Link preview generation (if Telegram Client API available)
- Inline buttons for direct booking (Telegram inline keyboard)
- Price trend indicators (↑↓ if price volatile)
- Reviews/ratings from aggregator if available

But current redesign fully addresses user feedback and is production-ready.

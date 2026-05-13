"""Top-N routes for split-ticket detection.

Curated list of high-traffic CDG/ORY-origin destinations where
2x one-way frequently beats round-trip prices (mostly LCC + medium-haul
mixes).  Static for PR1; can later be derived from priority_destinations
or per-route booking analytics.
"""

# (origin_iata, destination_iata)
TOP_ROUTES_FOR_SPLIT: list[tuple[str, str]] = [
    # Paris hubs → Spain / Iberia (frequent LCC mix-and-match)
    ("CDG", "BCN"), ("CDG", "MAD"), ("CDG", "AGP"), ("CDG", "SVQ"),
    ("CDG", "VLC"), ("CDG", "ALC"), ("CDG", "PMI"), ("CDG", "IBZ"),
    ("ORY", "BCN"), ("ORY", "MAD"), ("ORY", "AGP"), ("ORY", "PMI"),
    # Paris → Portugal
    ("CDG", "LIS"), ("CDG", "OPO"), ("ORY", "LIS"), ("ORY", "OPO"),
    # Paris → Italy
    ("CDG", "FCO"), ("CDG", "MXP"), ("CDG", "VCE"), ("CDG", "NAP"),
    ("ORY", "FCO"), ("ORY", "MXP"), ("ORY", "NAP"),
    # Paris → Greece / Croatia / Eastern Med
    ("CDG", "ATH"), ("CDG", "DBV"), ("CDG", "SPU"),
    # Paris → North Africa
    ("CDG", "RAK"), ("CDG", "CMN"), ("ORY", "RAK"), ("ORY", "TUN"),
]

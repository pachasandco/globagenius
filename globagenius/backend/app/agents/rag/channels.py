"""YouTube travel channels to ingest for RAG knowledge base."""

YOUTUBE_CHANNELS = [
    {
        "name": "Mark Wiens",
        "handle": "@MarkWiens",
        "channel_id": "UCZYTClwyANRz-a1pMBt-gw",  # Mark Wiens
        "subscribers": "11-12M",
        "focus": "Travel + Food (ultra dominant in travel food)",
    },
    {
        "name": "Best Ever Food Review Show",
        "handle": "@besteverfoodreviewshow",
        "channel_id": "UCvI7sDdF9pVUPf-HkFDpqQQ",  # Best Ever Food Review Show (approx)
        "subscribers": "12M",
        "focus": "Documentary format + street food global",
    },
    {
        "name": "Nas Daily",
        "handle": "@NasDaily",
        "channel_id": "UCeUZFvw9sKsqMXNOJJMHSFw",  # Nas Daily
        "subscribers": "14M",
        "focus": "Short-form, storytelling worldwide",
    },
    {
        "name": "Travel Thirsty",
        "handle": "@TravelThirsty",
        "channel_id": "UCnBl_FV7z-TkC5aILDWX3ow",  # Travel Thirsty (approx)
        "subscribers": "8M",
        "focus": "Cuisine and visual immersion",
    },
    {
        "name": "Drew Binsky",
        "handle": "@drewbinsky",
        "channel_id": "UC5wm1a1WgyBDuNQjGLEVlTA",  # Drew Binsky
        "subscribers": "4M",
        "focus": "Visit every country objective",
    },
    {
        "name": "Kara and Nate",
        "handle": "@KaraandNate",
        "channel_id": "UC0iKzKO7OJWz6Ny3e2JvAKw",  # Kara and Nate
        "subscribers": "4M",
        "focus": "Couple, 100+ countries",
    },
    {
        "name": "Lost LeBlanc",
        "handle": "@LostLeBlanc",
        "channel_id": "UClvj6fynVqQfRCAm06u3yEQ",  # Lost LeBlanc
        "subscribers": "2.5-3M",
        "focus": "Travel lifestyle, digital nomad",
    },
    {
        "name": "Indigo Traveller",
        "handle": "@IndigoTraveller",
        "channel_id": "UCT8eS8KqPHBGdCqQ3VDtL9g",  # Indigo Traveller (approx)
        "subscribers": "2M",
        "focus": "Risk-prone destinations, documentary",
    },
    {
        "name": "Nadir On The Go",
        "handle": "@NadirOnTheGo",
        "channel_id": "UCjq4jgOsFRqo3xAJlK5fhsg",  # Nadir On The Go (approx)
        "subscribers": "2.2M",
        "focus": "Bilingual content, cultural storytelling",
    },
    {
        "name": "Wolters World",
        "handle": "@WoltersWorld",
        "channel_id": "UCTLt0WM5VYPsYOc_7MgMrJg",  # Wolters World
        "subscribers": "1M+",
        "focus": "Travel tips and destination guides",
    },
    {
        "name": "FunForLouis",
        "handle": "@FunForLouis",
        "channel_id": "UCfhU7hxFhLNKJUaY_aTvI4w",  # Fun for Louis (approx)
        "subscribers": "2M",
        "focus": "Travel adventure and lifestyle",
    },
    {
        "name": "Mountain Trekker",
        "handle": "@MountainTrekker",
        "channel_id": "UCvK4bOhUPN0YJ0x0d8q-VNQ",  # Mountain Trekker (approx)
        "subscribers": "1.5M",
        "focus": "Mountain and nature travel",
    },
    {
        "name": "Mumbiker Nikhil",
        "handle": "@MumbikerNikhil",
        "channel_id": "UC5AEXHEiKqfDfDPPNPQ_-ng",  # Mumbiker Nikhil
        "subscribers": "4M",
        "focus": "Road trips and motorcycle travel",
    },
]

# Map of channel handle to YouTube channel ID (for quick lookup)
CHANNEL_HANDLE_MAP = {ch["handle"]: ch["channel_id"] for ch in YOUTUBE_CHANNELS}

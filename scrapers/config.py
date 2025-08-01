"""
Central configuration for the scraping suite
"""

# Geographic settings
TOULOUSE_COORDS = {"lat": 43.6047, "lng": 1.4442}
SEARCH_RADIUS_KM = 200

# Instagram settings
INSTAGRAM_CONFIG = {
    "username": "fiac_lux",
    "password": "@lfreD33",
    "session_file": "instagrapi_session.json",
    "rate_limit_delay": [3, 7],  # Random delay between requests
    "hashtags_per_run": 15,
    "posts_per_hashtag": 15,
}

# Reddit settings (demo mode by default)
REDDIT_CONFIG = {
    "client_id": "YOUR_CLIENT_ID",
    "client_secret": "YOUR_CLIENT_SECRET",
    "user_agent": "FrenchOutdoorScraper/1.0",
    "use_demo_mode": True,
}

# Database
DATABASE_PATH = "hidden_spots.db"

# Hashtags for Instagram
INSTAGRAM_HASHTAGS = {
    "water": [
        "baignadesauvage",
        "baignadenaturelle",
        "lacdemontagne",
        "cascadefrance",
        "cascadecachee",
        "sourcesecrète",
    ],
    "hiking": [
        "randonnee",
        "randonneefrance",
        "spotsecret",
        "bivouacfrance",
        "spotbivouac",
        "refugesecret",
    ],
    "urbex": [
        "urbexfrance",
        "urbex",
        "explorationurbaine",
        "lieuxabandonnés",
        "abandonné",
        "friche",
    ],
    "caves": [
        "speleologie",
        "speleof",
        "grottesecrete",
        "cavernesfrance",
        "explorationsouterraine",
        "gouffre",
    ],
    "regional": [
        "toulouse",
        "toulousemaville",
        "occitanie",
        "hautegaronne",
        "midipyrenees",
        "pyrenees",
        "ariege",
        "tarn",
        "tarnetgaronne",
        "gers",
        "cevennes",
        "montnoirfrance",
        "lauragais",
    ],
}

# Reddit subreddits
REDDIT_SUBREDDITS = [
    "france",
    "toulouse",
    "occitanie",
    "randonee",
    "VoyageFrance",
    "AskFrance",
    "pyrenees",
    "midi_pyrenees",
]

# Keywords for identifying hidden spots
HIDDEN_KEYWORDS = [
    "secret",
    "caché",
    "peu connu",
    "sauvage",
    "préservé",
    "hors des sentiers",
    "méconnu",
    "confidentiel",
    "insolite",
    "abandonné",
    "désaffecté",
    "oublié",
    "interdit",
    "fermé au public",
    "accès restreint",
    "en ruine",
    "inexploré",
    "non balisé",
    "découverte",
    "vierge",
]

# Activity keywords
ACTIVITY_KEYWORDS = {
    "water": ["cascade", "lac", "rivière", "baignade", "source", "piscine naturelle"],
    "urbex": ["abandonné", "friche", "désaffecté", "ruine", "urbex"],
    "cave": ["grotte", "gouffre", "spéléo", "caverne", "souterrain"],
    "hiking": ["randonnée", "sentier", "gr", "chemin", "balade"],
}

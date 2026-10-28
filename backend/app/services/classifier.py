"""Classification automatique des chaînes : catégorie, langue, qualité, priorité.

Le moteur est 100 % basé sur des règles explicites (aucun service externe, aucun modèle
propriétaire) : il est donc rapide, prévisible et facilement extensible via les tables
ci-dessous.
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

from app.core.config import settings

# ---------------------------------------------------------------------------
# Catégories : slug -> (libellé, icône, couleur, mots-clés)
# ---------------------------------------------------------------------------
CATEGORY_RULES: dict[str, dict] = {
    "sport": {
        "name": "Sport",
        "icon": "trophy",
        "color": "#22c55e",
        "keywords": [
            "sport", "sports", "football", "foot", "soccer", "nba", "nfl", "nhl", "mlb", "f1",
            "formula", "motogp", "tennis", "golf", "rugby", "cricket", "boxing", "boxe", "mma", "ufc",
            "wrestling", "catch", "athletisme", "athletics", "olympic", "olympique", "cycling", "cyclisme",
            "basket", "basketball", "handball", "volley", "hockey", "sportv", "eurosport", "beinsport",
            "bein sport", "ssc", "alkass", "dazn", "espn", "sky sport", "canal sport", "supersport",
            "رياضة", "رياضه", "الرياضية", "الرياضيه", "كورة", "ملاعب", "سبورت", "دوري",
        ],
    },
    "news": {
        "name": "News",
        "icon": "newspaper",
        "color": "#3b82f6",
        "keywords": [
            "news", "info", "infos", "actualite", "actualites", "journal", "24h", "cnn", "bbc", "france 24",
            "france24", "aljazeera", "al jazeera", "sky news", "euronews", "rt", "arirang", "dw", "trt haber",
            "nhk", "cbs", "nbc", "abc news", "fox news", "msnbc", "bloomberg", "cnbc", "lci", "bfmtv", "bfm tv",
            "cnews", "i24", "tv5monde info", "العربية", "الاخبارية", "الاخباريه", "اخبار", "الجزيرة", "العالم",
            "أخبار", "جديد",
        ],
    },
    "movies": {
        "name": "Movies",
        "icon": "film",
        "color": "#a855f7",
        "keywords": [
            "movie", "movies", "cinema", "cine", "film", "films", "series", "serie", "serieclub", "action",
            "comedy", "drama", "horror", "thriller", "scifi", "sci-fi", "ocs", "canal cinema", "tcm", "starz",
            "showtime", "hbo", "amc", "paramount", "syfy", "mgm", "universal", "fx", "netflix", "prime video",
            "أفلام", "افلام", "سينما", "مسلسلات", "دراما", "فيلم",
        ],
    },
    "kids": {
        "name": "Kids",
        "icon": "baby",
        "color": "#f97316",
        "keywords": [
            "kids", "kid", "children", "child", "junior", "cartoon", "cartoons", "nick", "nickelodeon",
            "disney", "disney junior", "disney channel", "baby", "boomerang", "toon", "gulli", "piwi",
            "teletoon", "pogo", "chutti", "cn", "cartoon network", "pbs kids", "moonbug", "jeunesse",
            "enfants", "dessin anime", "dessins animes", "أطفال", "اطفال",
            "كرتون", "طيور الجنة", "سبيستون", "مجلة",
        ],
    },
    "music": {
        "name": "Music",
        "icon": "music",
        "color": "#ec4899",
        "keywords": [
            "music", "musique", "mtv", "vh1", "trace", "mcm", "nrj", "virgin", "hits", "clips",
            "dance", "rock", "jazz", "classic", "classique", "opera", "mezzo", "stingray", "kerrang",
            "موسيقى", "موسيقي", "أغاني", "اغاني", "طرب", "نجوم",
        ],
    },
    "religion": {
        "name": "Religion",
        "icon": "book-open",
        "color": "#14b8a6",
        "keywords": [
            "religion", "religious", "islam", "islamic", "quran", "coran", "holy", "gospel", "church",
            "christian", "catholic", "bible", "jewish", "torah", "hindu", "bhakti", "sunnah", "mecca",
            "makkah", "madinah", "iqraa", "risala", "majd", "saudi quran", "peace tv", "ewtn", "kbc",
            "قرآن", "القرآن", "قران", "القران", "إسلام", "اسلام", "دين", "ديني", "سنة", "السنة", "مكة",
            "المدينة", "إقرأ", "اقرأ", "الرسالة", "دعاء", "church",
        ],
    },
    "documentary": {
        "name": "Documentary",
        "icon": "compass",
        "color": "#eab308",
        "keywords": [
            "documentary", "documentaire", "docu", "discovery", "nat geo", "natgeo", "national geographic",
            "history", "planete", "planete+", "ushuaia", "voyage", "animal planet", "science", "nature",
            "curiosity", "smithsonian", "crime investigation", "investigation", "ثقافي", "وثائقي", "وثائقية",
            "ناشيونال",
        ],
    },
    "entertainment": {
        "name": "Entertainment",
        "icon": "sparkles",
        "color": "#8b5cf6",
        "keywords": [
            "entertainment", "divertissement", "variety", "reality", "show", "talk", "m6", "tf1", "tfx", "w9",
            "tmc", "c8", "cstar", "comedy central", "tlc", "e!", "bravo", "gameshow", "télé-réalité",
            "ترفيه", "منوعات", "مسابقات",
        ],
    },
    "culture": {
        "name": "Culture",
        "icon": "landmark",
        "color": "#06b6d4",
        "keywords": [
            "culture", "art", "arte", "theatre", "théâtre", "museum", "musée", "literature", "lecture",
            "education", "educatif", "école", "learn", "learning", "university", "samarra",
            "ثقافة", "تعليم", "تعليمية",
        ],
    },
    "adult": {
        "name": "Adult",
        "icon": "shield-alert",
        "color": "#ef4444",
        "keywords": ["adult", "xxx", "erotic", "erotique", "porn", "playboy", "hustler", "brazzers", "adulte"],
    },
    "local": {
        "name": "Local",
        "icon": "map-pin",
        "color": "#64748b",
        "keywords": [
            "local", "regional", "régional", "province", "city", "tv locale", "tunisie", "tunisia", "watania",
            "tunis", "mosaique", "nessma", "hannibal", "zitouna", "local tv", "محلي", "محلية", "تونس", "الوطنية",
        ],
    },
}

# ---------------------------------------------------------------------------
# Langues : code -> (libellé, drapeau, mots-clés/indices script ou pays)
# ---------------------------------------------------------------------------
LANGUAGE_RULES: dict[str, dict] = {
    "ar": {"name": "Arabic", "native_name": "العربية", "flag": "🇸🇦", "position": 0,
           "keywords": ["arabic", "arabe", "ar", "عربي", "العربية", "خليجي", "مغربي", "شام"]},
    "fr": {"name": "French", "native_name": "Français", "flag": "🇫🇷", "position": 1,
           "keywords": ["french", "francais", "français", "fr", "vf", "francophone", "quebec"]},
    "en": {"name": "English", "native_name": "English", "flag": "🇬🇧", "position": 2,
           "keywords": ["english", "anglais", "en", "uk", "us", "usa", "british", "american", "au", "ca"]},
    "tr": {"name": "Turkish", "native_name": "Türkçe", "flag": "🇹🇷", "position": 3,
           "keywords": ["turkish", "turc", "turkiye", "türkiye", "tr", "turk"]},
    "es": {"name": "Spanish", "native_name": "Español", "flag": "🇪🇸", "position": 4,
           "keywords": ["spanish", "espagnol", "español", "es", "latino", "latina", "mexico", "argentina"]},
    "de": {"name": "German", "native_name": "Deutsch", "flag": "🇩🇪", "position": 5, "keywords": ["german", "allemand", "de", "deutsch"]},
    "it": {"name": "Italian", "native_name": "Italiano", "flag": "🇮🇹", "position": 6, "keywords": ["italian", "italien", "it", "italiano"]},
    "pt": {"name": "Portuguese", "native_name": "Português", "flag": "🇵🇹", "position": 7, "keywords": ["portuguese", "portugais", "pt", "brasil", "brazil"]},
    "nl": {"name": "Dutch", "native_name": "Nederlands", "flag": "🇳🇱", "position": 8, "keywords": ["dutch", "neerlandais", "nl"]},
    "ru": {"name": "Russian", "native_name": "Русский", "flag": "🇷🇺", "position": 9, "keywords": ["russian", "russe", "ru", "рус"]},
    "hi": {"name": "Hindi", "native_name": "हिन्दी", "flag": "🇮🇳", "position": 10, "keywords": ["hindi", "india", "in", "bollywood"]},
    "ur": {"name": "Urdu", "native_name": "اردو", "flag": "🇵🇰", "position": 11, "keywords": ["urdu", "pakistan", "pk"]},
    "fa": {"name": "Persian", "native_name": "فارسی", "flag": "🇮🇷", "position": 12, "keywords": ["persian", "farsi", "iran", "ir"]},
    "ku": {"name": "Kurdish", "native_name": "Kurdî", "flag": "🏳️", "position": 13, "keywords": ["kurdish", "kurde", "kurd", "rojava"]},
    "zh": {"name": "Chinese", "native_name": "中文", "flag": "🇨🇳", "position": 14, "keywords": ["chinese", "mandarin", "cctv", "zh"]},
    "other": {"name": "Other", "native_name": "Other", "flag": "🌍", "position": 99, "keywords": []},
}

COUNTRY_LANGUAGE = {
    "tn": "ar", "dz": "ar", "ma": "ar", "eg": "ar", "sa": "ar", "ae": "ar", "qa": "ar", "kw": "ar",
    "bh": "ar", "om": "ar", "jo": "ar", "lb": "ar", "sy": "ar", "iq": "ar", "ye": "ar", "ps": "ar",
    "ly": "ar", "sd": "ar", "mr": "ar", "ar": "es", "fr": "fr", "be": "fr", "ch": "fr", "ca": "fr",
    "us": "en", "uk": "en", "gb": "en", "au": "en", "ie": "en", "nz": "en", "za": "en", "in": "hi",
    "tr": "tr", "es": "es", "mx": "es", "ar ": "es", "co": "es", "cl": "es", "pe": "es", "ve": "es",
    "de": "de", "at": "de", "it": "it", "pt": "pt", "br": "pt", "nl": "nl", "ru": "ru", "ua": "ru",
    "ir": "fa", "pk": "ur", "cn": "zh", "hk": "zh", "tw": "zh", "sg": "zh",
}

_ARABIC_RE = re.compile(r"[\u0600-\u06FF]")
_FRENCH_HINTS = re.compile(r"\b(le|la|les|des|du|é|è|de|tv5|franc|monde|foot|sport|cinema|série)\b", re.I)
_QUALITY_PATTERNS = [
    ("8K", re.compile(r"\b(8k|uhd8k)\b", re.I)),
    ("4K", re.compile(r"\b(4k|uhd|ultra\s?hd|2160p?)\b", re.I)),
    ("FHD", re.compile(r"\b(fhd|1080p?|full\s?hd)\b", re.I)),
    ("HD", re.compile(r"\b(hd|720p?|h265|hevc)\b", re.I)),
    ("SD", re.compile(r"\b(sd|576p?|480p?|360p?)\b", re.I)),
]


@dataclass
class Classification:
    """Résultat de la classification d'une chaîne."""

    category_slug: str
    language_code: str
    quality: str | None
    is_radio: bool
    priority: int
    normalized_name: str
    is_encrypted_hint: bool
    tags: list[str]


def normalize_text(value: str) -> str:
    """Minuscule, sans accents, sans ponctuation superflue (pour la recherche)."""
    value = unicodedata.normalize("NFKD", value or "")
    value = "".join(char for char in value if not unicodedata.combining(char))
    value = value.replace("&", " and ")
    value = re.sub(r"[\u064B-\u0652]", "", value)  # diacritiques arabes
    value = re.sub(r"\s+", " ", value)
    return value.strip().lower()


def detect_category(*sources: str | None) -> str:
    """Détermine la catégorie à partir du nom, du groupe et des métadonnées."""
    haystack = normalize_text(" ".join(source for source in sources if source))
    if not haystack:
        return "entertainment"
    scores: dict[str, int] = {}
    for slug, rule in CATEGORY_RULES.items():
        score = 0
        for keyword in rule["keywords"]:
            normalized_keyword = normalize_text(keyword)
            if not normalized_keyword:
                continue
            # Un « s » final est toléré : « Documentaires », « Sports », « Films »…
            if re.search(rf"(?<!\w){re.escape(normalized_keyword)}s?(?!\w)", haystack):
                score += 3 if len(normalized_keyword) > 4 else 2
        if score:
            scores[slug] = score
    if not scores:
        return "entertainment"
    # « adult » est prioritaire s'il est détecté (filtrage plus simple)
    if scores.get("adult", 0) >= 2:
        return "adult"
    return max(scores.items(), key=lambda item: item[1])[0]


def detect_language(*sources: str | None, country: str | None = None) -> str:
    """Détermine la langue via indices explicites, script, pays puis heuristiques."""
    cleaned_country = (country or "").strip().lower()[:3]
    if cleaned_country and cleaned_country[:2] in COUNTRY_LANGUAGE:
        return COUNTRY_LANGUAGE[cleaned_country[:2]]

    joined_raw = " ".join(source for source in sources if source)
    haystack = normalize_text(joined_raw)
    explicit = re.search(r"\b(tvg-language|lang(?:ue)?)\s*[=:]\s*([a-z]{2,3})\b", joined_raw, re.I)
    if explicit:
        code = explicit.group(2).lower()
        if code in LANGUAGE_RULES:
            return code

    for code, rule in LANGUAGE_RULES.items():
        if code == "other":
            continue
        for keyword in rule["keywords"]:
            normalized_keyword = normalize_text(keyword)
            # Un « s » final est toléré : « Documentaires », « Sports », « Films »…
            if re.search(rf"(?<!\w){re.escape(normalized_keyword)}s?(?!\w)", haystack):
                return code

    if _ARABIC_RE.search(joined_raw):
        return "ar"
    if _FRENCH_HINTS.search(haystack):
        return "fr"
    if not haystack:
        return "other"
    return "en" if re.search(r"\b(news|sport|kids|movies|music|tv|live)\b", haystack) else "other"


def detect_quality(*sources: str | None) -> str | None:
    haystack = " ".join(source for source in sources if source)
    for label, pattern in _QUALITY_PATTERNS:
        if pattern.search(haystack):
            return label
    return None


def compute_priority(category_slug: str, language_code: str, is_radio: bool, has_epg: bool) -> int:
    """Score de mise en avant : les chaînes sportives et arabes passent devant."""
    priority = 0
    if category_slug == "sport":
        priority += settings.PRIORITY_SPORT
    if language_code == "ar":
        priority += settings.PRIORITY_ARABIC
    if category_slug == "news":
        priority += settings.PRIORITY_NEWS
    if language_code == "fr":
        priority += settings.PRIORITY_FRENCH
    if has_epg:
        priority += 2
    if is_radio:
        priority -= 5
    if category_slug == "adult":
        priority -= 100
    return priority


def classify(
    name: str,
    *,
    group: str | None = None,
    tvg_language: str | None = None,
    country: str | None = None,
    is_radio_hint: bool = False,
    has_epg: bool = False,
    encrypted_hint: bool = False,
) -> Classification:
    """Classe une chaîne de bout en bout."""
    category_slug = detect_category(name, group)
    if category_slug == "entertainment" and is_radio_hint:
        # Une radio sans mot-clé identifiable (ex. « France Inter ») reste une
        # chaîne musicale plutôt que d'être rangée dans « Divertissement ».
        category_slug = "music"
    language_code = detect_language(
        tvg_language or "", name, group, country=country
    )
    if language_code not in LANGUAGE_RULES:
        language_code = "other"
    quality = detect_quality(name, group)
    tags = [category_slug, language_code]
    if quality:
        tags.append(quality.lower())
    if encrypted_hint:
        tags.append("encrypted")
    priority = compute_priority(category_slug, language_code, is_radio_hint, has_epg)
    return Classification(
        category_slug=category_slug,
        language_code=language_code,
        quality=quality,
        is_radio=is_radio_hint,
        priority=priority,
        normalized_name=normalize_text(name),
        is_encrypted_hint=encrypted_hint,
        tags=tags,
    )


def seed_reference_data() -> tuple[list[dict], list[dict]]:
    """Retourne les catégories et langues de référence à insérer au démarrage."""
    categories = [
        {
            "slug": slug,
            "name": rule["name"],
            "icon": rule["icon"],
            "color": rule["color"],
            "position": index * 10,
        }
        for index, (slug, rule) in enumerate(CATEGORY_RULES.items())
    ]
    languages = [
        {
            "code": code,
            "name": rule["name"],
            "native_name": rule["native_name"],
            "flag": rule["flag"],
            "position": rule["position"],
        }
        for code, rule in sorted(LANGUAGE_RULES.items(), key=lambda item: item[1]["position"])
    ]
    return categories, languages

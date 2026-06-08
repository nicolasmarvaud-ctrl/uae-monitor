#!/usr/bin/env python3
"""
UAE-France Economic Monitor - RSS News Fetcher
Fetches news from French and UAE sources, filters by sector, scores relevance,
translates Arabic content, and generates JSON digests for the static dashboard.
"""

import feedparser
import json
import hashlib
import os
import re
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path
from deep_translator import GoogleTranslator

# --- Configuration ---

SECTORS = {
    "energy": {
        "label": "Energy",
        "keywords": [
            "energy sector", "energy deal", "energy investment", "energy project",
            "oil production", "oil field", "oil price", "crude oil",
            "natural gas", "petroleum", "ADNOC", "TAQA", "Masdar",
            "renewable energy", "solar energy", "solar power", "solar farm",
            "wind energy", "wind farm", "wind power",
            "hydrogen", "green hydrogen", "blue hydrogen",
            "nuclear energy", "nuclear power", "Barakah",
            "power plant", "power generation", "LNG",
            "refinery", "petrochemical", "offshore",
            "carbon capture", "CCUS", "energy transition", "clean energy",
            "TotalEnergies", "Engie", "EDF", "Orano", "Technip", "Technip Energies",
            "transition energetique", "petrole", "gaz naturel",
            "energie renouvelable", "energie solaire", "energie eolienne",
            "hydrogene vert", "centrale nucleaire"
        ]
    },
    "ai_tech": {
        "label": "AI & New Technologies",
        "keywords": [
            "artificial intelligence", "machine learning", "deep learning",
            "generative AI", "large language model", "LLM", "neural network",
            "data center", "data centre", "semiconductor", "microchip",
            "robotics", "quantum computing", "cybersecurity", "cyber security",
            "smart city", "smart cities", "G42", "Presight",
            "Abu Dhabi AI", "Technology Innovation Institute", "MBZUAI",
            "OVHcloud", "Dassault Systemes",
            "intelligence artificielle", "apprentissage automatique",
            "centre de donnees", "semi-conducteur", "informatique quantique",
            "ville intelligente", "deeptech"
        ],
        # Short keywords that need word-boundary matching (regex \b)
        "keywords_bounded": ["\\bAI\\b", "\\bIA\\b", "\\bIoT\\b", "\\b5G\\b", "\\b6G\\b"]
    },
    "climate": {
        "label": "Climate Transition",
        "keywords": [
            "climate change", "climate policy", "climate action", "climate finance",
            "carbon neutral", "carbon footprint", "carbon tax", "carbon market",
            "CO2 emission", "greenhouse gas", "net zero", "net-zero",
            "sustainability", "sustainable development", "sustainable finance",
            "ESG investing", "ESG criteria", "green bond", "green finance",
            "decarbonization", "decarbonisation",
            "circular economy", "waste management", "water desalination",
            "biodiversity", "environmental protection",
            "changement climatique", "neutralite carbone", "finance verte",
            "developpement durable", "decarbonation", "economie circulaire",
            "gestion dechets", "dessalement", "obligation verte"
        ],
        "keywords_bounded": ["\\bCOP\\d+\\b", "\\bCOP \\d+\\b"]
    },
    "food_security": {
        "label": "Food Security",
        "keywords": [
            "food security", "food supply", "food production", "food import",
            "food self-sufficiency", "food tech", "foodtech",
            "agritech", "agri-tech", "agricultural technology",
            "vertical farm", "vertical farming", "indoor farming",
            "aquaculture", "fish farming", "irrigation system",
            "Al Dahra", "Agthia", "Elite Agro",
            "securite alimentaire", "production alimentaire",
            "ferme verticale", "autosuffisance alimentaire",
            "technologie agricole", "agroalimentaire"
        ]
    },
    "logistics": {
        "label": "Logistics",
        "keywords": [
            "logistics hub", "logistics sector", "supply chain",
            "shipping route", "shipping line", "freight transport",
            "free zone", "free trade zone", "trade corridor",
            "Jebel Ali", "DP World", "Etihad Rail", "Abu Dhabi Ports",
            "AD Ports", "port authority", "container terminal",
            "maritime trade", "maritime transport", "cargo hub",
            "CMA CGM", "Bollore Logistics",
            "logistique", "chaine approvisionnement", "zone franche",
            "transport maritime", "corridor commercial", "fret",
            "plateforme logistique"
        ]
    },
    "aeronautics": {
        "label": "Aeronautics",
        "keywords": [
            "aeronautics", "aerospace industry", "aerospace sector",
            "aviation industry", "aviation sector", "aircraft order",
            "aircraft delivery", "airline industry",
            "Airbus", "Boeing", "Etihad Airways", "Emirates airline",
            "flydubai", "Wizz Air Abu Dhabi",
            "Safran", "Thales", "Dassault Aviation", "MBDA",
            "defense contract", "defense industry", "defence industry",
            "military aircraft", "fighter jet",
            "drone technology", "unmanned aerial",
            "Dubai Airshow", "air show",
            "MRO", "aircraft maintenance",
            "aeronautique", "industrie aerospatiale",
            "industrie aerienne", "avion de combat",
            "industrie de defense", "salon aeronautique",
            "maintenance aeronautique"
        ],
        "keywords_bounded": ["\\bUAV\\b"]
    },
    "space": {
        "label": "Space",
        "keywords": [
            "space industry", "space sector", "space program", "space programme",
            "space agency", "space exploration", "space mission", "space technology",
            "satellite launch", "satellite constellation", "satellite operator",
            "earth observation satellite", "communication satellite",
            "orbital", "low earth orbit",
            "UAE Space Agency", "MBRSC", "Mohammed bin Rashid Space",
            "Hope probe", "Hope Mars",
            "CNES", "Arianespace", "ArianeGroup", "Thales Alenia Space",
            "industrie spatiale", "secteur spatial", "programme spatial",
            "agence spatiale", "lancement satellite", "exploration spatiale",
            "mission spatiale"
        ]
    },
    "fintech": {
        "label": "Fintech",
        "keywords": [
            "fintech", "financial technology", "digital banking", "neobank",
            "mobile payment", "digital payment", "payment platform",
            "cryptocurrency", "crypto exchange", "bitcoin", "stablecoin",
            "CBDC", "digital currency", "central bank digital",
            "insurtech", "regtech", "wealthtech", "open banking",
            "ADGM", "Abu Dhabi Global Market",
            "DIFC", "Dubai International Financial Centre",
            "First Abu Dhabi Bank",
            "technologie financiere", "banque numerique",
            "paiement numerique", "monnaie numerique",
            "cryptomonnaie"
        ]
    },
    "health": {
        "label": "Health",
        "keywords": [
            "healthcare sector", "healthcare industry", "healthcare investment",
            "hospital project", "hospital construction",
            "pharmaceutical industry", "pharma company", "pharma sector",
            "biotech company", "biotech sector", "biotechnology",
            "medical device", "medical technology", "medtech",
            "life sciences", "clinical trial", "clinical research",
            "genomics", "precision medicine", "telemedicine", "telehealth",
            "Abu Dhabi Health", "SEHA", "Mubadala Health", "M42",
            "Sanofi", "Servier", "bioMerieux", "Essilor Luxottica",
            "industrie pharmaceutique", "dispositif medical",
            "sciences de la vie", "essai clinique", "recherche clinique",
            "telemedecine", "secteur de la sante"
        ],
        "keywords_bounded": ["\\bDHA\\b"]
    }
}

# Geographic keywords — articles from non-UAE sources MUST match at least one
# ONLY UAE-specific terms. No generic "Middle East", "Gulf", company names.
GEO_KEYWORDS = [
    # UAE country names
    "UAE", "United Arab Emirates",
    "Emirats Arabes Unis", "Emirats arabes unis",
    # Demonyms
    "emirien", "emiriens", "emirienne", "emiriennes",
    "emirati", "emiratis", "Emirati", "Emiratis",
    # Emirates / cities
    "Abu Dhabi", "Dubai", "Sharjah", "Ajman", "Fujairah",
    "Ras Al Khaimah", "Umm Al Quwain", "Al Ain",
    "Saadiyat", "Yas Island", "Khalifa City",
    # Key UAE sovereign entities
    "Mubadala", "ADIA", "ADIO", "ICD",
    "TAQA", "ADNOC", "Masdar",
    "Etihad Airways", "Etihad Rail", "Emirates airline", "flydubai",
    "DP World", "AD Ports", "G42", "EDGE Group",
    "Emaar", "Aldar", "First Abu Dhabi Bank",
    "DIFC", "ADGM", "DMCC", "Jafza", "Jebel Ali",
    "MBZUAI", "Abu Dhabi Investment Authority",
    "Dubai Holding", "Dubai Future Foundation",
    "Emirates Nuclear", "Barakah",
    # France-UAE bilateral
    "franco-emirien", "franco-emirati", "France-EAU", "France-UAE"
]
# Short geo keywords needing word boundaries
# Bounded geo keywords: require word boundaries AND context to avoid false positives
# "EAU" excluded — too many false positives with French "l'eau" (water)
# "ADQ" moved here for word boundary matching
GEO_KEYWORDS_BOUNDED = ["\\bFAB\\b", "\\bTII\\b", "\\bADQ\\b"]

# RSS Feed sources
FEEDS = {
    # --- French Sources ---
    "Les Echos": {
        "url": "https://syndication.lesechos.fr/rss/rss_une.xml",
        "lang": "fr",
        "category": "french"
    },
    "Les Echos Industrie": {
        "url": "https://syndication.lesechos.fr/rss/rss_industrie.xml",
        "lang": "fr",
        "category": "french"
    },
    "Les Echos Tech": {
        "url": "https://syndication.lesechos.fr/rss/rss_tech_medias.xml",
        "lang": "fr",
        "category": "french"
    },
    "La Tribune": {
        "url": "https://www.latribune.fr/rss/rubriques/economie.html",
        "lang": "fr",
        "category": "french"
    },
    "Le Monde Economie": {
        "url": "https://www.lemonde.fr/economie/rss_full.xml",
        "lang": "fr",
        "category": "french"
    },
    "Le Monde International": {
        "url": "https://www.lemonde.fr/international/rss_full.xml",
        "lang": "fr",
        "category": "french"
    },
    "BFM Business": {
        "url": "https://www.bfmtv.com/rss/economie/",
        "lang": "fr",
        "category": "french"
    },
    "L'Usine Nouvelle": {
        "url": "https://www.usinenouvelle.com/rss/",
        "lang": "fr",
        "category": "french"
    },
    "France 24 Eco FR": {
        "url": "https://www.france24.com/fr/eco-tech/rss",
        "lang": "fr",
        "category": "french"
    },
    "France 24 Eco EN": {
        "url": "https://www.france24.com/en/business/rss",
        "lang": "en",
        "category": "french"
    },
    "Le Figaro Economie": {
        "url": "https://www.lefigaro.fr/rss/figaro_economie.xml",
        "lang": "fr",
        "category": "french"
    },
    "Challenges": {
        "url": "https://www.challenges.fr/rss.xml",
        "lang": "fr",
        "category": "french"
    },
    "La Croix Economie": {
        "url": "https://www.la-croix.com/rss/economie.xml",
        "lang": "fr",
        "category": "french"
    },
    "L'Opinion": {
        "url": "https://www.lopinion.fr/rss",
        "lang": "fr",
        "category": "french"
    },
    "Le JDD": {
        "url": "https://www.lejdd.fr/rss.xml",
        "lang": "fr",
        "category": "french"
    },
    "Le Grand Continent": {
        "url": "https://legrandcontinent.eu/fr/feed/",
        "lang": "fr",
        "category": "french"
    },
    "Alternatives Economiques": {
        "url": "https://www.alternatives-economiques.fr/rss.xml",
        "lang": "fr",
        "category": "french"
    },
    "Mediapart": {
        "url": "https://www.mediapart.fr/articles/feed",
        "lang": "fr",
        "category": "french"
    },
    "The Economist": {
        "url": "https://www.economist.com/middle-east-and-africa/rss.xml",
        "lang": "en",
        "category": "international"
    },

    # --- UAE / Gulf Sources (English) ---
    "The National": {
        "url": "https://www.thenationalnews.com/arc/outboundfeeds/rss/?outputType=xml&size=30",
        "lang": "en",
        "category": "uae"
    },
    "Gulf News": {
        "url": "https://gulfnews.com/feed",
        "lang": "en",
        "category": "uae"
    },

    # --- Sector-specific / International ---
    "Reuters Energy": {
        "url": "https://www.reuters.com/technology/rss",
        "lang": "en",
        "category": "international"
    },
    "SpaceNews": {
        "url": "https://spacenews.com/feed/",
        "lang": "en",
        "category": "international"
    },
    "IRENA": {
        "url": "https://www.irena.org/rss",
        "lang": "en",
        "category": "international"
    },
    "TechCrunch": {
        "url": "https://techcrunch.com/feed/",
        "lang": "en",
        "category": "international"
    },
    "FlightGlobal": {
        "url": "https://www.flightglobal.com/rss",
        "lang": "en",
        "category": "international"
    },
}


def compute_article_id(title, link):
    """Generate a unique ID for an article."""
    raw = f"{title}|{link}"
    return hashlib.md5(raw.encode("utf-8")).hexdigest()[:12]


def translate_arabic(text):
    """Translate Arabic text to English using Google Translate (free)."""
    if not text or not text.strip():
        return text
    try:
        translated = GoogleTranslator(source="ar", target="en").translate(text[:4500])
        return translated if translated else text
    except Exception as e:
        print(f"  [WARN] Translation failed: {e}")
        return text


def translate_french(text):
    """Translate French text to English for keyword matching."""
    # We don't actually translate french articles — we match french keywords directly
    # This function is only used if needed for relevance scoring
    return text


def clean_html(text):
    """Remove HTML tags from text."""
    if not text:
        return ""
    clean = re.sub(r"<[^>]+>", " ", text)
    clean = re.sub(r"\s+", " ", clean).strip()
    return clean


def keyword_match(text, keyword):
    """Check if a keyword matches in text. Handles plain and regex-bounded keywords."""
    return keyword.lower() in text


def bounded_match(text_original, pattern):
    """Check if a word-boundary regex pattern matches in text (case-insensitive)."""
    return bool(re.search(pattern, text_original, re.IGNORECASE))


def score_article(title, summary, lang, source_category):
    """Score an article's relevance based on sector keywords and geographic proximity."""
    text_lower = f"{title} {summary}".lower()
    text_original = f"{title} {summary}"

    matched_sectors = []
    sector_score_total = 0

    for sector_id, sector in SECTORS.items():
        sector_score = 0

        # Standard keywords (substring match, case-insensitive)
        for kw in sector.get("keywords", []):
            if keyword_match(text_lower, kw):
                sector_score += 1

        # Bounded keywords (regex word-boundary match)
        for pattern in sector.get("keywords_bounded", []):
            if bounded_match(text_original, pattern):
                sector_score += 1

        if sector_score > 0:
            matched_sectors.append({
                "id": sector_id,
                "label": sector["label"],
                "score": sector_score
            })
            sector_score_total += sector_score

    # Geographic relevance check
    geo_score = 0
    for kw in GEO_KEYWORDS:
        if kw.lower() in text_lower:
            geo_score += 2
    for pattern in GEO_KEYWORDS_BOUNDED:
        if bounded_match(text_original, pattern):
            geo_score += 2

    # KEY FILTER:
    # - UAE sources: keep ALL articles (general context)
    # - Non-UAE sources with geo match: keep (UAE-related context from French/intl press)
    # - Non-UAE sources without geo match: DROP (no UAE connection = noise)
    if source_category != "uae" and geo_score == 0:
        return {
            "sectors": [],
            "bilateral_score": 0,
            "total_score": 0
        }

    # Base score: geo + sector. Minimum 1 for articles that pass the filter.
    total_score = max(sector_score_total + geo_score, 1)

    return {
        "sectors": matched_sectors,
        "bilateral_score": geo_score,
        "total_score": total_score
    }


def parse_date(entry):
    """Extract and normalize publication date from feed entry."""
    date_fields = ["published_parsed", "updated_parsed"]
    for field in date_fields:
        parsed = entry.get(field)
        if parsed:
            try:
                dt = datetime(*parsed[:6], tzinfo=timezone.utc)
                return dt.isoformat()
            except Exception:
                continue

    # Fallback: try string parsing
    for field in ["published", "updated"]:
        val = entry.get(field, "")
        if val:
            return val

    return datetime.now(timezone.utc).isoformat()


def fetch_feed(name, config):
    """Fetch and parse a single RSS feed."""
    print(f"  Fetching: {name}...")
    try:
        feed = feedparser.parse(config["url"])
        if feed.bozo and not feed.entries:
            print(f"  [WARN] {name}: Feed error - {feed.bozo_exception}")
            return []

        articles = []
        for entry in feed.entries[:30]:  # Limit per feed
            title = clean_html(entry.get("title", ""))
            summary = clean_html(entry.get("summary", entry.get("description", "")))
            link = entry.get("link", "")
            published = parse_date(entry)

            if not title:
                continue

            # Translate Arabic content
            original_title = title
            original_summary = summary
            if config["lang"] == "ar":
                title = translate_arabic(title)
                summary = translate_arabic(summary)

            # Score relevance
            scoring = score_article(title, summary, config["lang"], config["category"])

            # Only keep articles with some relevance
            if scoring["total_score"] == 0:
                continue

            article = {
                "id": compute_article_id(original_title, link),
                "title": title,
                "summary": summary[:500],
                "link": link,
                "source": name,
                "source_lang": config["lang"],
                "category": config["category"],
                "published": published,
                "sectors": scoring["sectors"],
                "bilateral_score": scoring["bilateral_score"],
                "relevance_score": scoring["total_score"],
            }

            # Keep original text for Arabic translations
            if config["lang"] == "ar":
                article["original_title"] = original_title
                article["original_summary"] = original_summary[:500]

            articles.append(article)

        print(f"  [OK] {name}: {len(articles)} relevant articles")
        return articles

    except Exception as e:
        print(f"  [ERROR] {name}: {e}")
        return []


def generate_digest():
    """Main function: fetch all feeds and generate a digest JSON file."""
    now = datetime.now(timezone.utc)
    cet = now + timedelta(hours=1)  # CET = UTC+1 (CEST = UTC+2 in summer)

    print(f"=== UAE-France Economic Monitor ===")
    print(f"Digest generation started: {cet.strftime('%Y-%m-%d %H:%M CET')}")
    print()

    all_articles = []

    for name, config in FEEDS.items():
        articles = fetch_feed(name, config)
        all_articles.extend(articles)

    # Deduplicate by ID
    seen = set()
    unique_articles = []
    for art in all_articles:
        if art["id"] not in seen:
            seen.add(art["id"])
            unique_articles.append(art)

    # Sort by relevance score (highest first)
    unique_articles.sort(key=lambda x: x["relevance_score"], reverse=True)

    # Build digest
    digest = {
        "generated_at": now.isoformat(),
        "generated_at_cet": cet.strftime("%Y-%m-%d %H:%M"),
        "total_articles": len(unique_articles),
        "sources_fetched": len(FEEDS),
        "articles": unique_articles,
        "sector_summary": {}
    }

    # Sector summary
    for sector_id, sector in SECTORS.items():
        count = sum(
            1 for art in unique_articles
            if any(s["id"] == sector_id for s in art["sectors"])
        )
        digest["sector_summary"][sector_id] = {
            "label": sector["label"],
            "count": count
        }

    # Write digest files
    base_dir = Path(__file__).parent.parent / "docs" / "data"
    base_dir.mkdir(parents=True, exist_ok=True)
    digests_dir = base_dir / "digests"
    digests_dir.mkdir(parents=True, exist_ok=True)

    # Timestamped digest
    filename = f"digest_{now.strftime('%Y%m%d_%H%M')}.json"
    filepath = digests_dir / filename
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(digest, f, ensure_ascii=False, indent=2)
    print(f"\nDigest saved: {filepath}")

    # Latest digest (always overwritten)
    latest_path = base_dir / "latest.json"
    with open(latest_path, "w", encoding="utf-8") as f:
        json.dump(digest, f, ensure_ascii=False, indent=2)
    print(f"Latest digest: {latest_path}")

    # Update index of all digests
    digest_files = sorted(digests_dir.glob("digest_*.json"), reverse=True)
    index = {
        "digests": [
            {
                "filename": f.name,
                "date": f.name.replace("digest_", "").replace(".json", ""),
            }
            for f in digest_files[:60]  # Keep last 60 digests (~30 days)
        ]
    }
    index_path = base_dir / "index.json"
    with open(index_path, "w", encoding="utf-8") as f:
        json.dump(index, f, ensure_ascii=False, indent=2)
    print(f"Index updated: {index_path}")

    print(f"\n=== Done: {len(unique_articles)} articles across {len(FEEDS)} sources ===")
    return digest


if __name__ == "__main__":
    generate_digest()

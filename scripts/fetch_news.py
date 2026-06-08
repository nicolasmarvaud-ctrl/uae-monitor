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
        "keywords_en": [
            "energy", "oil", "gas", "petroleum", "ADNOC", "TAQA", "Masdar",
            "renewable", "solar", "wind", "hydrogen", "nuclear", "Barakah",
            "power plant", "grid", "electricity", "fuel", "LNG", "refinery",
            "carbon capture", "CCUS", "energy transition", "clean energy",
            "TotalEnergies", "Engie", "EDF", "Orano", "Technip"
        ],
        "keywords_fr": [
            "energie", "energies", "petrole", "gaz", "renouvelable", "solaire",
            "eolien", "hydrogene", "nucleaire", "transition energetique",
            "electricite", "carburant", "raffinerie", "capture carbone"
        ]
    },
    "ai_tech": {
        "label": "AI & New Technologies",
        "keywords_en": [
            "artificial intelligence", "AI", "machine learning", "deep learning",
            "technology", "tech", "digital", "cloud", "data center", "semiconductor",
            "chip", "robotics", "automation", "5G", "6G", "IoT", "blockchain",
            "quantum", "cybersecurity", "smart city", "G42", "Presight",
            "Abu Dhabi AI", "Technology Innovation Institute", "TII", "MBZUAI",
            "Falcon", "Atos", "Thales", "Dassault Systemes", "OVHcloud"
        ],
        "keywords_fr": [
            "intelligence artificielle", "IA", "technologie", "numerique",
            "digital", "cloud", "semi-conducteur", "puce", "robotique",
            "automatisation", "cybersecurite", "ville intelligente", "deeptech"
        ]
    },
    "climate": {
        "label": "Climate Transition",
        "keywords_en": [
            "climate", "carbon", "CO2", "emission", "net zero", "sustainability",
            "sustainable", "green", "ESG", "COP", "decarbonization",
            "circular economy", "waste management", "water desalination",
            "environment", "biodiversity", "pollution", "recycling"
        ],
        "keywords_fr": [
            "climat", "carbone", "emission", "neutralite carbone", "durabilite",
            "durable", "vert", "decarbonation", "economie circulaire",
            "gestion dechets", "dessalement", "environnement", "biodiversite"
        ]
    },
    "food_security": {
        "label": "Food Security",
        "keywords_en": [
            "food security", "agriculture", "agritech", "agri-tech", "farming",
            "vertical farm", "aquaculture", "food production", "food supply",
            "food tech", "foodtech", "irrigation", "crop", "livestock",
            "food import", "food self-sufficiency", "Al Dahra", "Agthia"
        ],
        "keywords_fr": [
            "securite alimentaire", "agriculture", "agritech", "agroalimentaire",
            "ferme verticale", "aquaculture", "production alimentaire",
            "irrigation", "elevage", "autosuffisance alimentaire"
        ]
    },
    "logistics": {
        "label": "Logistics",
        "keywords_en": [
            "logistics", "supply chain", "port", "shipping", "freight",
            "trade", "export", "import", "customs", "free zone", "free trade",
            "Jebel Ali", "DP World", "Etihad Rail", "Abu Dhabi Ports",
            "AD Ports", "COSCO", "warehouse", "distribution", "corridor",
            "maritime", "cargo", "CMA CGM", "Bollore"
        ],
        "keywords_fr": [
            "logistique", "chaine approvisionnement", "port", "transport maritime",
            "fret", "commerce", "exportation", "importation", "douane",
            "zone franche", "libre-echange", "entrepot", "distribution",
            "corridor", "maritime", "cargo"
        ]
    },
    "aeronautics": {
        "label": "Aeronautics",
        "keywords_en": [
            "aeronautics", "aerospace", "aviation", "aircraft", "airline",
            "Airbus", "Boeing", "Etihad", "Emirates", "flydubai",
            "Safran", "Thales", "Dassault Aviation", "MBDA", "defense",
            "defence", "military", "drone", "UAV", "air show", "Dubai Airshow",
            "airport", "MRO", "maintenance", "satellite launch", "rocket"
        ],
        "keywords_fr": [
            "aeronautique", "aerospatial", "aviation", "avion", "compagnie aerienne",
            "defense", "militaire", "drone", "salon aeronautique", "aeroport",
            "maintenance aeronautique", "satellite"
        ]
    },
    "space": {
        "label": "Space",
        "keywords_en": [
            "space", "satellite", "orbit", "launch", "rocket", "Mars",
            "Moon", "lunar", "space agency", "UAE Space Agency", "MBRSC",
            "Hope probe", "astronaut", "space station", "space tech",
            "earth observation", "CNES", "Arianespace", "ArianeGroup", "Thales Alenia"
        ],
        "keywords_fr": [
            "espace", "spatial", "satellite", "orbite", "lancement", "fusee",
            "Mars", "Lune", "lunaire", "agence spatiale", "sonde",
            "astronaute", "station spatiale", "observation terrestre"
        ]
    },
    "fintech": {
        "label": "Fintech",
        "keywords_en": [
            "fintech", "financial technology", "digital bank", "neobank",
            "payment", "crypto", "cryptocurrency", "bitcoin", "stablecoin",
            "CBDC", "digital currency", "insurtech", "regtech", "wealthtech",
            "ADGM", "DIFC", "sandbox", "Abu Dhabi Global Market",
            "Dubai International Financial Centre", "First Abu Dhabi Bank", "FAB",
            "BNP Paribas", "Societe Generale", "Amundi"
        ],
        "keywords_fr": [
            "fintech", "banque digitale", "paiement", "crypto", "cryptomonnaie",
            "monnaie numerique", "assurtech", "finance numerique",
            "banque numerique", "technologie financiere"
        ]
    },
    "health": {
        "label": "Health",
        "keywords_en": [
            "health", "healthcare", "hospital", "pharma", "pharmaceutical",
            "biotech", "biotechnology", "medical", "medtech", "life sciences",
            "clinical trial", "vaccine", "genomics", "telemedicine",
            "Abu Dhabi Health", "DHA", "SEHA", "Mubadala Health",
            "Sanofi", "Servier", "bioMerieux", "Essilor"
        ],
        "keywords_fr": [
            "sante", "hopital", "pharmaceutique", "biotech", "biotechnologie",
            "medical", "medtech", "sciences de la vie", "essai clinique",
            "vaccin", "genomique", "telemedecine", "dispositif medical"
        ]
    }
}

# Geographic / bilateral keywords — articles from non-UAE sources MUST match at least one
GEO_KEYWORDS = [
    # UAE country
    "UAE", "United Arab Emirates", "Emirats", "Emirats Arabes Unis", "EAU",
    "emirien", "emiriens", "emirati", "emiratis",
    # Emirates / cities
    "Abu Dhabi", "Dubai", "Sharjah", "Ajman", "Fujairah", "Ras Al Khaimah",
    "Umm Al Quwain", "Al Ain", "Khalifa City", "Saadiyat", "Yas Island",
    # Gulf region
    "Gulf", "Golfe", "GCC", "CCEAG", "Moyen-Orient", "Middle East",
    "Arabian", "peninsule arabique", "Arab Gulf",
    # Key UAE entities
    "Mubadala", "ADIA", "ADQ", "ADIO", "ICD", "TAQA", "ADNOC", "Masdar",
    "Etihad", "Emirates", "DP World", "AD Ports", "G42", "EDGE Group",
    "Emaar", "Aldar", "First Abu Dhabi Bank", "FAB", "DIFC", "ADGM",
    "DMCC", "Jafza", "Jebel Ali", "MBZUAI", "TII",
    "Abu Dhabi Investment", "Dubai Holding", "Dubai Future",
    # France-UAE bilateral
    "franco-emirien", "franco-emirati", "France-EAU", "France-UAE",
    "Business France", "BPI France", "Bpifrance", "MEDEF International",
    "Choose France", "ambassade", "embassy",
    # French companies with major UAE presence
    "TotalEnergies", "Engie", "EDF", "Thales", "Airbus", "Safran",
    "Dassault", "Naval Group", "CMA CGM", "Veolia", "Suez",
    "BNP Paribas", "Societe Generale", "Amundi", "AXA",
    "Sanofi", "Atos", "Capgemini", "Schneider Electric"
]

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
    "WAM English": {
        "url": "https://www.wam.ae/en/rss/all",
        "lang": "en",
        "category": "uae"
    },
    "The National Business": {
        "url": "https://www.thenationalnews.com/business/rss",
        "lang": "en",
        "category": "uae"
    },
    "Gulf News Business": {
        "url": "https://gulfnews.com/business/rss",
        "lang": "en",
        "category": "uae"
    },
    "Zawya": {
        "url": "https://www.zawya.com/en/rss-feed.xml",
        "lang": "en",
        "category": "uae"
    },
    "Arabian Business": {
        "url": "https://www.arabianbusiness.com/rss",
        "lang": "en",
        "category": "uae"
    },
    "Khaleej Times Business": {
        "url": "https://www.khaleejtimes.com/rss/business",
        "lang": "en",
        "category": "uae"
    },

    # --- UAE Sources (Arabic - will be translated) ---
    "WAM Arabic": {
        "url": "https://www.wam.ae/ar/rss/all",
        "lang": "ar",
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


def score_article(title, summary, lang, source_category):
    """Score an article's relevance based on sector keywords and geographic proximity."""
    text = f"{title} {summary}".lower()

    matched_sectors = []
    sector_score_total = 0

    for sector_id, sector in SECTORS.items():
        sector_score = 0
        if lang == "fr":
            keywords = sector["keywords_fr"] + sector["keywords_en"]
        else:
            keywords = sector["keywords_en"]

        for kw in keywords:
            if kw.lower() in text:
                sector_score += 1

        if sector_score > 0:
            matched_sectors.append({
                "id": sector_id,
                "label": sector["label"],
                "score": sector_score
            })
            sector_score_total += sector_score

    # Geographic / bilateral relevance
    geo_score = 0
    for kw in GEO_KEYWORDS:
        if kw.lower() in text:
            geo_score += 2

    # KEY FILTER: For non-UAE sources, require geographic relevance
    # UAE-native sources (WAM, Gulf News, etc.) are inherently about the UAE
    if source_category != "uae" and geo_score == 0:
        return {
            "sectors": [],
            "bilateral_score": 0,
            "total_score": 0
        }

    total_score = sector_score_total + geo_score

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

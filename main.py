from pathlib import Path
from typing import Optional
import json
import re

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel


# =========================================================
# PATHS
# =========================================================

BASE = Path(__file__).resolve().parent
DATA = BASE / "data"


# =========================================================
# FASTAPI APP
# =========================================================

app = FastAPI(
    title="IP-SAKTI Sahayak API",
    version="1.2.0"
)


# =========================================================
# CORS
# =========================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =========================================================
# JSON LOADER
# =========================================================

def load_json(name):

    file_path = DATA / name

    with open(
        file_path,
        "r",
        encoding="utf-8"
    ) as f:
        return json.load(f)


# =========================================================
# DATA
# =========================================================

KNOWLEDGE = load_json("knowledge.json")
SOURCES = load_json("sources.json")
INGREDIENTS = load_json("ingredients.json")


# =========================================================
# REQUEST MODELS
# =========================================================

class AskRequest(BaseModel):

    question: str = ""
    jurisdiction: str = "India"
    language: str = "English"


class IPRequest(BaseModel):

    name: str = ""
    description: str = ""
    novelty: str = ""
    traditional_knowledge: str = "No / Unknown"
    similar_product: str = "Unknown"
    jurisdiction: str = "India"
    language: str = "English"


class FormulationRequest(BaseModel):

    name: str = ""
    formulation_name: str = ""
    dosage_form: str = ""
    ingredients: str = ""
    intended_use: str = ""
    novelty: str = "Unknown"
    jurisdiction: str = "India"
    language: str = "English"


class RegulatoryRequest(BaseModel):

    category: str = ""
    jurisdiction: str = "India"
    description: str = ""
    language: str = "English"


# =========================================================
# LANGUAGE HELPERS
# =========================================================

def is_hindi(language: str) -> bool:

    value = str(
        language or ""
    ).lower()

    return (
        "hindi" in value
        or "हिन्दी" in value
        or "हिंदी" in value
    )


# =========================================================
# SOURCE HELPERS
# =========================================================

def source_record(item):

    return {
        "title": (
            item.get("source")
            or item.get("title")
            or ""
        ),

        "authority": item.get(
            "authority",
            ""
        ),

        "version": item.get(
            "version",
            item.get(
                "effective_date",
                "Not specified"
            )
        ),

        "relevance": item.get(
            "summary",
            item.get(
                "description",
                ""
            )
        ),

        "url": item.get(
            "url",
            ""
        )
    }


def source_text(item):

    return (
        str(item.get("title", "")) + " " +
        str(item.get("source", "")) + " " +
        str(item.get("authority", "")) + " " +
        str(item.get("summary", "")) + " " +
        str(item.get("description", ""))
    ).lower()


def jurisdiction_sources(jurisdiction: str):

    value = str(
        jurisdiction or "India"
    ).lower().strip()


    # -----------------------------------------------------
    # INDIA
    # -----------------------------------------------------

    if value == "india":

        india_sources = [
            item
            for item in SOURCES
            if (
                "india" in source_text(item)
                or "ayush" in source_text(item)
                or "ip india" in source_text(item)
                or "ccras" in source_text(item)
                or "traditional knowledge digital library"
                in source_text(item)
            )
        ]

        if india_sources:
            return india_sources

        return SOURCES[:5]


    # -----------------------------------------------------
    # INTERNATIONAL
    # -----------------------------------------------------

    international_words = [
        "international",
        "wipo",
        "patentscope",
        "united states",
        "usa",
        "europe",
        "european",
        "eu",
        "pct"
    ]


    international_sources = [
        item
        for item in SOURCES
        if any(
            word in source_text(item)
            for word in international_words
        )
    ]


    if international_sources:
        return international_sources

    return SOURCES[:5]


# =========================================================
# HEALTH CHECK
# =========================================================

@app.get("/health")
def health():

    return {
        "status": "ok",
        "service": "IP-SAKTI Sahayak",
        "version": "1.2.0"
    }


# =========================================================
# KNOWLEDGE RETRIEVAL
# =========================================================

def retrieve(
    question: str,
    jurisdiction: str
):

    terms = set(
        re.findall(
            r"[a-zA-Z]{3,}",
            str(question).lower()
        )
    )

    scored = []


    for item in KNOWLEDGE:

        text = (
            str(item.get("title", "")) + " " +
            str(item.get("summary", "")) + " " +
            str(item.get("category", "")) + " " +
            str(item.get("description", ""))
        ).lower()


        score = sum(
            1
            for term in terms
            if term in text
        )


        if (
            str(jurisdiction or "").lower()
            in text
        ):

            score += 2


        if score > 0:

            scored.append(
                (
                    score,
                    item
                )
            )


    scored.sort(
        key=lambda x: x[0],
        reverse=True
    )


    return [
        item
        for score, item in scored[:4]
    ]


# =========================================================
# ASK SAHAYAK
# =========================================================

@app.post("/ask")
def ask(req: AskRequest):

    question = (
        req.question or ""
    ).strip()

    hindi = is_hindi(
        req.language
    )


    if not question:

        return {
            "answer": (
                "कृपया अपना प्रश्न दर्ज करें।"
                if hindi
                else
                "Please provide a question."
            ),

            "confidence": "Low",

            "next_steps": [],

            "sources": [],

            "disclaimer": (
                "केवल प्रारंभिक सूचना आधारित मार्गदर्शन।"
                if hindi
                else
                "Informational guidance only."
            )
        }


    hits = retrieve(
        question,
        req.jurisdiction
    )

    lower = question.lower()


    # -----------------------------------------------------
    # NO MATCH
    # -----------------------------------------------------

    if not hits:

        if hindi:

            answer = (
                "वर्तमान curated knowledge base में पर्याप्त "
                "matching evidence नहीं मिला। सिस्टम अनुमान "
                "लगाने के बजाय abstain कर रहा है।"
            )

            steps = [
                "Product category और jurisdiction स्पष्ट करें।",
                "Specific IP या regulatory issue बताएं।",
                "Case-specific assessment के लिए qualified professional से सलाह लें।"
            ]

        else:

            answer = (
                "I could not find sufficient matching evidence "
                "in the current curated prototype knowledge base. "
                "The system is abstaining rather than inventing an answer."
            )

            steps = [
                "Specify the product category and jurisdiction.",
                "Specify the exact IP or regulatory issue.",
                "Seek qualified professional assessment for a case-specific matter."
            ]


        return {
            "answer": answer,
            "confidence": "Low",
            "next_steps": steps,
            "sources": [],
            "disclaimer": (
                "सीमित curated knowledge base का उपयोग किया गया है।"
                if hindi
                else
                "The prototype uses a limited curated knowledge base."
            )
        }


    # -----------------------------------------------------
    # PATENT
    # -----------------------------------------------------

    if (
        "patent" in lower
        or "patentable" in lower
        or "novel" in lower
        or "prior art" in lower
    ):

        if hindi:

            answer = (
                "प्रारंभिक patentability review में यह देखना "
                "आवश्यक है कि formulation या process में क्या "
                "तकनीकी रूप से नया है। इसके बाद patent और "
                "non-patent prior art तथा Traditional Knowledge "
                "sources की जाँच करनी चाहिए।"
            )

            steps = [
                "Novel technical features स्पष्ट करें।",
                "Patent और non-patent prior art search करें।",
                "Relevant Traditional Knowledge sources जाँचें।",
                "Filing से पहले professional patentability opinion लें।"
            ]

        else:

            answer = (
                "For a preliminary patentability review, identify "
                "what is technically new in the formulation or process. "
                "Then review patent, non-patent prior art and relevant "
                "traditional-knowledge sources."
            )

            steps = [
                "Define the novel technical features.",
                "Search patent and non-patent prior art.",
                "Review relevant traditional-knowledge sources.",
                "Obtain a professional patentability opinion before filing."
            ]


    # -----------------------------------------------------
    # TRADEMARK
    # -----------------------------------------------------

    elif (
        "trademark" in lower
        or "brand" in lower
        or "logo" in lower
    ):

        if hindi:

            answer = (
                "Trademark protection मुख्य रूप से distinctive "
                "brand name, identifier या logo से संबंधित है। "
                "Filing से पहले clearance search और appropriate "
                "class selection आवश्यक है।"
            )

            steps = [
                "Proposed brand name या mark define करें।",
                "Trademark clearance search करें।",
                "Appropriate class और jurisdiction चुनें।",
                "Applicable procedure के अनुसार filing करें।"
            ]

        else:

            answer = (
                "Trademark protection primarily concerns a distinctive "
                "brand name, identifier or logo. A clearance search and "
                "appropriate class selection should be completed before filing."
            )

            steps = [
                "Define the proposed brand name or mark.",
                "Conduct a trademark clearance search.",
                "Select the appropriate class and jurisdiction.",
                "File according to the applicable procedure."
            ]


    # -----------------------------------------------------
    # TRADITIONAL KNOWLEDGE / ABS
    # -----------------------------------------------------

    elif (
        "traditional knowledge" in lower
        or "biological resource" in lower
        or "biological" in lower
        or "abs" in lower
        or "nagoya" in lower
    ):

        if hindi:

            answer = (
                "यदि innovation में biological resources या "
                "associated Traditional Knowledge का उपयोग है, "
                "तो provenance, access और applicable "
                "access-and-benefit-sharing requirements की जाँच करें।"
            )

            steps = [
                "Biological resource का origin record करें।",
                "Associated Traditional Knowledge identify करें।",
                "Applicable ABS framework check करें।",
                "Permissions या benefit-sharing लागू होने पर specialist advice लें।"
            ]

        else:

            answer = (
                "If an innovation uses biological resources or "
                "associated traditional knowledge, review provenance, "
                "access and any applicable access-and-benefit-sharing requirements."
            )

            steps = [
                "Record the origin of the biological resource.",
                "Identify associated traditional knowledge.",
                "Check the applicable ABS framework.",
                "Seek specialist advice if permissions or benefit-sharing may apply."
            ]


    # -----------------------------------------------------
    # REGULATORY
    # -----------------------------------------------------

    elif (
        "regulat" in lower
        or "medicine" in lower
        or "drug" in lower
        or "cosmetic" in lower
        or "nutraceutical" in lower
        or "supplement" in lower
    ):

        if hindi:

            answer = (
                "Regulatory requirements product classification, "
                "ingredients, dosage form और intended use पर निर्भर "
                "करते हैं। पहले product category निर्धारित करें और "
                "फिर applicable authority तथा current requirements map करें।"
            )

            steps = [
                "Formulation और intended use record करें।",
                "Product classification निर्धारित करें।",
                "Competent authority identify करें।",
                "Current evidence, labeling और documentation requirements check करें।"
            ]

        else:

            answer = (
                "Regulatory requirements depend on product classification, "
                "ingredients, dosage form and intended use. First determine "
                "the product category and then map the applicable authority "
                "and current requirements."
            )

            steps = [
                "Record the formulation and intended use.",
                "Determine the product classification.",
                "Identify the competent authority.",
                "Check current evidence, labeling and documentation requirements."
            ]


    # -----------------------------------------------------
    # GENERAL
    # -----------------------------------------------------

    else:

        if hindi:

            answer = (
                "इस प्रश्न के लिए पहले jurisdiction, product category "
                "और applicable IP/regulatory framework identify करना "
                "उचित होगा। नीचे दिए गए cited knowledge items आगे की "
                "analysis के लिए starting evidence देते हैं।"
            )

            steps = [
                "Jurisdiction specify करें।",
                "Product या formulation category specify करें।",
                "Cited sources review करें।",
                "Evidence insufficient होने पर qualified professional से सलाह लें।"
            ]

        else:

            answer = (
                "This question should first be approached by identifying "
                "the jurisdiction, product category and applicable "
                "IP/regulatory framework. The cited knowledge items provide "
                "starting evidence for further analysis."
            )

            steps = [
                "Specify the jurisdiction.",
                "Specify the product or formulation category.",
                "Review the cited sources.",
                "Seek qualified professional assessment if evidence is insufficient."
            ]


    selected_sources = jurisdiction_sources(
        req.jurisdiction
    )


    return {
        "answer": answer,

        "confidence": "Medium",

        "next_steps": steps,

        "sources": [
            source_record(item)
            for item in (
                hits
                if hits
                else selected_sources[:4]
            )
        ],

        "disclaimer": (
            "प्रारंभिक सूचना आधारित मार्गदर्शन; यह legal advice, "
            "regulatory approval, certification या final determination नहीं है।"
            if hindi
            else
            "Preliminary informational guidance only; not legal advice, "
            "regulatory approval, certification or a final determination."
        )
    }


# =========================================================
# INGREDIENT MATCHING
# =========================================================

def match_ingredients(raw_text: str):

    text = str(
        raw_text or ""
    ).lower()

    matches = []


    for item in INGREDIENTS:

        keywords = item.get(
            "keywords",
            []
        )

        name = str(
            item.get("name", "")
        )

        aliases = item.get(
            "aliases",
            []
        )

        search_terms = (
            [name]
            + keywords
            + aliases
        )

        found = False


        for keyword in search_terms:

            keyword = str(
                keyword or ""
            ).strip().lower()

            if keyword and keyword in text:

                found = True
                break


        if found:

            matches.append(item)


    return matches


# =========================================================
# INGREDIENTS API
# =========================================================

@app.get("/ingredients")
def ingredients(
    q: Optional[str] = None
):

    # -----------------------------------------------------
    # Return complete ingredient catalogue
    # -----------------------------------------------------

    if not q:

        return {
            "items": INGREDIENTS,
            "ingredients": INGREDIENTS
        }


    # -----------------------------------------------------
    # Search ingredients
    # -----------------------------------------------------

    query = str(
        q or ""
    ).strip().lower()


    if not query:

        return {
            "items": [],
            "ingredients": []
        }


    results = []


    for item in INGREDIENTS:

        searchable = " ".join([
            str(item.get("name", "")),
            " ".join(
                map(
                    str,
                    item.get(
                        "aliases",
                        []
                    )
                )
            ),
            " ".join(
                map(
                    str,
                    item.get(
                        "keywords",
                        []
                    )
                )
            )
        ]).lower()


        if query in searchable:

            results.append(item)


    return {
        "items": results,
        "ingredients": results
    }


# =========================================================
# FORMULATION HELPERS
# =========================================================

def formulation_name(req: FormulationRequest):

    return (
        req.name.strip()
        or req.formulation_name.strip()
        or "Unnamed formulation"
    )


def contains_any(
    text: str,
    words
):

    value = str(
        text or ""
    ).lower()

    return any(
        word.lower() in value
        for word in words
    )


def ingredient_notes(
    matched,
    hindi=False
):

    notes = []


    for item in matched:

        notes.append({

            "name":
                item.get(
                    "name",
                    ""
                ),

            "part_used":
                item.get(
                    "part_used",
                    ""
                ),

            "aliases":
                item.get(
                    "aliases",
                    []
                ),

            "traditional_context":
                item.get(
                    "traditional_context",
                    ""
                ),

            "ip_flag":
                item.get(
                    "ip_flag",
                    ""
                ),

            "abs_flag":
                item.get(
                    "abs_flag",
                    ""
                ),

            "regulatory_flag":
                item.get(
                    "regulatory_flag",
                    ""
                ),

            "common_forms":
                item.get(
                    "common_forms",
                    []
                )
        })


    return notes


# =========================================================
# FORMULATION CATEGORY
# =========================================================

def classify_formulation_category(
    text_all: str,
    novelty: str,
    hindi=False
):

    text = str(
        text_all or ""
    ).lower()

    novelty_text = str(
        novelty or ""
    ).lower()


    # -----------------------------------------------------
    # COSMETIC
    # -----------------------------------------------------

    if contains_any(
        text,
        [
            "cosmetic",
            "cream",
            "skin",
            "shampoo",
            "soap",
            "face wash",
            "hair oil"
        ]
    ):

        category = (
            "कॉस्मेटिक"
            if hindi
            else
            "Cosmetic"
        )

        regulatory = (
            "Cosmetic classification, safety, labeling "
            "और manufacturing requirements verify करें।"
            if hindi
            else
            "Confirm cosmetic classification and applicable "
            "safety, labeling and manufacturing requirements."
        )

        return category, regulatory


    # -----------------------------------------------------
    # FOOD / NUTRACEUTICAL
    # -----------------------------------------------------

    if contains_any(
        text,
        [
            "nutraceutical",
            "food",
            "nutrition",
            "beverage",
            "supplement",
            "aahar",
            "health drink"
        ]
    ):

        category = (
            "आयुर्वेद-आहार / न्यूट्रास्यूटिकल"
            if hindi
            else
            "Ayurveda-Aahar / Nutraceutical"
        )

        regulatory = (
            "Food/nutraceutical classification, permitted "
            "ingredients, claims और labeling requirements "
            "verify करें।"
            if hindi
            else
            "Confirm food/nutraceutical classification, "
            "permitted ingredients, claims and labeling requirements."
        )

        return category, regulatory


    # -----------------------------------------------------
    # NEW DRUG
    # -----------------------------------------------------

    if contains_any(
        text,
        [
            "new drug",
            "clinical trial",
            "clinical",
            "novel drug"
        ]
    ):

        category = (
            "नई / गैर-शास्त्रीय औषधि"
            if hindi
            else
            "New / Non-classical Drug"
        )

        regulatory = (
            "New/non-classical medicinal product के लिए "
            "additional evidence और approval steps की "
            "आवश्यकता हो सकती है। Current competent-authority "
            "pathway verify करें।"
            if hindi
            else
            "A new/non-classical medicinal product may require "
            "additional evidence and approval steps. Confirm "
            "the current competent-authority pathway."
        )

        return category, regulatory


    # -----------------------------------------------------
    # PHYTOPHARMACEUTICAL
    # -----------------------------------------------------

    if "phytopharma" in text:

        category = (
            "फाइटोफार्मास्यूटिकल"
            if hindi
            else
            "Phytopharmaceutical"
        )

        regulatory = (
            "Phytopharmaceutical-specific requirements और "
            "evidence pathway competent authority के साथ "
            "verify करें।"
            if hindi
            else
            "Confirm phytopharmaceutical-specific requirements "
            "and the evidence pathway with the competent authority."
        )

        return category, regulatory


    # -----------------------------------------------------
    # PROPRIETARY
    # -----------------------------------------------------

    if (
        novelty_text.startswith("novel")
        or "proprietary" in text
        or "proprietary medicine" in text
    ):

        category = (
            "प्रोप्राइटरी मेडिसिन"
            if hindi
            else
            "Proprietary Medicine"
        )

        regulatory = (
            "Proprietary-medicine route और current "
            "manufacturing, evidence तथा licensing "
            "requirements verify करें।"
            if hindi
            else
            "Confirm the proprietary-medicine route and "
            "current manufacturing, evidence and licensing requirements."
        )

        return category, regulatory


    # -----------------------------------------------------
    # DEFAULT
    # -----------------------------------------------------

    category = (
        "शास्त्रीय / सामान्य औषधि"
        if hindi
        else
        "Classical / Generic Medicine"
    )

    regulatory = (
        "Verify करें कि formulation और intended use "
        "applicable classical/generic medicine pathway "
        "में आते हैं या नहीं।"
        if hindi
        else
        "Confirm whether the formulation and intended use "
        "fall within the applicable classical/generic medicine pathway."
    )

    return category, regulatory


# =========================================================
# FORMULATION IP ROUTES
# =========================================================

def get_ip_routes(
    matched,
    novelty,
    ingredients,
    hindi=False
):

    routes = []


    if (
        str(novelty or "").strip()
        and str(novelty).lower()
        not in [
            "unknown",
            "no",
            "none",
            "not sure"
        ]
    ):

        routes.append(
            "पेटेंट"
            if hindi
            else
            "Patent"
        )

    else:

        routes.append(
            "पेटेंट"
            if hindi
            else
            "Patent"
        )


    routes.append(
        "ट्रेडमार्क"
        if hindi
        else
        "Trademark"
    )


    routes.append(
        "ट्रेड सीक्रेट"
        if hindi
        else
        "Trade Secret"
    )


    routes.append(
        "डिज़ाइन"
        if hindi
        else
        "Design"
    )


    unique_routes = []


    for route in routes:

        if route not in unique_routes:

            unique_routes.append(route)


    return unique_routes


# =========================================================
# PRELIMINARY INDICATOR
# =========================================================

def get_preliminary_indicator(
    matched,
    novelty,
    ingredients,
    hindi=False
):

    novelty_text = str(
        novelty or ""
    ).strip().lower()


    if matched:

        if (
            novelty_text
            and novelty_text not in [
                "unknown",
                "no",
                "none",
                "not sure"
            ]
        ):

            indicator = (
                "ज्ञात ingredients के साथ संभावित नया "
                "technical contribution बताया गया है; "
                "detailed prior-art review आवश्यक है।"
                if hindi
                else
                "Known ingredients are combined with a stated "
                "potentially new technical contribution; detailed "
                "prior-art review is required."
            )

        else:

            indicator = (
                "ज्ञात ingredients detect हुए हैं; "
                "novelty establish करने के लिए detailed "
                "prior-art review आवश्यक है।"
                if hindi
                else
                "Known ingredients were detected; detailed "
                "prior-art review is required before establishing novelty."
            )


        return indicator


    return (
        "Prototype database में कोई known ingredient match "
        "नहीं मिला; यह novelty का proof नहीं है और prior-art "
        "search आवश्यक है।"
        if hindi
        else
        "No known ingredient match was found in the prototype "
        "database; this does not prove novelty and a prior-art "
        "search is still required."
    )


# =========================================================
# ATTENTION LEVEL
# =========================================================

def get_attention_level(
    matched,
    novelty,
    ingredients
):

    novelty_text = str(
        novelty or ""
    ).lower()


    if (
        len(matched) >= 2
        and novelty_text not in [
            "",
            "unknown",
            "no",
            "none",
            "not sure"
        ]
    ):

        return "High"


    if len(matched) >= 2:

        return "High"


    if len(matched) == 1:

        return "Medium"


    return "Medium"


# =========================================================
# FORMULATION EXPLANATION
# =========================================================

def get_formulation_explanation(
    category,
    matched,
    novelty,
    jurisdiction,
    hindi=False
):

    if hindi:

        explanation = (
            f"यह प्रारंभिक screening {category} category, "
            f"detected ingredient knowledge और दिए गए formulation "
            f"details पर आधारित है। Jurisdiction: {jurisdiction}. "
        )

        if matched:

            explanation += (
                f"System ने {len(matched)} known ingredient"
                f"{'s' if len(matched) != 1 else ''} detect "
                "किए हैं। Known ingredients अपने-आप में novel "
                "patentable invention सिद्ध नहीं करते।"
            )

        else:

            explanation += (
                "Prototype ingredient database में कोई confident "
                "match नहीं मिला। इसका अर्थ यह नहीं है कि formulation "
                "नई या patentable है।"
            )

        return explanation


    explanation = (
        f"This preliminary screening uses the {category} category, "
        f"detected ingredient knowledge and the submitted formulation "
        f"details. Jurisdiction: {jurisdiction}. "
    )


    if matched:

        explanation += (
            f"The system detected {len(matched)} known ingredient"
            f"{'s' if len(matched) != 1 else ''}. "
            "Known ingredients alone do not establish a novel or "
            "patentable invention."
        )

    else:

        explanation += (
            "No confident match was found in the prototype ingredient "
            "database. This does not mean that the formulation is novel "
            "or patentable."
        )


    return explanation


# =========================================================
# FORMULATION CLASSIFIER
# =========================================================

@app.post("/classify")
def classify(req: FormulationRequest):

    # -----------------------------------------------------
    # BASIC INPUT
    # -----------------------------------------------------

    name = formulation_name(req)

    ingredients_text = str(
        req.ingredients or ""
    ).strip()

    dosage_form = str(
        req.dosage_form or ""
    ).strip()

    intended_use = str(
        req.intended_use or ""
    ).strip()

    novelty = str(
        req.novelty or "Unknown"
    ).strip()

    jurisdiction = str(
        req.jurisdiction or "India"
    ).strip()

    hindi = is_hindi(
        req.language
    )


    # -----------------------------------------------------
    # COMBINED TEXT
    # -----------------------------------------------------

    text_all = " ".join([
        name,
        dosage_form,
        ingredients_text,
        intended_use
    ]).lower()


    # -----------------------------------------------------
    # MATCH INGREDIENTS
    # -----------------------------------------------------

    matched = match_ingredients(
        text_all
    )


    ingredient_data = ingredient_notes(
        matched,
        hindi
    )


    # -----------------------------------------------------
    # FORMULATION CATEGORY
    # -----------------------------------------------------

    category, regulatory = (
        classify_formulation_category(
            text_all,
            novelty,
            hindi
        )
    )


    # -----------------------------------------------------
    # PRELIMINARY INDICATOR
    # -----------------------------------------------------

    preliminary_indicator = (
        get_preliminary_indicator(
            matched,
            novelty,
            ingredients_text,
            hindi
        )
    )


    # -----------------------------------------------------
    # ATTENTION LEVEL
    # -----------------------------------------------------

    attention_level = (
        get_attention_level(
            matched,
            novelty,
            ingredients_text
        )
    )


    # -----------------------------------------------------
    # POSSIBLE IP ROUTES
    # -----------------------------------------------------

    possible_ip_routes = (
        get_ip_routes(
            matched,
            novelty,
            ingredients_text,
            hindi
        )
    )


    # -----------------------------------------------------
    # EXPLANATION
    # -----------------------------------------------------

    explanation = (
        get_formulation_explanation(
            category,
            matched,
            novelty,
            jurisdiction,
            hindi
        )
    )


    # -----------------------------------------------------
    # NEXT STEPS
    # -----------------------------------------------------

    if hindi:

        next_steps = [

            "Formulation की ingredients, composition और dosage details verify करें।",

            "Detected ingredients के Traditional Knowledge और prior-art status को review करें।",

            "Patent और non-patent prior-art search करें।",

            "यदि formulation या process में नया technical contribution है, तो detailed patentability assessment कराएँ।",

            regulatory,

            "Commercial launch या IP filing से पहले qualified IP/regulatory professional से सलाह लें।"
        ]

    else:

        next_steps = [

            "Verify the formulation ingredients, composition and dosage details.",

            "Review the Traditional Knowledge and prior-art status of detected ingredients.",

            "Conduct patent and non-patent prior-art searches.",

            "If the formulation or process contains a new technical contribution, obtain a detailed patentability assessment.",

            regulatory,

            "Before commercial launch or IP filing, consult a qualified IP/regulatory professional."
        ]


    # -----------------------------------------------------
    # EXTRA INGREDIENT WARNINGS
    # -----------------------------------------------------

    warnings = []


    for item in matched:

        ip_flag = str(
            item.get(
                "ip_flag",
                ""
            )
        ).strip()


        abs_flag = str(
            item.get(
                "abs_flag",
                ""
            )
        ).strip()


        regulatory_flag = str(
            item.get(
                "regulatory_flag",
                ""
            )
        ).strip()


        if ip_flag:

            warnings.append(
                ip_flag
            )


        if abs_flag:

            warnings.append(
                abs_flag
            )


        if regulatory_flag:

            warnings.append(
                regulatory_flag
            )


    # Remove duplicate warnings

    unique_warnings = []


    for warning in warnings:

        if warning not in unique_warnings:

            unique_warnings.append(
                warning
            )


    # -----------------------------------------------------
    # JURISDICTION SOURCES
    # -----------------------------------------------------

    selected_sources = (
        jurisdiction_sources(
            jurisdiction
        )
    )


    formatted_sources = [

        source_record(item)

        for item in selected_sources[:5]

    ]


    # -----------------------------------------------------
    # IMPORTANT DISCLAIMER
    # -----------------------------------------------------

    if hindi:

        disclaimer = (
            "प्रारंभिक सूचना आधारित guidance only। "
            "यह legal advice, regulatory approval, certification "
            "या final patentability determination नहीं है। "
            "Final decision के लिए applicable official sources "
            "और qualified professional assessment आवश्यक है।"
        )

    else:

        disclaimer = (
            "Preliminary informational guidance only. "
            "This is not legal advice, regulatory approval, "
            "certification or a final patentability determination. "
            "Final decisions should be based on applicable official "
            "sources and qualified professional assessment."
        )


    # -----------------------------------------------------
    # FINAL FORMULATION RESPONSE
    # -----------------------------------------------------

    return {

        "formulation_name":
            name,

        "dosage_form":
            dosage_form,

        "intended_use":
            intended_use,

        "jurisdiction":
            jurisdiction,

        "category":
            category,

        "preliminary_indicator":
            preliminary_indicator,

        "attention_level":
            attention_level,

        "confidence":
            "Medium",

        "summary":
            explanation,

        "analysis":
            explanation,

        "regulatory":
            regulatory,

        "matched_ingredients":
            ingredient_data,

        "possible_ip_routes":
            possible_ip_routes,

        "next_steps":
            next_steps,

        "warnings":
            unique_warnings,

        "sources":
            formatted_sources,

        "warning":
            disclaimer,

        "disclaimer":
            disclaimer
    }


# =========================================================
# IP CHECKER
# =========================================================

@app.post("/ip-check")
def ip_check(req: IPRequest):

    hindi = is_hindi(
        req.language
    )


    name = str(
        req.name or ""
    ).strip()

    description = str(
        req.description or ""
    ).strip()

    novelty = str(
        req.novelty or ""
    ).strip()

    traditional_knowledge = str(
        req.traditional_knowledge or ""
    ).strip()

    similar_product = str(
        req.similar_product or ""
    ).strip()

    jurisdiction = str(
        req.jurisdiction or "India"
    ).strip()


    combined_text = " ".join([
        name,
        description,
        novelty
    ]).lower()


    # -----------------------------------------------------
    # BASIC RISK FLAGS
    # -----------------------------------------------------

    flags = []


    if traditional_knowledge.lower() in [
        "yes",
        "unknown",
        "yes / unknown"
    ]:

        flags.append(
            "Traditional Knowledge review required."
        )


    if similar_product.lower() in [
        "yes",
        "unknown"
    ]:

        flags.append(
            "Prior-art or similar-product search recommended."
        )


    if not novelty:

        flags.append(
            "Novelty information is incomplete."
        )


    # -----------------------------------------------------
    # INDICATOR
    # -----------------------------------------------------

    if (
        traditional_knowledge.lower()
        in [
            "yes",
            "unknown",
            "yes / unknown"
        ]
        or similar_product.lower()
        in [
            "yes",
            "unknown"
        ]
    ):

        indicator = (
            "अधिक साक्ष्य की आवश्यकता है"
            if hindi
            else
            "More evidence needed"
        )

        attention = "High"


    elif novelty:

        indicator = (
            "प्रारंभिक IP screening अनुकूल हो सकती है, "
            "लेकिन prior-art review आवश्यक है।"
            if hindi
            else
            "The preliminary IP screening may be promising, "
            "but prior-art review is required."
        )

        attention = "Medium"


    else:

        indicator = (
            "प्रारंभिक screening पूरी हुई; पर्याप्त novelty "
            "evidence उपलब्ध नहीं है।"
            if hindi
            else
            "Preliminary screening completed; sufficient novelty "
            "evidence is not available."
        )

        attention = "Medium"


    # -----------------------------------------------------
    # IP ROUTES
    # -----------------------------------------------------

    routes = [

        "पेटेंट"
        if hindi
        else
        "Patent",

        "ट्रेडमार्क"
        if hindi
        else
        "Trademark",

        "ट्रेड सीक्रेट"
        if hindi
        else
        "Trade Secret",

        "डिज़ाइन"
        if hindi
        else
        "Design",

        "कॉपीराइट"
        if hindi
        else
        "Copyright",

        "GI"
    ]


    # -----------------------------------------------------
    # RECOMMENDATIONS
    # -----------------------------------------------------

    if hindi:

        recommendations = [
            "Innovation की novelty और technical contribution document करें.",
            "Patent और non-patent prior art search करें.",
            "Traditional Knowledge involvement verify करें.",
            "Applicable jurisdiction-specific requirements check करें.",
            "Filing या commercialisation से पहले qualified professional से assessment लें."
        ]

    else:

        recommendations = [
            "Document the innovation's novelty and technical contribution.",
            "Conduct patent and non-patent prior-art searches.",
            "Verify whether Traditional Knowledge is involved.",
            "Check jurisdiction-specific requirements.",
            "Obtain qualified professional assessment before filing or commercialisation."
        ]


    # -----------------------------------------------------
    # SOURCES
    # -----------------------------------------------------

    selected_sources = (
        jurisdiction_sources(
            jurisdiction
        )
    )


    formatted_sources = [

        source_record(item)

        for item in selected_sources[:5]

    ]


    # -----------------------------------------------------
    # DISCLAIMER
    # -----------------------------------------------------

    disclaimer = (
        "प्रारंभिक सूचना आधारित guidance only; "
        "यह legal advice या final IP determination नहीं है।"
        if hindi
        else
        "Preliminary informational guidance only; "
        "this is not legal advice or a final IP determination."
    )


    # -----------------------------------------------------
    # RESPONSE
    # -----------------------------------------------------

    return {

        "name":
            name,

        "preliminary_indicator":
            indicator,

        "attention_level":
            attention,

        "confidence":
            "Medium",

        "possible_ip_routes":
            routes,

        "recommendations":
            recommendations,

        "flags":
            flags,

        "sources":
            formatted_sources,

        "disclaimer":
            disclaimer
    }


# =========================================================
# REGULATORY NAVIGATOR
# =========================================================

@app.post("/regulatory")
def regulatory(req: RegulatoryRequest):

    category = str(
        req.category or ""
    ).strip()

    jurisdiction = str(
        req.jurisdiction or "India"
    ).strip()

    description = str(
        req.description or ""
    ).strip()

    hindi = is_hindi(
        req.language
    )


    # -----------------------------------------------------
    # INDIA
    # -----------------------------------------------------

    if jurisdiction.lower() == "india":

        if hindi:

            overview = (
                "भारत में regulatory pathway product category, "
                "intended use, formulation, dosage form और applicable "
                "rules पर निर्भर करता है।"
            )

            steps = [
                "Product category और intended use निर्धारित करें।",
                "Applicable competent authority identify करें।",
                "Current applicable rules और standards verify करें।",
                "Required formulation, safety, quality और labeling evidence तैयार करें।",
                "Official authority requirements के अनुसार आगे की प्रक्रिया पूरी करें।"
            ]

        else:

            overview = (
                "In India, the regulatory pathway depends on product "
                "category, intended use, formulation, dosage form and "
                "the applicable rules."
            )

            steps = [
                "Determine the product category and intended use.",
                "Identify the applicable competent authority.",
                "Verify the current applicable rules and standards.",
                "Prepare required formulation, safety, quality and labeling evidence.",
                "Follow the official authority requirements for the applicable pathway."
            ]


    # -----------------------------------------------------
    # INTERNATIONAL
    # -----------------------------------------------------

    else:

        if hindi:

            overview = (
                "International regulatory requirements jurisdiction के "
                "अनुसार अलग हो सकती हैं। Target country/market, product "
                "classification, intended use और applicable authority "
                "पहले identify करें।"
            )

            steps = [
                "Target country या market specify करें।",
                "Product classification determine करें।",
                "Applicable regulatory authority identify करें।",
                "Current registration, safety, quality और labeling requirements check करें।",
                "Target jurisdiction के official requirements के अनुसार pathway बनाएं।"
            ]

        else:

            overview = (
                "International regulatory requirements vary by jurisdiction. "
                "Identify the target country or market, product classification, "
                "intended use and applicable authority first."
            )

            steps = [
                "Specify the target country or market.",
                "Determine the product classification.",
                "Identify the applicable regulatory authority.",
                "Check current registration, safety, quality and labeling requirements.",
                "Build the pathway according to the official requirements of the target jurisdiction."
            ]


    # -----------------------------------------------------
    # CATEGORY-SPECIFIC GUIDANCE
    # -----------------------------------------------------

    category_lower = category.lower()


    if (
        "cosmetic" in category_lower
        or "कॉस्मेटिक" in category_lower
    ):

        if hindi:

            category_note = (
                "Cosmetic products के लिए ingredients, safety, "
                "claims, labeling और manufacturing requirements "
                "की जाँच आवश्यक है।"
            )

        else:

            category_note = (
                "For cosmetic products, review ingredients, safety, "
                "claims, labeling and manufacturing requirements."
            )


    elif (
        "nutraceutical" in category_lower
        or "food" in category_lower
        or "आहार" in category_lower
    ):

        if hindi:

            category_note = (
                "Food/nutraceutical route में permitted ingredients, "
                "claims, labeling और applicable food requirements "
                "verify करें।"
            )

        else:

            category_note = (
                "For the food/nutraceutical route, verify permitted "
                "ingredients, claims, labeling and applicable food requirements."
            )


    elif (
        "drug" in category_lower
        or "medicine" in category_lower
        or "औषधि" in category_lower
    ):

        if hindi:

            category_note = (
                "Medicinal products के लिए classification, quality, "
                "safety, evidence, manufacturing और applicable "
                "approval requirements verify करें।"
            )

        else:

            category_note = (
                "For medicinal products, verify classification, quality, "
                "safety, evidence, manufacturing and applicable approval requirements."
            )


    else:

        if hindi:

            category_note = (
                "Exact regulatory requirements product classification "
                "और intended use verify करने के बाद निर्धारित किए जाने चाहिए।"
            )

        else:

            category_note = (
                "Exact regulatory requirements should be determined "
                "after confirming product classification and intended use."
            )


    # -----------------------------------------------------
    # SOURCES
    # -----------------------------------------------------

    selected_sources = (
        jurisdiction_sources(
            jurisdiction
        )
    )


    formatted_sources = [

        source_record(item)

        for item in selected_sources[:5]

    ]


    # -----------------------------------------------------
    # DISCLAIMER
    # -----------------------------------------------------

    if hindi:

        disclaimer = (
            "यह प्रारंभिक regulatory guidance है। यह regulatory "
            "approval, licence, certification या legal advice नहीं है। "
            "Current official requirements को filing या commercial "
            "launch से पहले verify करें।"
        )

    else:

        disclaimer = (
            "This is preliminary regulatory guidance. It is not "
            "regulatory approval, a licence, certification or legal advice. "
            "Verify current official requirements before filing or commercial launch."
        )


    # -----------------------------------------------------
    # FINAL REGULATORY RESPONSE
    # -----------------------------------------------------

    return {

        "category":
            category,

        "jurisdiction":
            jurisdiction,

        "description":
            description,

        "overview":
            overview,

        "summary":
            overview,

        "category_guidance":
            category_note,

        "next_steps":
            steps,

        "sources":
            formatted_sources,

        "disclaimer":
            disclaimer
    }


# =========================================================
# SOURCES ENDPOINT
# =========================================================

@app.get("/sources")
def sources():

    return {
        "sources": [
            source_record(item)
            for item in SOURCES
        ]
    }


# =========================================================
# ROOT ENDPOINT
# =========================================================

@app.get("/")
def root():

    return {

        "service":
            "IP-SAKTI Sahayak API",

        "status":
            "running",

        "version":
            "1.2.0",

        "modules": [

            "Ask Sahayak",

            "Innovation IP Checker",

            "Formulation Explorer",

            "Regulatory Navigator",

            "Evidence & Sources"

        ]
    }


# =========================================================
# GLOBAL FALLBACK
# =========================================================

@app.get("/favicon.ico")
def favicon():

    return {
        "status": "ok"
    }

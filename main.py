from pathlib import Path
from typing import Optional
import json
import re

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel


BASE = Path(__file__).resolve().parent
DATA = BASE / "data"


app = FastAPI(
    title="IP-SAKTI Sahayak API",
    version="1.1.0"
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def load_json(name):
    with open(DATA / name, "r", encoding="utf-8") as f:
        return json.load(f)


KNOWLEDGE = load_json("knowledge.json")
SOURCES = load_json("sources.json")
INGREDIENTS = load_json("ingredients.json")


class AskRequest(BaseModel):
    question: str
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
    dosage_form: str = ""
    ingredients: str = ""
    intended_use: str = ""
    novelty: str = "Unknown"
    jurisdiction: str = "India"
    language: str = "English"


class RegulatoryRequest(BaseModel):
    category: str
    jurisdiction: str = "India"
    description: str = ""
    language: str = "English"


def is_hindi(language: str) -> bool:
    value = str(language or "").lower()
    return "hindi" in value or "हिन्दी" in value


def source_record(item):
    return {
        "title": item.get("source") or item.get("title", ""),
        "authority": item.get("authority", ""),
        "version": item.get(
            "version",
            item.get("effective_date", "Not specified")
        ),
        "relevance": item.get(
            "summary",
            item.get("description", "")
        ),
        "url": item.get("url", "")
    }


def jurisdiction_sources(jurisdiction: str):
    j = str(jurisdiction or "").lower()

    if j == "india":
        india = [
            x for x in SOURCES
            if "india" in (
                str(x.get("title", "")) + " " +
                str(x.get("source", "")) + " " +
                str(x.get("authority", "")) + " " +
                str(x.get("summary", ""))
            ).lower()
        ]

        return india if india else SOURCES[:4]

    international_words = [
        "international",
        "wipo",
        "usa",
        "europe",
        "eu",
        "united states"
    ]

    international = [
        x for x in SOURCES
        if any(
            word in (
                str(x.get("title", "")) + " " +
                str(x.get("source", "")) + " " +
                str(x.get("authority", "")) + " " +
                str(x.get("summary", ""))
            ).lower()
            for word in international_words
        )
    ]

    return international if international else SOURCES[:4]


@app.get("/health")
def health():
    return {
        "status": "ok",
        "service": "IP-SAKTI Sahayak",
        "version": "1.1.0"
    }
def retrieve(question: str, jurisdiction: str):
    terms = set(re.findall(r"[a-zA-Z]{3,}", question.lower()))
    scored = []

    for item in KNOWLEDGE:
        text = (
            str(item.get("title", "")) + " " +
            str(item.get("summary", "")) + " " +
            str(item.get("category", ""))
        ).lower()

        score = sum(1 for term in terms if term in text)

        if str(jurisdiction or "").lower() in text:
            score += 2

        if score > 0:
            scored.append((score, item))

    scored.sort(key=lambda x: x[0], reverse=True)

    return [item for score, item in scored[:4]]


@app.post("/ask")
def ask(req: AskRequest):
    question = req.question.strip()
    hindi = is_hindi(req.language)

    if not question:
        return {
            "answer": (
                "कृपया अपना प्रश्न दर्ज करें।"
                if hindi
                else "Please provide a question."
            ),
            "confidence": "Low",
            "next_steps": [],
            "sources": [],
            "disclaimer": (
                "केवल प्रारंभिक सूचना आधारित मार्गदर्शन।"
                if hindi
                else "Informational guidance only."
            )
        }

    hits = retrieve(question, req.jurisdiction)
    lower = question.lower()

    if not hits:
        if hindi:
            answer = (
                "वर्तमान curated knowledge base में पर्याप्त matching "
                "evidence नहीं मिला। सिस्टम अनुमान लगाकर उत्तर देने के "
                "बजाय abstain कर रहा है।"
            )

            steps = [
                "Product category, jurisdiction और specific IP/regulatory issue स्पष्ट करें।",
                "Case-specific assessment के लिए qualified professional से सलाह लें।"
            ]

        else:
            answer = (
                "I could not find sufficient matching evidence in the "
                "current curated prototype knowledge base. I am abstaining "
                "rather than inventing an answer."
            )

            steps = [
                "Refine the question with product category, jurisdiction and the specific IP/regulatory issue.",
                "Escalate to a qualified human facilitator for a case-specific assessment."
            ]

        return {
            "answer": answer,
            "confidence": "Low",
            "next_steps": steps,
            "sources": [],
            "disclaimer": (
                "सीमित curated knowledge base का उपयोग किया गया है। "
                "Production deployment में authoritative version-tracked sources आवश्यक हैं।"
                if hindi
                else
                "The prototype uses a limited local knowledge base. "
                "Production deployment should use a version-tracked authoritative corpus."
            )
        }

    if (
        "patent" in lower
        or "patentable" in lower
        or "novel" in lower
    ):
        if hindi:
            answer = (
                "प्रारंभिक patentability review में पहले यह देखें कि "
                "तकनीकी रूप से क्या नया है और फिर prior-art search करें। "
                "Ayurveda से जुड़े विषयों में Traditional Knowledge और "
                "अन्य prior-art sources भी जाँचना आवश्यक है। "
                "यह केवल प्रारंभिक संकेतक है, अंतिम patentability determination नहीं।"
            )

            steps = [
                "Novel technical features को स्पष्ट करें।",
                "Patent और non-patent prior art search करें।",
                "Relevant Traditional Knowledge/prior-art sources जाँचें।",
                "Filing से पहले professional patentability opinion लें।"
            ]

        else:
            answer = (
                "For a preliminary patentability review, focus first on "
                "what is technically new and then perform a prior-art search. "
                "For Ayurveda-related subject matter, also check traditional "
                "knowledge and other prior-art sources."
            )

            steps = [
                "Define the novel technical features.",
                "Search patent and non-patent prior art.",
                "Check traditional-knowledge/prior-art sources where relevant.",
                "Obtain a professional patentability opinion before filing."
            ]

    elif "trademark" in lower or "brand" in lower:
        if hindi:
            answer = (
                "Trademark strategy मुख्य रूप से distinctive brand name, "
                "identifier या logo की protection से संबंधित है। "
                "Adoption या filing से पहले clearance search और सही "
                "class/jurisdiction चुनना आवश्यक है।"
            )

            steps = [
                "Proposed mark और goods/services define करें।",
                "Trademark clearance search करें।",
                "Appropriate classes और jurisdiction चुनें।",
                "Applicable procedure के अनुसार file और monitor करें।"
            ]

        else:
            answer = (
                "A trademark strategy is primarily about protecting a "
                "distinctive brand identifier for specified goods or services."
            )

            steps = [
                "Define the proposed mark and goods/services.",
                "Conduct a clearance search.",
                "Select appropriate classes and jurisdiction.",
                "File and monitor the application."
            ]

    elif (
        "abs" in lower
        or "nagoya" in lower
        or "biological" in lower
        or "traditional knowledge" in lower
    ):
        if hindi:
            answer = (
                "यदि innovation में biological resources या associated "
                "Traditional Knowledge का उपयोग है, तो यह निर्धारित करें "
                "कि access-and-benefit-sharing obligations लागू होती हैं या नहीं। "
                "सटीक requirements source और applicable national/international "
                "framework पर निर्भर करती हैं।"
            )

            steps = [
                "Biological resource का origin और access history record करें।",
                "Associated Traditional Knowledge identify करें।",
                "Applicable national ABS framework check करें।",
                "Benefit-sharing या permissions लागू होने पर specialist advice लें।"
            ]

        else:
            answer = (
                "If the innovation uses biological resources or associated "
                "traditional knowledge, determine whether access-and-benefit-sharing "
                "obligations apply."
            )

            steps = [
                "Record biological-resource origin and access history.",
                "Identify associated traditional knowledge.",
                "Check the applicable national ABS framework.",
                "Seek specialist advice if benefit-sharing or permissions may apply."
            ]
        elif (
        "regulat" in lower
        or "medicine" in lower
        or "cosmetic" in lower
        or "nutraceutical" in lower
    ):
        if hindi:
            answer = (
                "Regulatory requirements product classification और intended "
                "use पर काफी निर्भर करते हैं। Product category, ingredients, "
                "dosage form और intended use से शुरुआत करके applicable authority "
                "और current requirements map करें।"
            )

            steps = [
                "Formulation और intended use record करें।",
                "Product classification निर्धारित करें।",
                "Competent authority और current rules identify करें।",
                "Applicable evidence और documents तैयार करें।"
            ]

        else:
            answer = (
                "Regulatory requirements depend heavily on how the product "
                "is classified and what it is intended to do."
            )

            steps = [
                "Capture formulation and intended use.",
                "Classify the product.",
                "Identify the competent authority and current rules.",
                "Prepare applicable evidence and documents."
            ]

    else:
        if hindi:
            answer = (
                "इस प्रश्न के लिए पहले jurisdiction, product category और "
                "applicable IP/regulatory framework identify करना चाहिए। "
                "नीचे दिए गए cited knowledge items आगे की analysis के लिए "
                "starting evidence प्रदान करते हैं।"
            )

            steps = [
                "Jurisdiction specify करें।",
                "Product/formulation category specify करें।",
                "Cited sources review करें।",
                "Evidence insufficient होने पर qualified professional से सलाह लें।"
            ]

        else:
            answer = (
                "Based on the current evidence set, this question should be "
                "approached by identifying the jurisdiction, product category "
                "and applicable IP/regulatory framework first."
            )

            steps = [
                "Specify the jurisdiction.",
                "Specify product/formulation category.",
                "Review the cited sources.",
                "Escalate if the evidence is insufficient or case-specific."
            ]

    selected_sources = jurisdiction_sources(req.jurisdiction)

    return {
        "answer": answer,
        "confidence": "Medium",
        "next_steps": steps,
        "sources": [
            source_record(item)
            for item in (
                hits if hits else selected_sources[:4]
            )
        ],
        "disclaimer": (
            "प्रारंभिक सूचना आधारित मार्गदर्शन; यह legal advice, "
            "regulatory approval, certification या final patentability "
            "determination नहीं है।"
            if hindi
            else
            "Preliminary informational guidance only; not legal advice, "
            "regulatory approval, certification or a final patentability determination."
        )
    }


def match_ingredients(raw_text: str):
    text = raw_text.lower()
    matches = []

    for item in INGREDIENTS:
        if any(
            keyword.lower() in text
            for keyword in item.get("keywords", [])
        ):
            matches.append(item)

    return matches


@app.get("/ingredients")
def ingredients(q: Optional[str] = None):
    if not q:
        return {"items": INGREDIENTS}

    terms = re.findall(r"[a-zA-Z]{3,}", q.lower())

    items = [
        item for item in INGREDIENTS
        if any(
            term in (
                str(item.get("name", "")) + " " +
                " ".join(item.get("aliases", []))
            ).lower()
            for term in terms
        )
    ]

    return {"items": items}


@app.post("/classify")
def classify(req: FormulationRequest):
    text_all = (
        req.name + " " +
        req.ingredients + " " +
        req.intended_use + " " +
        req.dosage_form
    ).lower()

    matched = match_ingredients(text_all)
    hindi = is_hindi(req.language)

    if any(
        word in text_all
        for word in ["cosmetic", "cream", "skin", "shampoo", "soap"]
    ):
        category = "Cosmetic"

        regulatory = (
            "Cosmetic classification, safety, labeling और manufacturing "
            "requirements verify करें।"
            if hindi else
            "Confirm cosmetic classification and applicable safety, "
            "labeling and manufacturing requirements."
        )

    elif any(
        word in text_all
        for word in [
            "nutraceutical",
            "food",
            "nutrition",
            "beverage",
            "supplement",
            "aahar"
        ]
    ):
        category = "Ayurveda-Aahar / nutraceutical"

        regulatory = (
            "Food/nutraceutical classification, permitted ingredients, "
            "claims और labeling requirements verify करें।"
            if hindi else
            "Confirm food/nutraceutical classification, permitted "
            "ingredients, claims and labeling requirements."
        )

    elif any(
        word in text_all
        for word in ["new drug", "clinical", "novel drug"]
    ):
        category = "New / non-classical drug"

        regulatory = (
            "New/non-classical medicinal product के लिए additional "
            "evidence और approval steps की आवश्यकता हो सकती है। "
            "Current competent-authority pathway verify करें।"
            if hindi else
            "A new/non-classical medicinal product may require additional "
            "evidence and approval steps; confirm the current competent-authority pathway."
        )

    elif "phytopharma" in text_all:
        category = "Phytopharmaceutical"

        regulatory = (
            "Phytopharmaceutical-specific requirements और evidence "
            "pathway competent authority के साथ verify करें।"
            if hindi else
            "Confirm phytopharmaceutical-specific requirements and "
            "evidence pathway with the competent authority."
        )

    elif (
        req.novelty.lower().startswith("novel")
        or "proprietary" in text_all
    ):
        category = "Proprietary medicine"

        regulatory = (
            "Proprietary-medicine route और current manufacturing, "
            "evidence तथा licensing requirements verify करें।"
            if hindi else
            "Confirm the proprietary-medicine route and current "
            "manufacturing, evidence and licensing requirements."
        )

    else:
        category = "Classical / generic medicine"

        regulatory = (
            "Verify करें कि formulation और intended use applicable "
            "classical/generic medicine pathway में आते हैं या नहीं।"
            if hindi else
            "Confirm whether the formulation and intended use fall "
            "within the applicable classical/generic medicine pathway."
        )

    ingredient_notes = []

    for item in matched:
        ingredient_notes.append({
            "name": item.get("name", ""),
            "part_used": item.get("part_used", ""),
            "aliases": item.get("aliases", []),
            "traditional_context": item.get(
                "traditional_context", ""
            ),
            "ip_flag": item.get("ip_flag", ""),
            "abs_flag": item.get("abs_flag", ""),
            "regulatory_flag": item.get(
                "regulatory_flag", ""
            ),
            "common_forms": item.get(
                "common_forms", []
            )
        })

    if matched:
        if hindi:
            abs_text = (
                "Detected ingredient(s) का traditional/biological-resource "
                "context है। Provenance और applicable ABS requirements review करें।"
            )

            ip = (
                "एक या अधिक known traditional ingredients detect हुए हैं। "
                "Novelty claim करने से पहले Traditional Knowledge और prior art "
                "review करें। यदि formulation/process में नया technical contribution "
                "है, तो अलग patentability analysis आवश्यक होगा।"
            )

        else:
            abs_text = (
                "Matched ingredient(s) have traditional/biological-resource "
                "context. Review provenance and whether applicable ABS requirements are triggered."
            )

            ip = (
                "Because one or more known traditional ingredients were detected, "
                "review traditional knowledge and prior art before asserting novelty. "
                "A novel technical formulation/process may still require a separate patentability analysis."
            )

    else:
        if hindi:
            abs_text = (
                "Prototype database में कोई ingredient confidently match नहीं हुआ। "
                "Scientific/common names और biological-resource provenance verify करें।"
            )

            ip = (
                "Check करें कि proposed formulation या process में कोई नया "
                "technical contribution है या नहीं और prior-art search करें।"
            )

        else:
            abs_text = (
                "No ingredient in the prototype database was confidently matched. "
                "Enter scientific/common names and review provenance for any biological resource."
            )

            ip = (
                "Review whether the proposed formulation or process contains "
                "a new technical contribution and conduct a prior-art search."
            )

    if hindi:
        explanation = (
            "Prototype formulation rules और ingredient knowledge layer को "
            "combine करता है। यह navigation aid है, legal या regulatory "
            "determination नहीं।"
        )

        confidence = "Medium"

    else:
        explanation = (
            "The prototype combines formulation rules with the ingredient "
            "knowledge layer. It is a navigation aid, not a legal or regulatory determination."
        )

        confidence = "Medium"

    selected_sources = jurisdiction_sources(req.jurisdiction)

    return {
        "category": category,
        "regulatory_guidance": regulatory,
        "matched_ingredients": ingredient_notes,
        "ip_guidance": ip,
        "abs_guidance": abs_text,
        "explanation": explanation,
        "confidence": confidence,
        "sources": [
            source_record(item)
            for item in selected_sources[:4]
        ],
        "disclaimer": (
            "प्रारंभिक सूचना आधारित मार्गदर्शन; यह legal advice, "
            "regulatory approval या final classification नहीं है।"
            if hindi
            else
            "Preliminary informational guidance only; not legal advice, "
            "regulatory approval or a final classification."
        )
    }
@app.post("/ip-check")
def ip_check(req: IPRequest):
    hindi = is_hindi(req.language)

    name = req.name.strip()
    description = req.description.strip()
    novelty = req.novelty.strip()
    tk = req.traditional_knowledge.strip()
    similar = req.similar_product.strip()

    attention = "Medium"
    indicator = "Preliminary review needed"

    if (
        tk.lower() not in ["no", "no / unknown", "unknown", "none"]
        or similar.lower() not in ["no", "unknown", "none"]
    ):
        attention = "High"

    if novelty.lower() in [
        "yes",
        "novel",
        "new",
        "yes - novel"
    ]:
        indicator = "Potential IP opportunity; evidence required"
    else:
        indicator = "Preliminary IP assessment required"

    routes = [
        "Patent",
        "Trademark",
        "Trade Secret",
        "Design",
        "Copyright",
        "Geographical Indication"
    ]

    if hindi:
        answer = (
            f"'{name or 'इस innovation'}' के लिए यह केवल preliminary IP "
            "indicator है। Final patentability या ownership determination "
            "के लिए prior-art, Traditional Knowledge और applicable rules "
            "की detailed review आवश्यक है।"
        )

        recommendations = [
            "Innovation के novel technical features document करें।",
            "Relevant patent और non-patent prior art search करें।",
            "Traditional Knowledge involvement verify करें।",
            "Similar products और existing disclosures check करें।",
            "Filing या commercialization से पहले qualified IP professional से सलाह लें।"
        ]

    else:
        answer = (
            f"For '{name or 'this innovation'}', this is only a preliminary "
            "IP indicator. A final patentability or ownership determination "
            "requires detailed review of prior art, traditional knowledge "
            "and applicable rules."
        )

        recommendations = [
            "Document the novel technical features.",
            "Search relevant patent and non-patent prior art.",
            "Verify any Traditional Knowledge involvement.",
            "Check similar products and existing disclosures.",
            "Seek qualified IP professional advice before filing or commercialization."
        ]

    selected_sources = jurisdiction_sources(req.jurisdiction)

    return {
        "indicator": indicator,
        "attention": attention,
        "answer": answer,
        "possible_ip_routes": routes,
        "recommendations": recommendations,
        "input_summary": {
            "name": name,
            "description": description,
            "novelty": novelty,
            "traditional_knowledge": tk,
            "similar_product": similar,
            "jurisdiction": req.jurisdiction
        },
        "sources": [
            source_record(item)
            for item in selected_sources[:4]
        ],
        "disclaimer": (
            "यह preliminary informational guidance है। यह legal advice, "
            "final patentability opinion, regulatory approval या commercial "
            "clearance नहीं है।"
            if hindi
            else
            "This is preliminary informational guidance only. It is not legal "
            "advice, a final patentability opinion, regulatory approval or commercial clearance."
        )
    }


@app.post("/regulatory")
def regulatory(req: RegulatoryRequest):
    hindi = is_hindi(req.language)
    category = req.category.strip()

    if hindi:
        if req.jurisdiction.lower() == "india":
            answer = (
                f"'{category}' के लिए India-specific regulatory pathway "
                "product classification, ingredients, intended use और "
                "applicable authority पर निर्भर करेगा।"
            )
        else:
            answer = (
                f"'{category}' के लिए international jurisdiction में "
                "applicable authority, classification और local requirements "
                "verify करना आवश्यक है।"
            )

        steps = [
            "Product classification determine करें।",
            "Ingredients और intended use document करें।",
            "Applicable competent authority identify करें।",
            "Current rules, standards और evidence requirements verify करें।",
            "Submission/commercialization से पहले professional review लें।"
        ]

    else:
        if req.jurisdiction.lower() == "india":
            answer = (
                f"For '{category}', the India-specific regulatory pathway "
                "depends on product classification, ingredients, intended use "
                "and the applicable competent authority."
            )
        else:
            answer = (
                f"For '{category}', the international pathway requires "
                "verification of the applicable authority, classification "
                "and local requirements."
            )

        steps = [
            "Determine product classification.",
            "Document ingredients and intended use.",
            "Identify the applicable competent authority.",
            "Verify current rules, standards and evidence requirements.",
            "Obtain professional review before submission or commercialization."
        ]

    selected_sources = jurisdiction_sources(req.jurisdiction)

    return {
        "category": category,
        "jurisdiction": req.jurisdiction,
        "answer": answer,
        "next_steps": steps,
        "sources": [
            source_record(item)
            for item in selected_sources[:4]
        ],
        "disclaimer": (
            "यह preliminary regulatory guidance है और regulatory approval "
            "या legal advice नहीं है।"
            if hindi
            else
            "This is preliminary regulatory guidance and is not regulatory approval or legal advice."
        )
    }


@app.get("/knowledge")
def knowledge():
    return {
        "items": KNOWLEDGE
    }


@app.get("/sources")
def sources():
    return {
        "items": [
            source_record(item)
            for item in SOURCES
        ]
    }

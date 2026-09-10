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
        "title": item.get("source") or item.get("title"),
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

        if jurisdiction.lower() in text:
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

    # PATENT
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

    # TRADEMARK
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

    # ABS / TRADITIONAL KNOWLEDGE
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

    # REGULATORY
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

    # GENERAL
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

    # PRODUCT CLASSIFICATION

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

    # INGREDIENT ANALYSIS

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

    # IP / TK / ABS

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

    # FINAL RESPONSE

    if hindi:
        explanation = (
            "Prototype formulation rules और ingredient knowledge layer को "
            "combine करता है। यह navigation aid है, legal या regulatory determination नहीं।"
        )

        next_steps = [
            "Product classification को current applicable rules से verify करें।",
            "Ingredient identity, plant part, source और provenance confirm करें।",
            "Matched ingredients के Traditional Knowledge/prior-art aspects review करें।",
            "Classification को regulatory journey से map करें।",
            "Appropriate IP protection route review करें।"
        ]

    else:
        explanation = (
            "The prototype combines formulation rules with an ingredient "
            "knowledge layer. It is a navigation aid, not a legal or regulatory determination."
        )

        next_steps = [
            "Verify classification against current applicable rules.",
            "Confirm ingredient identity, plant part, source and provenance.",
            "Review traditional-knowledge/prior-art considerations for matched ingredients.",
            "Map the classification to the regulatory journey.",
            "Review the appropriate IP protection route."
        ]

    selected_sources = jurisdiction_sources(req.jurisdiction)

    return {
        "category": category,
        "confidence": "Medium" if matched else "Low",
        "explanation": explanation,
        "regulatory": regulatory,
        "ip": ip,
        "abs": abs_text,
        "matched_ingredients": ingredient_notes,
        "next_steps": next_steps,
        "sources": [
            source_record(item)
            for item in selected_sources[:4]
        ]
    }
    @app.post("/ip-check")
def ip_check(req: IPRequest):
    hindi = is_hindi(req.language)

    risk = "Low"

    if req.similar_product == "Yes" or req.traditional_knowledge == "Yes":
        risk = "Medium"

    if not req.novelty.strip():
        risk = "High"

    if hindi:
        routes = [
            {
                "name": "Patent",
                "status": "Review",
                "reason": "New technical solution होने पर relevant हो सकता है; prior-art search आवश्यक है."
            },
            {
                "name": "Trademark",
                "status": "Review",
                "reason": "Distinctive brand name, product name या logo के लिए relevant हो सकता है."
            },
            {
                "name": "Trade Secret",
                "status": "Possible",
                "reason": "Confidential know-how को secrecy maintain करके protect किया जा सकता है."
            },
            {
                "name": "Design",
                "status": "Case-dependent",
                "reason": "Qualifying visual या aesthetic product features के लिए relevant हो सकता है."
            },
            {
                "name": "Copyright",
                "status": "Case-dependent",
                "reason": "Original artwork, documentation या software जैसी expression को protect कर सकता है."
            },
            {
                "name": "GI",
                "status": "Case-dependent",
                "reason": "Applicable geographical linkage और GI requirements पूरी होने पर relevant हो सकता है."
            }
        ]

        checks = [
            "Structured prior-art search करें.",
            "Relevant TK/prior-art databases check करें.",
            "Inventorship, development records और dates document करें.",
            "Public disclosure से पहले appropriate IP route assess करें."
        ]

        summary = (
            "Prototype केवल preliminary indicators देता है. "
            "High-attention result का मतलब यह नहीं है कि innovation unprotectable है; "
            "इसका मतलब है कि अधिक evidence की आवश्यकता है."
        )

        disclaimer = (
            "केवल प्रारंभिक informational guidance; यह legal advice, "
            "regulatory approval, certification या final patentability determination नहीं है."
        )

    else:
        routes = [
            {
                "name": "Patent",
                "status": "Review",
                "reason": "Potentially relevant where a new technical solution satisfies applicable patentability requirements; prior-art search is essential."
            },
            {
                "name": "Trademark",
                "status": "Review",
                "reason": "Relevant for a distinctive brand, product name or logo; clearance and class selection are needed."
            },
            {
                "name": "Trade Secret",
                "status": "Possible",
                "reason": "May help protect confidential know-how when secrecy can realistically be maintained."
            },
            {
                "name": "Design",
                "status": "Case-dependent",
                "reason": "May be relevant to protect qualifying visual or aesthetic features of a product."
            },
            {
                "name": "Copyright",
                "status": "Case-dependent",
                "reason": "May protect qualifying original expression such as artwork, documentation or software."
            },
            {
                "name": "GI",
                "status": "Case-dependent",
                "reason": "Relevant only where the product and geographical linkage satisfy the applicable GI framework."
            }
        ]

        checks = [
            "Run a structured prior-art search.",
            "Check TK/prior-art databases where relevant.",
            "Document dates, inventorship and development records.",
            "Assess the correct IP route before public disclosure."
        ]

        summary = (
            "The prototype finds preliminary indicators only. "
            "A high-attention result means more evidence is needed; "
            "it does not mean the innovation is unprotectable."
        )

        disclaimer = (
            "Preliminary informational guidance only; not legal advice, "
            "regulatory approval, certification or a final patentability determination."
        )

    if req.traditional_knowledge == "Yes":
        if hindi:
            checks.insert(
                1,
                "Traditional Knowledge का source और nature record करें तथा applicable protection/ABS considerations examine करें."
            )
        else:
            checks.insert(
                1,
                "Record the source and nature of traditional knowledge and examine applicable protection/ABS considerations."
            )

    selected_sources = jurisdiction_sources(req.jurisdiction)

    return {
        "risk": risk,
        "summary": summary,
        "routes": routes,
        "checks": checks,
        "sources": [
            source_record(item)
            for item in selected_sources[:4]
        ],
        "disclaimer": disclaimer
    }


@app.post("/regulatory")
def regulatory(req: RegulatoryRequest):
    hindi = is_hindi(req.language)

    if hindi:
        common = [
            {
                "title": "Classification confirm करें",
                "detail": "Current applicable rules और definitions के अनुसार product category verify करें."
            },
            {
                "title": "Competent authority identify करें",
                "detail": "Applicable authority, licence/registration route और current procedure identify करें."
            },
            {
                "title": "Evidence तैयार करें",
                "detail": "Formulation, ingredients, quality, safety, efficacy, labeling और applicable records compile करें."
            },
            {
                "title": "IP और ABS check करें",
                "detail": "Relevant होने पर IP strategy तथा traditional-knowledge/biological-resource obligations review करें."
            },
            {
                "title": "Submit / Comply",
                "detail": "Current authority procedure follow करें और approval/registration के बाद ongoing compliance maintain करें."
            }
        ]

        summary = (
            "इसे navigation checklist के रूप में उपयोग करें, "
            "regulatory approval decision के रूप में नहीं."
        )

        disclaimer = (
            "Requirements बदल सकती हैं. Regulatory action लेने से पहले "
            "current official rules verify करें."
        )

    else:
        common = [
            {
                "title": "Confirm classification",
                "detail": "Verify the selected product category using the current applicable rules and definitions."
            },
            {
                "title": "Map competent authority",
                "detail": "Identify the authority, licence/registration route and current procedural requirements."
            },
            {
                "title": "Prepare evidence",
                "detail": "Compile formulation, ingredient, quality, safety, efficacy, labeling and other applicable records."
            },
            {
                "title": "Check IP and ABS",
                "detail": "Review IP strategy and traditional-knowledge/biological-resource obligations where relevant."
            },
            {
                "title": "Submit / comply",
                "detail": "Follow the current authority procedure and maintain ongoing compliance after approval/registration where applicable."
            }
        ]

        summary = (
            "Use this as a navigation checklist, not as a regulatory approval decision."
        )

        disclaimer = (
            "Requirements can change. Verify current official rules before taking regulatory action."
        )

    if req.jurisdiction != "India":
        if hindi:
            common[1]["detail"] = (
                "International requirements jurisdiction के अनुसार अलग होते हैं. "
                "Target country/region select करके उसकी current competent authority और procedure verify करें."
            )
        else:
            common[1]["detail"] = (
                "International requirements differ by jurisdiction. "
                "Select the target country/region and verify its current competent authority and procedure."
            )

    selected_sources = jurisdiction_sources(req.jurisdiction)

    return {
        "title": f"{req.category} — preliminary pathway",
        "jurisdiction": req.jurisdiction,
        "summary": summary,
        "steps": common,
        "sources": [
            source_record(item)
            for item in selected_sources[:4]
        ],
        "disclaimer": disclaimer
    }


@app.get("/knowledge")
def knowledge(q: Optional[str] = None):
    items = KNOWLEDGE

    if q:
        terms = re.findall(r"[a-zA-Z]{3,}", q.lower())

        items = [
            item for item in KNOWLEDGE
            if any(
                term in (
                    str(item.get("title", "")) + " " +
                    str(item.get("summary", "")) + " " +
                    str(item.get("category", ""))
                ).lower()
                for term in terms
            )
        ]

    return {"items": items}


@app.get("/sources")
def sources():
    return {"sources": SOURCES}

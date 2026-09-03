from pathlib import Path
from typing import List, Optional
import json
import re

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

BASE = Path(__file__).resolve().parent
DATA = BASE / "data"

app = FastAPI(title="IP-SAKTI Sahayak API", version="1.0.0")

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

class FormulationRequest(BaseModel):
    name: str = ""
    dosage_form: str = ""
    ingredients: str = ""
    intended_use: str = ""
    novelty: str = "Unknown"
    jurisdiction: str = "India"

class RegulatoryRequest(BaseModel):
    category: str
    jurisdiction: str = "India"
    description: str = ""

@app.get("/health")
def health():
    return {
        "status": "ok",
        "service": "IP-SAKTI Sahayak",
        "version": "1.0.0",
    }


def source_record(item):
    return {
        "title": item.get("source") or item.get("title"),
        "authority": item.get("authority", ""),
        "version": item.get("version", item.get("effective_date", "Not specified")),
        "relevance": item.get("summary", item.get("description", "")),
        "url": item.get("url", "")
    }

def retrieve(question: str, jurisdiction: str):
    terms = set(re.findall(r"[a-zA-Z]{3,}", question.lower()))
    scored = []
    for item in KNOWLEDGE:
        text = (
            item["title"] + " " + item["summary"] + " " + item["category"]
        ).lower()
        score = sum(1 for t in terms if t in text)
        if jurisdiction.lower() in text:
            score += 2
        if score:
            scored.append((score,item))
    scored.sort(key=lambda x:x[0], reverse=True)
    return [x[1] for x in scored[:4]]

@app.post("/ask")
def ask(req: AskRequest):
    q = req.question.strip()
    if not q:
        return {"answer":"Please provide a question.","confidence":"Low","next_steps":[],"sources":[],"disclaimer":"Informational guidance only."}

    hits = retrieve(q, req.jurisdiction)
    lower=q.lower()

    if not hits:
        return {
            "answer":"I could not find sufficient matching evidence in the current curated prototype knowledge base. I am abstaining rather than inventing an answer.",
            "confidence":"Low",
            "next_steps":["Refine the question with product category, jurisdiction and the specific IP/regulatory issue.","Escalate to a qualified human facilitator for a case-specific assessment."],
            "sources":[],
            "disclaimer":"The prototype uses a limited local knowledge base. Production deployment should use a version-tracked authoritative corpus."
        }

    # Demo source-grounded synthesis. Replace this block with an LLM/RAG generator in production.
    if "patent" in lower or "patentable" in lower or "novel" in lower:
        answer=("For a preliminary patentability review, focus first on what is technically new and then perform a prior-art search. "
                "For Ayurveda-related subject matter, also check whether the claimed knowledge or material is already disclosed in relevant traditional-knowledge or other prior-art sources. "
                "The result here is an indicator, not a final patentability determination.")
        steps=["Define the novel technical features.","Search patent and non-patent prior art.","Check traditional-knowledge/prior-art pointers where relevant.","Obtain a professional patentability opinion before filing."]
    elif "trademark" in lower or "brand" in lower:
        answer=("A trademark strategy is primarily about protecting a distinctive brand identifier for specified goods or services. "
                "A clearance search should be done before adoption or filing, and the correct classes/territories should be selected.")
        steps=["Define the proposed mark and goods/services.","Conduct a clearance search.","Select appropriate classes and jurisdiction.","File and monitor the application under the applicable procedure."]
    elif "abs" in lower or "nagoya" in lower or "biological" in lower:
        answer=("If the innovation uses biological resources or associated traditional knowledge, determine whether access-and-benefit-sharing obligations apply. "
                "The exact obligations depend on the source, access history and applicable national/international framework.")
        steps=["Record biological-resource origin and access history.","Identify associated traditional knowledge.","Check the applicable national ABS framework.","Seek specialist advice if benefit-sharing or permissions may apply."]
    elif "regulat" in lower or "medicine" in lower or "cosmetic" in lower or "nutraceutical" in lower:
        answer=("Regulatory requirements depend heavily on how the product is classified and what it is intended to do. "
                "Start with product category, ingredients, dosage form and intended use, then map to the applicable authority and current requirements.")
        steps=["Capture formulation and intended use.","Classify the product.","Identify the competent authority and current rules.","Prepare applicable evidence/documents and maintain compliance."]
    else:
        answer=("Based on the current evidence set, this question should be approached by identifying the jurisdiction, product category and applicable IP/regulatory framework first. "
                "The cited knowledge items below provide the starting evidence for a more specific analysis.")
        steps=["Specify the jurisdiction.","Specify product/formulation category.","Review the cited sources.","Escalate if the evidence is insufficient or the matter is case-specific."]

    src=[source_record(h) for h in hits]
    return {"answer":answer,"confidence":"Medium","next_steps":steps,"sources":src,
            "disclaimer":"Preliminary informational guidance only; not legal advice, regulatory approval, certification or a final patentability determination."}


def match_ingredients(raw_text: str):
    text = raw_text.lower()
    matches = []
    for item in INGREDIENTS:
        if any(k.lower() in text for k in item["keywords"]):
            matches.append(item)
    return matches

@app.get("/ingredients")
def ingredients(q: Optional[str] = None):
    if not q:
        return {"items": INGREDIENTS}
    terms = [x for x in re.findall(r"[a-zA-Z]{3,}", q.lower())]
    items = [
        x for x in INGREDIENTS
        if any(t in (x["name"] + " " + " ".join(x["aliases"])).lower() for t in terms)
    ]
    return {"items": items}

@app.post("/classify")
def classify(req: FormulationRequest):
    text_all=(req.name+" "+req.ingredients+" "+req.intended_use+" "+req.dosage_form).lower()
    matched = match_ingredients(text_all)

    if any(x in text_all for x in ["cosmetic","cream","skin","shampoo","soap"]):
        category="Cosmetic"
        regulatory="Confirm cosmetic classification and applicable safety, labeling and manufacturing requirements for the selected jurisdiction."
    elif any(x in text_all for x in ["nutraceutical","food","nutrition","beverage","supplement","aahar"]):
        category="Ayurveda-Aahar / nutraceutical"
        regulatory="Confirm food/nutraceutical classification, permitted ingredients, claims and labeling requirements."
    elif any(x in text_all for x in ["new drug","clinical","novel drug"]):
        category="New / non-classical drug"
        regulatory="A new/non-classical medicinal product may require additional evidence and approval steps; confirm the current competent-authority pathway."
    elif "phytopharma" in text_all:
        category="Phytopharmaceutical"
        regulatory="Confirm phytopharmaceutical-specific requirements and evidence pathway with the competent authority."
    elif req.novelty.lower().startswith("novel") or "proprietary" in text_all:
        category="Proprietary medicine"
        regulatory="Confirm the proprietary-medicine route and current manufacturing, evidence and licensing requirements."
    else:
        category="Classical / generic medicine"
        regulatory="Confirm whether the formulation and intended use fall within the applicable classical/generic medicine pathway."

    ingredient_notes = []
    tk = req.novelty.lower().startswith("traditional") or bool(matched)
    for item in matched:
        ingredient_notes.append({
            "name": item["name"],
            "part_used": item["part_used"],
            "aliases": item["aliases"],
            "traditional_context": item["traditional_context"],
            "ip_flag": item["ip_flag"],
            "abs_flag": item["abs_flag"],
            "regulatory_flag": item["regulatory_flag"],
            "common_forms": item["common_forms"]
        })

    if matched:
        abs_text = "Matched ingredient(s) have traditional/biological-resource context. Review provenance and whether applicable ABS requirements are triggered."
        ip = "Because one or more known traditional ingredients were detected, review traditional knowledge and prior art before asserting novelty. A novel technical formulation/process may still require a separate patentability analysis."
    else:
        abs_text = "No ingredient in the prototype database was confidently matched. Enter scientific/common names and review provenance for any biological resource."
        ip = "Review whether the proposed formulation or process contains a new technical contribution and conduct a prior-art search."

    return {
        "category":category,
        "confidence":"Medium" if matched else "Low",
        "explanation":"The prototype combines formulation rules with an ingredient knowledge layer. It is a navigation aid, not a legal or regulatory determination.",
        "regulatory":regulatory,
        "ip":ip,
        "abs":abs_text,
        "matched_ingredients":ingredient_notes,
        "next_steps":[
            "Verify classification against current applicable rules.",
            "Confirm ingredient identity, plant part, source and provenance.",
            "Review traditional-knowledge/prior-art considerations for matched ingredients.",
            "Map the classification to the regulatory journey.",
            "Review the appropriate IP protection route."
        ],
        "sources":[
            source_record(x) for x in SOURCES[:3]
        ]
    }

@app.post("/ip-check")
def ip_check(req: IPRequest):
    risk="Low"
    if req.similar_product=="Yes" or req.traditional_knowledge=="Yes":
        risk="Medium"
    if not req.novelty.strip():
        risk="High"

    routes=[
        {"name":"Patent","status":"Review","reason":"Potentially relevant where a new technical solution satisfies applicable patentability requirements; prior-art search is essential."},
        {"name":"Trademark","status":"Review","reason":"Relevant for a distinctive brand, product name or logo; clearance and class selection are needed."},
        {"name":"Trade Secret","status":"Possible","reason":"May help protect confidential know-how when secrecy can realistically be maintained."},
        {"name":"Design","status":"Case-dependent","reason":"May be relevant to protect qualifying visual/aesthetic features of a product."},
        {"name":"Copyright","status":"Case-dependent","reason":"May protect qualifying original expression such as artwork, documentation or software, rather than an underlying idea."},
        {"name":"GI","status":"Case-dependent","reason":"Relevant only where the product and geographical linkage satisfy the applicable GI framework."}
    ]
    checks=["Run a structured prior-art search.","Check TK/prior-art databases where relevant.","Document dates, inventorship and development records.","Assess the correct IP route before public disclosure."]
    if req.traditional_knowledge=="Yes":
        checks.insert(1,"Record the source and nature of traditional knowledge and examine applicable protection/ABS considerations.")
    return {
        "risk":risk,
        "summary":"The prototype finds preliminary indicators only. A high-attention result means more evidence is needed; it does not mean the innovation is unprotectable.",
        "routes":routes,"checks":checks,
        "sources":[source_record(x) for x in SOURCES[:4]]
    }

@app.post("/regulatory")
def regulatory(req: RegulatoryRequest):
    common=[
        {"title":"Confirm classification","detail":"Verify the selected product category using the current applicable rules and definitions."},
        {"title":"Map competent authority","detail":"Identify the authority, licence/registration route and current procedural requirements."},
        {"title":"Prepare evidence","detail":"Compile formulation, ingredient, quality, safety, efficacy, labeling and other applicable records."},
        {"title":"Check IP and ABS","detail":"Review IP strategy and traditional-knowledge/biological-resource obligations where relevant."},
        {"title":"Submit / comply","detail":"Follow the current authority procedure and maintain ongoing compliance after approval/registration where applicable."}
    ]
    if req.jurisdiction != "India":
        common[1]["detail"]="International requirements differ by jurisdiction. Select the target country/region and verify its current competent authority and procedure."
    return {
        "title":f"{req.category} — preliminary pathway",
        "jurisdiction":req.jurisdiction,
        "summary":"Use this as a navigation checklist, not as a regulatory approval decision.",
        "steps":common,
        "sources":[source_record(x) for x in SOURCES[:4]],
        "disclaimer":"Requirements can change. Verify current official rules before taking regulatory action."
    }

@app.get("/knowledge")
def knowledge(q: Optional[str]=None):
    items=KNOWLEDGE
    if q:
        terms=[x for x in re.findall(r"[a-zA-Z]{3,}",q.lower())]
        items=[x for x in KNOWLEDGE if any(t in (x["title"]+" "+x["summary"]+" "+x["category"]).lower() for t in terms)]
    return {"items":items}

@app.get("/sources")
def sources():
    return {"sources":SOURCES}
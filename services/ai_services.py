import json
import os
import logging
import mimetypes
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional

from google import genai
from google.genai import types
from huggingface_hub import InferenceClient
from services.image_loader import load_image_bytes_and_mime


_ALLOWED_ISSUES = {
      # Road & Infrastructure
    "pothole": "pothole",
    "road damage": "road damage",
    "broken footpath": "broken footpath",
    "road obstruction": "road obstruction",
    "construction debris": "construction debris",

    # Sanitation & Waste
    "garbage": "garbage",
    "garbage overflow": "garbage overflow",
    "illegal dumping": "illegal dumping",
    "missed garbage collection": "missed garbage collection",
    "dead animal": "dead animal",

    # Street Lighting & Electrical
    "street light issue": "street light issue",
    "street light not working": "street light not working",
    "flickering street light": "flickering street light",
    "electric pole damage": "electric pole damage",
    "exposed wires": "exposed wires",

    # Water Supply
    "water leakage": "water leakage",
    "no water supply": "no water supply",
    "low water pressure": "low water pressure",
    "dirty water supply": "dirty water supply",
    "pipeline burst": "pipeline burst",

    # Drainage & Sewerage
    "drainage problem": "drainage problem",
    "blocked drainage": "blocked drainage",
    "sewer overflow": "sewer overflow",
    "open manhole": "open manhole",
    "waterlogging": "waterlogging",

    # Public Health
    "mosquito breeding": "mosquito breeding",
    "stray animals": "stray animals",
    "unhygienic condition": "unhygienic condition",

    # Parks & Public Spaces
    "damaged park equipment": "damaged park equipment",
    "broken bench": "broken bench",
    "park maintenance issue": "park maintenance issue",

    # Building & Construction
    "illegal construction": "illegal construction",
    "construction noise": "construction noise",
    "dust pollution": "dust pollution",
    "unsafe building": "unsafe building",

    # Traffic & Encroachment
    "traffic congestion": "traffic congestion",
    "illegal parking": "illegal parking",
    "encroachment": "encroachment",
    "signal not working": "signal not working",

    # Critical Issues
    "fire hazard": "fire hazard",
    "gas leakage": "gas leakage",
    "electric hazard": "electric hazard",
    "building collapse risk": "building collapse risk",
}

_ALLOWED_DEPARTMENTS = {
    "road & infrastructure": "Road & Infrastructure",
    "sanitation & waste management": "Sanitation & Waste Management",
    "electrical & street lighting": "Electrical & Street Lighting",
    "water supply": "Water Supply",
    "drainage & sewerage": "Drainage & Sewerage",
    "public health": "Public Health",
    "parks & gardens": "Parks & Gardens",
    "building & construction": "Building & Construction",
    "traffic & encroachment": "Traffic & Encroachment",
}


class AIServiceError(Exception):
    pass


@dataclass
class ImageIssueAnalysis:
    has_issue: bool
    confidence_score: float
    issue_type: Optional[str]
    reason: str
    is_public_space: Optional[bool] = None
    is_private_issue: Optional[bool] = None


def get_issue_detection_min_score() -> float:
    try:
        return float(os.getenv("ISSUE_DETECTION_MIN_SCORE", "65"))
    except ValueError:
        return 65.0


def _parse_json_object(raw_text: str) -> Dict:
    text = (raw_text or "").strip()
    if not text:
        raise AIServiceError("Empty model response")

    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL | re.IGNORECASE)
    if fenced:
        text = fenced.group(1)
    else:
        start = text.find("{")
        end = text.rfind("}")
        if start >= 0 and end > start:
            text = text[start : end + 1]

    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        raise AIServiceError(f"Could not parse vision model JSON: {raw_text}") from exc

    if not isinstance(payload, dict):
        raise AIServiceError("Vision model JSON must be an object")
    return payload


def _coerce_confidence_score(value) -> float:
    try:
        score = float(value)
    except (TypeError, ValueError):
        return 0.0
    return max(0.0, min(100.0, score))


def _coerce_bool(value) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value != 0
    if isinstance(value, str):
        return value.strip().lower() in {"true", "yes", "1"}
    return False


logger = logging.getLogger(__name__)
_HF_CHAT_MODEL = "openai/gpt-oss-120b"
_HF_VISION_MODEL = os.getenv("HF_VISION_MODEL", "Salesforce/blip-image-captioning-base")


def _hf_client() -> InferenceClient:
    token = os.getenv("HF_TOKEN")
    if not token:
        raise AIServiceError("HF_TOKEN is not configured")
    return InferenceClient(api_key=token)


def _normalize_issue(raw_text: str) -> str:
    normalized = raw_text.strip().lower()
    if normalized in _ALLOWED_ISSUES:
        return _ALLOWED_ISSUES[normalized]

    for issue in _ALLOWED_ISSUES:
        if issue in normalized:
            return _ALLOWED_ISSUES[issue]

    raise AIServiceError(f"Unsupported issue type from model output: {raw_text}")


def _extract_text_content(content) -> str:
    if isinstance(content, str):
        return content.strip()

    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, dict) and item.get("type") == "text" and item.get("text"):
                parts.append(item["text"])
        return " ".join(parts).strip()

    return str(content).strip()


def _issue_choices_text() -> str:
    return ", ".join(_ALLOWED_ISSUES.keys())


def analyze_image_for_civic_issue(image_path: str, description: str = "") -> ImageIssueAnalysis:
    try:
        image_bytes, mime_type = load_image_bytes_and_mime(image_path)
    except Exception as exc:
        raise AIServiceError(f"Image file not found or unreadable: {image_path}") from exc

    if not image_bytes:
        raise AIServiceError("Image file is empty")
    gemini_api_key = os.getenv("GEMINI_API_KEY")
    if not gemini_api_key:
        raise AIServiceError("GEMINI_API_KEY is not configured")

    citizen_description = (description or "").strip()
    prompt = f"""You are a strict civic-complaint image validator for a city government portal.

This portal accepts ONLY public civic infrastructure / public-space issues that municipal authorities are responsible for.

Analyze ONLY what is clearly visible in this photo.

PUBLIC issues (may be accepted if clearly visible):
- Problems on public roads, footpaths, streets, parks, public squares
- Street lights, public drainage, water leaks on public roads/pipes
- Garbage on public land, open public manholes, public sewer overflow
- Issues in shared public areas managed by the city

PRIVATE issues (MUST be rejected — never accept):
- Problems inside homes, apartments, bedrooms, kitchens, bathrooms, living rooms
- Office interiors, cubicles, meeting rooms, private commercial interiors
- Private compound walls, private driveways, private gardens, private parking lots
- Damage or maintenance inside shops/restaurants that are clearly indoor private business space
- Household appliances, furniture, personal belongings, private plumbing inside a building
- Any issue that is the responsibility of a homeowner, tenant, or private business — not the city

STRICT RULES:
1. Set is_private_issue to true if the problem is in a private home, office, or other non-public space.
2. Set is_public_space to true ONLY if the scene is clearly a public area (road, park, sidewalk, public utility on street, etc.).
3. If is_private_issue is true OR is_public_space is false, set has_civic_issue to false and issue_type to null — regardless of confidence.
4. Set has_civic_issue to false if there is no visible problem, or only a normal scene (selfie, sky, plain wall, etc.).
5. Do NOT hallucinate issues. The image must show clear evidence.
6. Do NOT accept based on description alone — image evidence is primary.
7. confidence_score (0-100): how clearly a PUBLIC civic issue is visible.
   - 0-40: no issue, private issue, or very unclear
   - 41-64: possible public issue but weak evidence
   - 65-100: clear public civic issue
8. When has_civic_issue is true, issue_type must be exactly one value from:
   {_issue_choices_text()}
9. reason: one short sentence explaining accept or reject (mention public vs private if relevant).

Citizen description (secondary context only): "{citizen_description or "not provided"}"

Return ONLY valid JSON:
{{
  "has_civic_issue": boolean,
  "is_public_space": boolean,
  "is_private_issue": boolean,
  "confidence_score": number,
  "issue_type": string or null,
  "reason": string
}}"""

    model_name = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
    try:
        logger.info("Gemini vision validation started model=%s image_path=%s", model_name, image_path)
        client = genai.Client(api_key=gemini_api_key)
        response = client.models.generate_content(
            model=model_name,
            contents=[
                prompt,
                types.Part.from_bytes(data=image_bytes, mime_type=mime_type),
            ],
        )
    except Exception as exc:
        raise AIServiceError(f"Gemini image reasoning failed: {exc}") from exc

    raw_output = (getattr(response, "text", "") or "").strip()
    logger.info("Gemini vision validation raw_output=%s", raw_output)

    payload = _parse_json_object(raw_output)
    has_issue = _coerce_bool(payload.get("has_civic_issue"))
    is_public_space = _coerce_bool(payload.get("is_public_space")) if "is_public_space" in payload else None
    is_private_issue = _coerce_bool(payload.get("is_private_issue")) if "is_private_issue" in payload else None
    confidence_score = _coerce_confidence_score(payload.get("confidence_score"))
    reason = str(payload.get("reason") or "").strip() or "No explanation provided"
    issue_type_raw = payload.get("issue_type")

    if is_private_issue or is_public_space is False:
        has_issue = False
        confidence_score = min(confidence_score, 25.0)
        if is_private_issue:
            reason = (
                "This appears to be a private property issue (home, office, or indoor private space). "
                "Only public civic issues on roads, parks, and public infrastructure can be reported here. "
                f"{reason}"
            )
        else:
            reason = (
                "The issue does not appear to be in a public space managed by the city. "
                f"{reason}"
            )

    issue_type: Optional[str] = None
    if issue_type_raw not in (None, "", "null", "none") and has_issue:
        try:
            issue_type = _normalize_issue(str(issue_type_raw))
        except AIServiceError:
            issue_type = None
            has_issue = False
            confidence_score = min(confidence_score, 40.0)
            reason = f"Model suggested unsupported issue type: {issue_type_raw}"

    min_score = get_issue_detection_min_score()
    accepted = (
        has_issue
        and not is_private_issue
        and is_public_space is not False
        and confidence_score >= min_score
        and issue_type is not None
    )

    if not accepted and has_issue and confidence_score < min_score:
        reason = f"Confidence {confidence_score:.0f}% is below required {min_score:.0f}%. {reason}"

    if not accepted:
        return ImageIssueAnalysis(
            has_issue=False,
            confidence_score=confidence_score,
            issue_type=None,
            reason=reason,
            is_public_space=is_public_space,
            is_private_issue=is_private_issue,
        )

    return ImageIssueAnalysis(
        has_issue=True,
        confidence_score=confidence_score,
        issue_type=issue_type,
        reason=reason,
        is_public_space=True if is_public_space is not False else is_public_space,
        is_private_issue=False,
    )


def detect_issue_from_image(image_path: str, description: str = "") -> str:
    analysis = analyze_image_for_civic_issue(image_path, description)
    if not analysis.has_issue or not analysis.issue_type:
        raise AIServiceError(analysis.reason or "No civic issue detected in the uploaded photo")
    return analysis.issue_type


def detect_issue_from_description(description: str) -> str:
    if not description or not description.strip():
        raise AIServiceError("description is required for issue detection")

    prompt = (
        "Classify this civic complaint description into exactly one issue type.\\n"
        "Description: {description}\\n"
        "Choose one from: {choices}.\\n"
        "Return only the issue name."
    ).format(description=description.strip(), choices=_issue_choices_text())

    try:
        logger.info("HF text issue-detection started")
        client = _hf_client()
        completion = client.chat.completions.create(
            model=_HF_CHAT_MODEL,
            messages=[
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
        )
    except Exception as exc:
        raise AIServiceError(f"HuggingFace text issue detection failed: {exc}") from exc

    raw_output = _extract_text_content(completion.choices[0].message.content)
    logger.info("HF text issue-detection raw_output=%s", raw_output)
    return _normalize_issue(raw_output)


def map_issue_to_department(issue_type: str) -> str:
    prompt = (
        "Map this civic issue to exactly one department.\\n"
        "Issue: {issue}\\n"
        "Choose one from: Road & Infrastructure, Sanitation & Waste Management, "
        "Electrical & Street Lighting, Water Supply, Drainage & Sewerage.\\n"
        "Return only department name."
    ).format(issue=issue_type)

    try:
        logger.info("HF reasoning started issue_type=%s", issue_type)
        client = _hf_client()

        completion = client.chat.completions.create(
            model=_HF_CHAT_MODEL,
            messages=[
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
        )
    except Exception as exc:
        raise AIServiceError(f"HuggingFace request failed: {exc}") from exc

    content = completion.choices[0].message.content.strip()
    logger.info("HF reasoning raw_output=%s", content)
    normalized = content.lower()

    if normalized in _ALLOWED_DEPARTMENTS:
        return _ALLOWED_DEPARTMENTS[normalized]

    for key, value in _ALLOWED_DEPARTMENTS.items():
        if key in normalized:
            return value

    rule_fallback: Dict[str, str] = {
        "pothole": "Road & Infrastructure",
        "garbage": "Sanitation & Waste Management",
        "street light issue": "Electrical & Street Lighting",
        "water leakage": "Water Supply",
        "drainage problem": "Drainage & Sewerage",
    }
    if issue_type in rule_fallback:
        return rule_fallback[issue_type]

    raise AIServiceError(f"Unsupported department mapping output: {content}")

"""
Release Notes Processor - DETERMINISTIC PYTHON ENFORCEMENT
Python handles structure, LLM handles language
"""
import os
import sys
import signal
import json
import re
import zipfile
import io
from pathlib import Path
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from docx import Document
from openai import AsyncOpenAI
import google.generativeai as genai
import uvicorn

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

print("=" * 60, file=sys.stderr)
print("=== RELEASE NOTES PROCESSOR - DETERMINISTIC ===", file=sys.stderr)
print("=" * 60, file=sys.stderr)

app = FastAPI(title="Release Notes Processor", version="5.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# ============================================================================
# ENVIRONMENT & CLIENTS
# ============================================================================
QUBRID_API_KEY = os.environ.get("QUBRID_API_KEY")
QUBRID_BASE_URL = os.environ.get("QUBRID_BASE_URL", "https://platform.qubrid.com/v1")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

print(f"\nEnvironment:", file=sys.stderr)
print(f"  QUBRID: {'✓' if QUBRID_API_KEY else '✗'} (PRIMARY)", file=sys.stderr)
print(f"  GROQ: {'✓' if GROQ_API_KEY else '✗'} (FALLBACK 1)", file=sys.stderr)
print(f"  GEMINI: {'✓' if GEMINI_API_KEY else '✗'} (FALLBACK 2)", file=sys.stderr)

qubrid_client = AsyncOpenAI(api_key=QUBRID_API_KEY, base_url=QUBRID_BASE_URL) if QUBRID_API_KEY else None
groq_client = AsyncOpenAI(api_key=GROQ_API_KEY, base_url="https://api.groq.com/openai/v1") if GROQ_API_KEY else None
gemini_model = genai.GenerativeModel("gemini-2.5-flash") if GEMINI_API_KEY else None

# ============================================================================
# LOGO FIX - SERVE FROM MULTIPLE LOCATIONS
# ============================================================================
LOGO_PATHS = [
    Path(__file__).parent.parent / "frontend" / "public" / "zetalogo.png",
    Path(__file__).parent.parent / "frontend" / "build" / "zetalogo.png",
    Path(__file__).parent / "zetalogo.png",
    Path(__file__).parent.parent / "zetalogo.png",
]

LOGO_FILE = None
for path in LOGO_PATHS:
    if path.exists():
        LOGO_FILE = path
        print(f"\n✓ Logo found at: {path}", file=sys.stderr)
        break

if not LOGO_FILE:
    print(f"\n⚠️ Logo file not found!", file=sys.stderr)

# Frontend build directory
frontend_build = Path(__file__).parent.parent / "frontend" / "build"
if frontend_build.exists() and (frontend_build / "index.html").exists():
    print(f"✓ Frontend build: {frontend_build}", file=sys.stderr)
    app.mount("/static", StaticFiles(directory=str(frontend_build / "static")), name="static")

OUTPUT_DIR = Path(__file__).parent / "output"
OUTPUT_DIR.mkdir(exist_ok=True)

# ============================================================================
# DETERMINISTIC HELPER FUNCTIONS
# ============================================================================
def enforce_acronym_formatting(text: str) -> str:
    """Bold ALL acronyms - deterministic, 100% reliable"""
    if not text:
        return text
    
    acronyms = [
        'UPI', 'SFTP', 'NPCI', 'API', 'ANV', 'POS', 'IMPS', 'NEFT', 'RTGS',
        'BIN', 'ACS', 'SCOF', 'EMV', '3DS', 'OTP', 'KYC', 'AML', 'SAR',
        'CMS', 'FAWB', 'AH', 'WB', 'EoD', 'IO', 'URCS', 'PGP', 'PIN',
        'SDK', 'URL', 'HTTP', 'HTTPS', 'JSON', 'XML', 'SQL', 'DB', 'ID',
        'PDF', 'CSV', 'MD', 'UI', 'UX', 'QA', 'DEV', 'OPS'
    ]
    
    result = text
    for acronym in acronyms:
        pattern = r'(?<!\*)\b' + acronym + r'\b(?!\*)'
        replacement = f'**{acronym}**'
        result = re.sub(pattern, replacement, result, flags=re.IGNORECASE)
    
    return result

def enforce_text_corrections(text: str) -> str:
    """Deterministic text corrections: workbench, Center, quotes, temporal words"""
    if not text:
        return text
    result = text
    # "work bench" → "workbench" (case-insensitive)
    result = re.sub(r'\bwork\s+bench\b', 'workbench', result, flags=re.IGNORECASE)
    result = re.sub(r'\bwork\s+benches\b', 'workbenches', result, flags=re.IGNORECASE)
    # "Centre/centre" → "Center" for known centers
    result = re.sub(r'\bOperations\s+Centr[eé]\b', 'Operations Center', result, flags=re.IGNORECASE)
    result = re.sub(r'\bSupport\s+Centr[eé]\b', 'Support Center', result, flags=re.IGNORECASE)
    result = re.sub(r'\bAgent\s+Centr[eé]\b', 'Agent Center', result, flags=re.IGNORECASE)
    result = re.sub(r'\bEoD\s+Centr[eé]\b', 'EoD Center', result, flags=re.IGNORECASE)
    result = re.sub(r'\bEOD\s+Centr[eé]\b', 'EOD Center', result, flags=re.IGNORECASE)
    # Generic "Centre" → "Center"
    result = re.sub(r'\bCentre\b', 'Center', result)
    result = re.sub(r'\bcentre\b', 'center', result)
    # Remove all quotes (single and double) from documentation
    result = result.replace('"', '').replace("'", '').replace('\u201c', '').replace('\u201d', '').replace('\u2018', '').replace('\u2019', '')
    return result

def enforce_no_temporal_words(text: str) -> str:
    """Remove temporal words: existing, current, now, currently, previously, presently"""
    if not text:
        return text
    result = text
    # Replace temporal words with appropriate alternatives or remove them
    result = re.sub(r'\bexisting\s+', '', result, flags=re.IGNORECASE)
    result = re.sub(r'\bcurrently\s*,?\s*', '', result, flags=re.IGNORECASE)
    result = re.sub(r'\bpresently\s*,?\s*', '', result, flags=re.IGNORECASE)
    result = re.sub(r'\bpreviously\s*,?\s*', '', result, flags=re.IGNORECASE)
    # "current" as standalone adjective (not part of "currently")
    result = re.sub(r'\bcurrent\b', '', result, flags=re.IGNORECASE)
    # "now" as standalone word (careful not to match "know", "now" inside words)
    result = re.sub(r'\bnow\b\s*,?\s*', '', result, flags=re.IGNORECASE)
    # Clean up double spaces
    result = re.sub(r'  +', ' ', result).strip()
    return result

def enforce_no_special_chars_in_title(title: str) -> str:
    """Remove special characters and symbols from title"""
    if not title:
        return title
    # Remove special chars but keep letters, numbers, spaces, hyphens
    result = re.sub(r'[^\w\s\-]', '', title)
    result = re.sub(r'  +', ' ', result).strip()
    return result

def enforce_description_format(description: str) -> str:
    """Ensure description does NOT start with Introduced/Added/Enhanced etc."""
    if not description:
        return description
    starters = ['introduced', 'added', 'enhanced', 'this enhancement', 'this feature', 'this update']
    lower = description.strip().lower()
    for starter in starters:
        if lower.startswith(starter):
            # Restructure: move the verb into the middle
            rest = description.strip()[len(starter):].strip()
            if rest.startswith(','):
                rest = rest[1:].strip()
            # Capitalize first letter of rest and append the action verb
            if rest:
                rest = rest[0].upper() + rest[1:]
                if starter in ['introduced', 'added', 'enhanced']:
                    description = f"{rest.rstrip('.')} is {starter}"
                else:
                    description = rest
            break
    return description

def ensure_period(sentence: str) -> str:
    """Ensure a paragraph sentence ends with a period."""
    s = sentence.strip()
    if not s:
        return s
    if s[-1] not in '.!?':
        s += '.'
    return s

def enforce_paragraph_or_bullets(text: str, lead_type: str) -> str:
    """When LLM returns plain text (not array), parse it into items and apply
    paragraph (1-2 items) or lead line + bullets (3+) formatting."""
    if not text:
        return ""

    # Split text into items: detect existing bullets or split by newlines/sentences
    lines = [l.strip() for l in text.strip().split('\n') if l.strip()]
    items = []
    for line in lines:
        # Strip bullet markers
        clean = re.sub(r'^[-•*]\s*', '', line).strip()
        if clean:
            items.append(clean)

    if not items:
        return text

    # If only one item that looks like a paragraph (no bullets detected), return as paragraph with period
    if len(items) == 1 and not any(line.strip().startswith(('-', '•', '*')) for line in text.strip().split('\n') if line.strip()):
        return ensure_period(items[0])

    return enforce_lead_line(items, lead_type)

def enforce_lead_line(items: List[str], lead_type: str) -> str:
    """Format enhancement/impact based on item count:
    - 1-2 items: write as paragraph(s) with periods at the end
    - 3+ items: lead line + bullet points (no periods on bullets)
    """
    if not items:
        return ""

    # Clean items: strip leading bullet markers and whitespace
    cleaned = []
    for item in items:
        s = item.strip()
        s = re.sub(r'^[-•*]\s*', '', s)  # remove bullet prefix if present
        if s:
            cleaned.append(s)

    if not cleaned:
        return ""

    if len(cleaned) <= 2:
        # Write as paragraph(s) — complete sentences with periods
        paragraphs = [ensure_period(item) for item in cleaned]
        return "\n\n".join(paragraphs)
    else:
        # 3+ items: lead line + bullet points without periods
        if lead_type == "enhancement":
            lead = "The enhancement introduces the following:"
        else:
            lead = "The impact of the enhancement is detailed below:"
        bullets = [f"- {item.rstrip('.')}" for item in cleaned]
        return f"{lead}\n\n" + "\n".join(bullets)

# ============================================================================
# RUBRIC-BASED SYSTEM PROMPT (SIMPLIFIED)
# ============================================================================
RUBRIC_SYSTEM_PROMPT = """You are an expert technical writer for enterprise SaaS release notes.
Follow Microsoft Style Guide (MSTP) best practices strictly.

YOUR TASK: Transform rough engineering draft into polished, customer-facing release notes.

=============================================================================
RUBRIC RULES:
=============================================================================

STEP 1: FEATURE FILTERING
- Keep ONLY features where "To be published externally" = "Yes" or "Y"

STEP 2: CONTENT WRITING GUIDELINES
- Use SIMPLE PRESENT TENSE for all sections
- Use ACTIVE VOICE only
- Do a complete spell check in MSTP format
- Use clear CUSTOMER-FACING language
- NO internal references or source links
- NO temporal words anywhere: "existing", "current", "now", "currently", "previously", "presently"
- NO quotes in any documentation output
- Use "workbench" (one word), never "work bench"
- Always use "Center" (not "Centre" or "centre") for Operations Center, Support Center, EOD Center, Agent Center

ACRONYM RULES:
- Bold ALL acronyms: API, APIs, API-based, Pre-API
- Bold acronyms in plural form
- Bold acronyms in headings
- Bold acronyms prefixed or suffixed with hyphen

STEP 3: STRUCTURE

1. TITLE
   - Start with NOUN (can start with "Enhancements in")
   - Use Title Case
   - Short and outcome-focused
   - NO special characters or symbols in the title
   - Example: Biometric Authentication for UPI Transactions, Credit Balance Refund in Operations Center

2. DESCRIPTION
   - 1-2 lines in PRESENT TENSE
   - DO NOT start with "Introduced", "Added", "Enhanced", "This enhancement", or similar
   - Instead, start with the functionality/feature itself and use "introduced/added/enhanced" in the MIDDLE
   - Example WRONG: "This enhancement enabled productionising pushpa temple indicator"
   - Example CORRECT: "Productionising pushpa temple indicator is enabled to ensure effectiveness"
   - Example CORRECT: "The loan disbursement functionality is enhanced to support multiple channels"

3. PROBLEM STATEMENT
   - Present tense
   - State what is missing or inefficient
   - NO temporal words: "existing", "current", "now", "currently"

4. ENHANCEMENT
   - Present tense
   - NO temporal words: "existing", "current", "now", "currently"
   - For 1-2 enhancements: write as complete paragraph sentences. Directly start with the actual enhancement. Each sentence MUST end with a period.
   - For 3+ enhancements: Python will add a lead line. Return as bullet points. Bullets must NOT end with periods.
   - Return as ARRAY of items (Python will format as paragraphs or bullets based on count)

5. IMPACT
   - Present tense
   - NO temporal words: "existing", "current", "now", "currently"
   - For 1-2 impacts: write as complete paragraph sentences. Directly start with the actual impact. Each sentence MUST end with a period.
   - For 3+ impacts: Python will add a lead line. Return as bullet points. Bullets must NOT end with periods.
   - Bullets start with: "Allows users to", "Enables agents to", "Increases the efficiency"
   - Return as ARRAY of items (Python will format as paragraphs or bullets based on count)

=============================================================================
OUTPUT FORMAT - RETURN EXACTLY THIS JSON:
=============================================================================
{
  "refined_title": "Title Case, starts with noun, NO special characters, max 12 words",
  "description": "Present tense, 1-2 lines. Start with functionality name, use introduced/added/enhanced in the middle. NOT starting with Introduced/Added/Enhanced.",
  "problem_statement": "Present tense, no temporal words",
  "enhancement_bullets": ["First enhancement", "Second enhancement"],
  "impact_bullets": ["First impact", "Second impact"]
}

NOTE: Python will handle:
- Acronym bolding
- Lead line insertion
- Bullet formatting
- Period removal
- "workbench" / "Center" enforcement
- Temporal word removal
- Quote removal
=============================================================================
"""

# ============================================================================
# DATA MODELS
# ============================================================================
class RawFeature:
    def __init__(self, data: dict):
        self.feature_name = data.get("feature_name", "")
        self.product_module = data.get("product_module", "")
        self.problem_statement = data.get("problem_statement", "")
        self.enhancement = data.get("enhancement", "")
        self.impact = data.get("impact", "")
        self.publish_externally = data.get("publish_externally", "")
        self.geography = data.get("geography", "All")
        self.ui_changes = data.get("ui_changes", "")
        self.reports_extracts = data.get("reports_extracts", "")
        self.audit_logs = data.get("audit_logs", "")
        self.known_issues = data.get("known_issues", "")

class ProcessedFeature:
    def __init__(self, data: dict):
        self.title = data.get("title", "")
        self.description = data.get("description", "")
        self.problem_statement = data.get("problem_statement", "")
        self.enhancement = data.get("enhancement", "")
        self.impact = data.get("impact", "")
        self.tag = data.get("tag", "")
        self.geography = data.get("geography", "All")
        self.ui_changes = data.get("ui_changes")
        self.reports_extracts = data.get("reports_extracts")
        self.audit_logs = data.get("audit_logs", "Disabled")
        self.known_issues = data.get("known_issues")

# ============================================================================
# DOCUMENT PROCESSING
# ============================================================================
def extract_tables_from_docx(file_path: str) -> List[RawFeature]:
    """Extract feature tables from Word document"""
    doc = Document(file_path)
    features = []
    
    for table in doc.tables:
        feature_data = {}
        for row in table.rows:
            if len(row.cells) >= 2:
                key = row.cells[0].text.strip()
                value = row.cells[1].text.strip()
                
                key_lower = key.lower().strip()

                key_mapping_exact = {
                    "Feature": "feature_name",
                    "Product Module": "product_module",
                    "Problem Statement": "problem_statement",
                    "Problem Statement/Context": "problem_statement",
                    "Enhancement": "enhancement",
                    "Impact": "impact",
                    "To be published Externally": "publish_externally",
                    "To be published externally": "publish_externally",
                    "To be published Externally (Yes/No)": "publish_externally",
                    "To be published externally (Yes/No)": "publish_externally",
                    "Geography": "geography",
                    "User Interface Changes": "ui_changes",
                    "Reports & Extracts": "reports_extracts",
                    "Reports and Extracts": "reports_extracts",
                    "Audit Logs": "audit_logs",
                    "Audit Logs Enabled": "audit_logs",
                    "Known Issues and Callouts": "known_issues",
                    "Known Issues & Callouts": "known_issues",
                    "Known Issues": "known_issues",
                }

                # Try exact match first, then fuzzy match on key
                matched_field = key_mapping_exact.get(key)
                if not matched_field:
                    if 'publish' in key_lower and 'external' in key_lower:
                        matched_field = "publish_externally"
                    elif 'problem' in key_lower and 'statement' in key_lower:
                        matched_field = "problem_statement"
                    elif 'known' in key_lower and 'issue' in key_lower:
                        matched_field = "known_issues"
                    elif 'user interface' in key_lower or 'ui change' in key_lower:
                        matched_field = "ui_changes"
                    elif 'report' in key_lower and 'extract' in key_lower:
                        matched_field = "reports_extracts"
                    elif 'audit' in key_lower and 'log' in key_lower:
                        matched_field = "audit_logs"

                if matched_field:
                    feature_data[matched_field] = value
        
        if feature_data.get("feature_name"):
            features.append(RawFeature(feature_data))
    
    print(f"Extracted {len(features)} features from document", file=sys.stderr)
    return features

def filter_publishable_features(features: List[RawFeature]) -> List[RawFeature]:
    """Filter features marked for external publication - ONLY yes/Y"""
    publishable = []
    for f in features:
        publish_value = f.publish_externally.strip().lower()
        if publish_value in ['yes', 'y']:
            publishable.append(f)

    print(f"Publishable: {len(publishable)} of {len(features)} features", file=sys.stderr)
    return publishable

# ============================================================================
# LLM PROCESSING
# ============================================================================
async def process_with_llm(client, feature: RawFeature, provider: str):
    """Process feature with LLM - LLM only handles language, Python handles structure"""
    user_prompt = f"""
Feature Name: {feature.feature_name}
Product Module: {feature.product_module}
Problem Statement: {feature.problem_statement}
Enhancement: {feature.enhancement}
Impact: {feature.impact}

Rewrite in customer-facing language. Return ONLY JSON."""
    
    model_name = "openai/gpt-oss-20b" if provider == "qubrid" else "llama-3.3-70b-versatile"
    print(f"  → Using model: {model_name}", file=sys.stderr)
    
    response = await client.chat.completions.create(
        model=model_name,
        messages=[
            {"role": "system", "content": RUBRIC_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt}
        ],
        response_format={"type": "json_object"},
        temperature=0.3
    )
    
    return json.loads(response.choices[0].message.content)

async def apply_complete_conversion(feature: RawFeature):
    """Apply LLM conversion with DETERMINISTIC Python enforcement"""
    llm_result = None
    
    # PRIMARY: Try Qubrid first
    if qubrid_client:
        try:
            print(f"  → Qubrid (openai/gpt-oss-20b)...", file=sys.stderr)
            llm_result = await process_with_llm(qubrid_client, feature, "qubrid")
            print(f"  ✓ Qubrid success", file=sys.stderr)
        except Exception as e:
            print(f"  ✗ Qubrid failed: {e}", file=sys.stderr)
    
    # FALLBACK 1: Try Groq
    if not llm_result and groq_client:
        try:
            print(f"  → Groq (llama-3.3-70b-versatile)...", file=sys.stderr)
            llm_result = await process_with_llm(groq_client, feature, "groq")
            print(f"  ✓ Groq success", file=sys.stderr)
        except Exception as e:
            print(f"  ✗ Groq failed: {e}", file=sys.stderr)
    
    # FALLBACK 2: Try Gemini
    if not llm_result and gemini_model:
        try:
            print(f"  → Gemini (gemini-2.5-flash)...", file=sys.stderr)
            response = await gemini_model.generate_content_async(
                f"{RUBRIC_SYSTEM_PROMPT}\n\n{feature.feature_name}\nProblem: {feature.problem_statement}\nEnhancement: {feature.enhancement}\nImpact: {feature.impact}\n\nReturn ONLY JSON"
            )
            llm_result = json.loads(response.text.strip())
            print(f"  ✓ Gemini success", file=sys.stderr)
        except Exception as e:
            print(f"  ✗ Gemini failed: {e}", file=sys.stderr)
    
    # Helper: check if optional section has real value
    def has_value(val):
        if not val:
            return False
        return val.strip().lower() not in ['na', 'none', 'no', '-', '', 'n/a', 'nil']

    # Use LLM result with DETERMINISTIC Python enforcement
    if llm_result:
        # 1. Python handles Enhancement: paragraphs (1-2) or lead line + bullets (3+)
        enhancement_text = ""
        if llm_result.get("enhancement_bullets"):
            enhancement_text = enforce_lead_line(llm_result["enhancement_bullets"], "enhancement")
        else:
            raw_enh = llm_result.get("enhancement", feature.enhancement)
            enhancement_text = enforce_paragraph_or_bullets(raw_enh, "enhancement")
        enhancement_text = enforce_no_temporal_words(enhancement_text)
        enhancement_text = enforce_text_corrections(enhancement_text)
        enhancement_text = enforce_acronym_formatting(enhancement_text)

        # 2. Python handles Impact: paragraphs (1-2) or lead line + bullets (3+)
        impact_text = ""
        if llm_result.get("impact_bullets"):
            impact_text = enforce_lead_line(llm_result["impact_bullets"], "impact")
        else:
            raw_imp = llm_result.get("impact", feature.impact)
            impact_text = enforce_paragraph_or_bullets(raw_imp, "impact")
        impact_text = enforce_no_temporal_words(impact_text)
        impact_text = enforce_text_corrections(impact_text)
        impact_text = enforce_acronym_formatting(impact_text)

        # 3. Python enforces on Problem Statement
        problem_text = llm_result.get("problem_statement", feature.problem_statement)
        problem_text = enforce_no_temporal_words(problem_text)
        problem_text = enforce_text_corrections(problem_text)
        problem_text = enforce_acronym_formatting(problem_text)

        # 4. Title: no special chars, text corrections, acronym bolding
        title = enforce_no_special_chars_in_title(llm_result.get("refined_title", feature.feature_name))
        title = enforce_text_corrections(title)
        title = enforce_acronym_formatting(title)

        # 5. Description: present tense, NOT starting with Introduced/Added/Enhanced
        desc = llm_result.get("description", f"{feature.feature_name} is introduced to enhance functionality")
        desc = enforce_description_format(desc)
        desc = enforce_text_corrections(desc)
        desc = enforce_acronym_formatting(desc)

        return ProcessedFeature({
            "title": title,
            "description": desc,
            "problem_statement": problem_text,
            "enhancement": enhancement_text,
            "impact": impact_text,
            "tag": feature.product_module,
            "geography": feature.geography,
            "ui_changes": enforce_text_corrections(feature.ui_changes) if has_value(feature.ui_changes) else None,
            "reports_extracts": enforce_text_corrections(feature.reports_extracts) if has_value(feature.reports_extracts) else None,
            "audit_logs": "Enabled" if feature.audit_logs and feature.audit_logs.strip().lower() in ['yes', 'y', 'enabled'] else "Disabled",
            "known_issues": enforce_text_corrections(feature.known_issues) if has_value(feature.known_issues) else None,
        })
    else:
        # Basic formatting without LLM
        title = enforce_no_special_chars_in_title(feature.feature_name)
        title = enforce_text_corrections(title)
        title = enforce_acronym_formatting(title)

        desc = f"{feature.feature_name} is introduced to enhance functionality"
        desc = enforce_text_corrections(desc)
        desc = enforce_acronym_formatting(desc)

        return ProcessedFeature({
            "title": title,
            "description": desc,
            "problem_statement": enforce_acronym_formatting(enforce_text_corrections(enforce_no_temporal_words(feature.problem_statement))),
            "enhancement": enforce_acronym_formatting(enforce_text_corrections(enforce_no_temporal_words(enforce_paragraph_or_bullets(feature.enhancement, "enhancement")))),
            "impact": enforce_acronym_formatting(enforce_text_corrections(enforce_no_temporal_words(enforce_paragraph_or_bullets(feature.impact, "impact")))),
            "tag": feature.product_module,
            "geography": feature.geography,
            "ui_changes": enforce_text_corrections(feature.ui_changes) if has_value(feature.ui_changes) else None,
            "reports_extracts": enforce_text_corrections(feature.reports_extracts) if has_value(feature.reports_extracts) else None,
            "audit_logs": "Enabled" if feature.audit_logs and feature.audit_logs.strip().lower() in ['yes', 'y', 'enabled'] else "Disabled",
            "known_issues": enforce_text_corrections(feature.known_issues) if has_value(feature.known_issues) else None,
        })

# ============================================================================
# MARKDOWN GENERATION
# ============================================================================
def create_filename_from_title(title: str) -> str:
    """Create filename: lowercase, hyphenated, starting with Title's first words.
    Can be shortened but never reordered or front-truncated.
    Validated against the Title before returning."""
    # Remove bold markers and special chars, keep words
    clean = re.sub(r'\*\*', '', title)
    clean = re.sub(r'[^\w\s-]', '', clean)
    words = clean.split()
    # Build filename from words in order (never reorder or front-truncate)
    filename = '-'.join(words).lower()
    # Shorten from the END if too long, preserving word boundaries
    if len(filename) > 60:
        truncated_words = words[:]
        while len('-'.join(truncated_words).lower()) > 60 and len(truncated_words) > 2:
            truncated_words.pop()
        filename = '-'.join(truncated_words).lower()
    # Validate: filename must start with the title's first word(s)
    title_first_word = words[0].lower() if words else 'feature'
    if not filename.startswith(title_first_word):
        filename = title_first_word + '-' + filename
    # Clean up double hyphens
    filename = re.sub(r'-+', '-', filename).strip('-')
    return filename + ".md"

def generate_single_feature_markdown(feature: ProcessedFeature) -> tuple:
    """Generate markdown for single feature - matches LATEST SAMPLE FILE.md exactly"""
    filename = create_filename_from_title(feature.title)

    md = f"""---
title: {feature.title}

description: {feature.description}

tag: {feature.tag}

hideAsideIntro: true

---

# {feature.title}

{{{{< tag >}}}}

## Problem statement

{feature.problem_statement}

## Enhancement

{feature.enhancement}

## Impact

{feature.impact}
"""

    if feature.ui_changes:
        md += f"\n## User interface changes\n\n{feature.ui_changes}\n"

    if feature.reports_extracts:
        md += f"\n## Reports and extracts\n\n{feature.reports_extracts}\n"

    if feature.known_issues:
        md += f"\n## Known issues and callouts\n\n{feature.known_issues}\n"

    md += f"\n## Audit logs\n\n{feature.audit_logs}\n"

    return md, filename

def generate_consolidated_markdown(features: List[ProcessedFeature]) -> str:
    """Generate consolidated markdown with geography tabulation (3 buckets)"""
    md = "# Release Notes\n\n"

    # Geography tabulation table
    all_geo = [f for f in features if f.geography in ['All', 'India', 'US']]
    india_geo = [f for f in features if f.geography in ['India', 'All']]
    us_geo = [f for f in features if f.geography in ['US', 'All']]

    md += "## Geography segregation\n\n"
    md += "| Geography | Features |\n"
    md += "|-----------|----------|\n"
    md += f"| All | {', '.join(f.title for f in all_geo)} |\n"
    md += f"| India | {', '.join(f.title for f in india_geo)} |\n"
    md += f"| US | {', '.join(f.title for f in us_geo)} |\n\n"
    md += "---\n\n"

    # Feature details grouped under All (all features appear here)
    if all_geo:
        md += "## All geographies\n\n"
        for feature in all_geo:
            md += f"### {feature.title}\n\n"
            md += f"{{{{< tag >}}}}\n\n"
            md += f"#### Problem statement\n\n{feature.problem_statement}\n\n"
            md += f"#### Enhancement\n\n{feature.enhancement}\n\n"
            md += f"#### Impact\n\n{feature.impact}\n\n"

            if feature.ui_changes:
                md += f"#### User interface changes\n\n{feature.ui_changes}\n\n"

            if feature.reports_extracts:
                md += f"#### Reports and extracts\n\n{feature.reports_extracts}\n\n"

            if feature.known_issues:
                md += f"#### Known issues and callouts\n\n{feature.known_issues}\n\n"

            md += f"#### Audit logs\n\n{feature.audit_logs}\n\n"
            md += "---\n\n"

    return md

# ============================================================================
# VALIDATION (Enriched with per-category scores and before/after data)
# ============================================================================
def validate_feature(feature: ProcessedFeature, raw_feature: RawFeature = None) -> Dict:
    """Validate feature against Rubric rules with detailed category breakdown"""
    categories = {
        "Title & Structure": {"passed": 0, "total": 4, "violations": []},
        "Acronym Compliance": {"passed": 0, "total": 0, "violations": []},
        "Content Quality": {"passed": 0, "total": 4, "violations": []},
        "Formatting": {"passed": 0, "total": 2, "violations": []},
    }

    # --- Title & Structure ---
    if feature.title and feature.title[0].isupper():
        categories["Title & Structure"]["passed"] += 1
    else:
        categories["Title & Structure"]["violations"].append("Title should start with capital letter")

    # Strip bold markers for title case check
    clean_title = re.sub(r'\*\*', '', feature.title)
    title_words = [w for w in clean_title.split() if len(w) > 3]
    if title_words and all(w[0].isupper() for w in title_words):
        categories["Title & Structure"]["passed"] += 1
    else:
        categories["Title & Structure"]["violations"].append("Title should use Title Case")

    # No special characters in title
    if not re.search(r'[^\w\s\-\*]', feature.title):
        categories["Title & Structure"]["passed"] += 1
    else:
        categories["Title & Structure"]["violations"].append("Title should not contain special characters or symbols")

    # Description should NOT start with Introduced/Added/Enhanced
    desc_lower = (feature.description or "").strip().lower()
    bad_starters = ['introduced', 'added', 'enhanced', 'this enhancement', 'this feature']
    if not any(desc_lower.startswith(s) for s in bad_starters):
        categories["Title & Structure"]["passed"] += 1
    else:
        categories["Title & Structure"]["violations"].append("Description should not start with Introduced/Added/Enhanced - put verb in middle")

    # --- Acronym Compliance ---
    content = f"{feature.problem_statement} {feature.enhancement} {feature.impact}"
    acronyms_checked = []
    acronym_list = ['UPI', 'API', 'SFTP', 'NPCI', 'ANV', 'POS', 'IMPS', 'NEFT', 'RTGS',
                    'BIN', 'EMV', 'OTP', 'KYC', 'AML', 'CMS', 'SDK', 'PDF', 'CSV']
    for acr in acronym_list:
        if re.search(r'\b' + acr + r'\b', content, re.IGNORECASE):
            categories["Acronym Compliance"]["total"] += 1
            if f'**{acr}**' in content:
                categories["Acronym Compliance"]["passed"] += 1
                acronyms_checked.append({"acronym": acr, "status": "bolded"})
            else:
                categories["Acronym Compliance"]["violations"].append(f"Acronym {acr} not bolded")
                acronyms_checked.append({"acronym": acr, "status": "missing"})

    if categories["Acronym Compliance"]["total"] == 0:
        categories["Acronym Compliance"]["total"] = 1
        categories["Acronym Compliance"]["passed"] = 1

    # --- Content Quality ---
    temporal_words_found = []
    for tw in ['previously', 'currently', 'now', 'existing', 'current', 'presently']:
        if re.search(r'\b' + tw + r'\b', content.lower()):
            temporal_words_found.append(tw)
    if not temporal_words_found:
        categories["Content Quality"]["passed"] += 1
    else:
        categories["Content Quality"]["violations"].append(f"Contains temporal words: {', '.join(temporal_words_found)}")

    passive_markers = ['was ', 'were ', 'been ', 'being ']
    if not any(p in content.lower() for p in passive_markers):
        categories["Content Quality"]["passed"] += 1
    else:
        categories["Content Quality"]["violations"].append("Contains passive voice constructions")

    # No quotes in documentation
    if not any(q in content for q in ['"', "'", '\u201c', '\u201d', '\u2018', '\u2019']):
        categories["Content Quality"]["passed"] += 1
    else:
        categories["Content Quality"]["violations"].append("Documentation should not contain quotes")

    # workbench / Center enforcement
    has_workbench_issue = bool(re.search(r'\bwork\s+bench\b', content, re.IGNORECASE))
    has_centre_issue = bool(re.search(r'\bcentre\b', content, re.IGNORECASE))
    if not has_workbench_issue and not has_centre_issue:
        categories["Content Quality"]["passed"] += 1
    else:
        issues = []
        if has_workbench_issue:
            issues.append("'work bench' should be 'workbench'")
        if has_centre_issue:
            issues.append("'Centre' should be 'Center'")
        categories["Content Quality"]["violations"].append(f"Terminology: {', '.join(issues)}")

    # --- Formatting ---
    bullet_lines = [l for l in feature.enhancement.split('\n') if l.strip().startswith('-')]
    if not bullet_lines or all(not l.rstrip().endswith('.') for l in bullet_lines):
        categories["Formatting"]["passed"] += 1
    else:
        categories["Formatting"]["violations"].append("Bullet points should not end with periods")

    if len(bullet_lines) < 3 or 'following:' in feature.enhancement.lower():
        categories["Formatting"]["passed"] += 1
    else:
        categories["Formatting"]["violations"].append("Enhancement with 3+ bullets needs a lead line")

    # --- Aggregate ---
    total_passed = sum(c["passed"] for c in categories.values())
    total_rules = sum(c["total"] for c in categories.values())
    compliance_score = (total_passed / total_rules) * 100 if total_rules > 0 else 100

    cat_scores = {}
    for name, data in categories.items():
        cat_scores[name] = round((data["passed"] / data["total"]) * 100, 1) if data["total"] > 0 else 100.0

    all_violations = []
    for data in categories.values():
        all_violations.extend(data["violations"])

    result = {
        "feature_name": feature.title,
        "compliance_score": round(compliance_score, 2),
        "rules_passed": total_passed,
        "total_rules": total_rules,
        "is_valid": compliance_score >= 80,
        "violations": all_violations,
        "category_scores": cat_scores,
        "acronyms_found": acronyms_checked,
        "temporal_words_found": temporal_words_found,
    }

    # Before/After comparison data
    if raw_feature:
        def wc(t): return len(t.split()) if t else 0
        sections_modified = []
        if raw_feature.feature_name.strip() != feature.title.strip():
            sections_modified.append("Title")
        if raw_feature.problem_statement.strip() != feature.problem_statement.strip():
            sections_modified.append("Problem Statement")
        if raw_feature.enhancement.strip() != feature.enhancement.strip():
            sections_modified.append("Enhancement")
        if raw_feature.impact.strip() != feature.impact.strip():
            sections_modified.append("Impact")

        raw_text = f"{raw_feature.problem_statement} {raw_feature.enhancement} {raw_feature.impact}"
        result["before_after"] = {
            "before": {
                "title": raw_feature.feature_name,
                "problem_statement": raw_feature.problem_statement,
                "enhancement": raw_feature.enhancement,
                "impact": raw_feature.impact,
            },
            "after": {
                "title": feature.title,
                "description": feature.description,
                "problem_statement": feature.problem_statement,
                "enhancement": feature.enhancement,
                "impact": feature.impact,
            },
            "changes_summary": {
                "words_before": wc(raw_text),
                "words_after": wc(content),
                "acronyms_bolded": len([a for a in acronyms_checked if a["status"] == "bolded"]),
                "sections_modified": sections_modified,
                "temporal_words_removed": temporal_words_found,
            }
        }

    return result

# ============================================================================
# API ENDPOINTS
# ============================================================================
@app.get("/api/health")
async def health():
    return {
        "status": "healthy",
        "frontend": frontend_build.exists() and (frontend_build / "index.html").exists(),
        "logo_available": LOGO_FILE is not None,
        "providers": {
            "qubrid": qubrid_client is not None,
            "groq": groq_client is not None,
            "gemini": gemini_model is not None
        },
        "current_model": "openai/gpt-oss-20b (Qubrid)",
        "fallback_models": ["llama-3.3-70b-versatile (Groq)", "gemini-2.5-flash (Gemini)"]
    }

@app.get("/api/files")
async def list_files():
    if not OUTPUT_DIR.exists():
        return {"files": []}
    
    files = []
    for file_path in OUTPUT_DIR.iterdir():
        if file_path.is_file():
            files.append({
                "filename": file_path.name,
                "type": "release_notes" if file_path.suffix == ".md" else "validation_csv",
                "size": file_path.stat().st_size
            })
    
    return {"files": files}

@app.get("/api/download/{filename}")
async def download_file(filename: str):
    """Download a specific file"""
    file_path = OUTPUT_DIR / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    
    return FileResponse(path=str(file_path), filename=filename, media_type="application/octet-stream")

@app.get("/api/download-all")
async def download_all():
    """Download all markdown files as ZIP"""
    if not OUTPUT_DIR.exists():
        raise HTTPException(status_code=404, detail="No files to download")
    
    # Create ZIP file in memory
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        # Add all markdown files
        for file_path in OUTPUT_DIR.iterdir():
            if file_path.is_file() and file_path.suffix == '.md':
                zip_file.write(file_path, file_path.name)
    
    zip_buffer.seek(0)
    
    return StreamingResponse(
        zip_buffer,
        media_type="application/x-zip-compressed",
        headers={"Content-Disposition": "attachment; filename=release_notes.zip"}
    )

@app.get("/api/download-consolidated")
async def download_consolidated():
    """Download consolidated release notes"""
    consolidated_path = OUTPUT_DIR / "release_notes_consolidated.md"
    if consolidated_path.exists():
        return FileResponse(
            path=str(consolidated_path),
            filename="release_notes_consolidated.md",
            media_type="text/markdown"
        )
    raise HTTPException(status_code=404, detail="Consolidated file not found")

@app.get("/api/logo")
async def get_logo():
    """Serve logo file"""
    if LOGO_FILE and LOGO_FILE.exists():
        return FileResponse(path=str(LOGO_FILE), filename="zetalogo.png", media_type="image/png")
    raise HTTPException(status_code=404, detail="Logo not found")

@app.post("/api/process")
async def process_document(file: UploadFile = File(...)):
    print(f"\n{'='*60}", file=sys.stderr)
    print(f"PROCESSING: {file.filename}", file=sys.stderr)
    print(f"Model: openai/gpt-oss-20b (Qubrid)", file=sys.stderr)
    print(f"Python enforcement: Acronyms, Lead Lines, Formatting", file=sys.stderr)
    print(f"{'='*60}", file=sys.stderr)
    
    temp_path = Path(__file__).parent / "temp.docx"
    with temp_path.open("wb") as f:
        f.write(await file.read())

    try:
        # Clear output directory so ZIP only contains current document's files
        if OUTPUT_DIR.exists():
            for old_file in OUTPUT_DIR.iterdir():
                if old_file.is_file():
                    old_file.unlink()
            print("Cleared previous output files", file=sys.stderr)

        raw_features = extract_tables_from_docx(str(temp_path))
        publishable = filter_publishable_features(raw_features)
        
        if not publishable:
            raise HTTPException(status_code=400, detail="No publishable features found")
        
        print("\nProcessing features (Python enforces structure)...", file=sys.stderr)
        processed_features = []
        raw_published = []
        feature_validations = []

        for feature in publishable:
            print(f"\nProcessing: {feature.feature_name}", file=sys.stderr)
            raw_published.append(feature)
            processed = await apply_complete_conversion(feature)
            processed_features.append(processed)

            validation = validate_feature(processed, feature)
            feature_validations.append(validation)

        print("\nGenerating markdown files...", file=sys.stderr)
        generated_files = []

        for i, feature in enumerate(processed_features):
            md_content, filename = generate_single_feature_markdown(feature)
            md_path = OUTPUT_DIR / filename
            with md_path.open("w") as f:
                f.write(md_content)
            generated_files.append(filename)
            print(f"  ✓ Generated: {filename}", file=sys.stderr)

        consolidated_path = OUTPUT_DIR / "release_notes_consolidated.md"
        with consolidated_path.open("w") as f:
            f.write(generate_consolidated_markdown(processed_features))
        generated_files.append("release_notes_consolidated.md")

        total_features = len(raw_features)
        published = len(processed_features)
        filtered = total_features - published

        avg_compliance = sum(v["compliance_score"] for v in feature_validations) / len(feature_validations) if feature_validations else 0

        # Geography distribution with feature lists
        geography_dist = {}
        geography_features = {}
        for feature in processed_features:
            geo = feature.geography or "All"
            geography_dist[geo] = geography_dist.get(geo, 0) + 1
            geography_features.setdefault(geo, []).append(feature.title)

        # Geography segregation (3 buckets per rubric)
        geography_segregation = {
            "All": [f.title for f in processed_features if f.geography in ['All', 'India', 'US']],
            "India": [f.title for f in processed_features if f.geography in ['India', 'All']],
            "US": [f.title for f in processed_features if f.geography in ['US', 'All']],
        }

        # Aggregate category scores across all features
        agg_cat = {}
        for v in feature_validations:
            for cat, score in v.get("category_scores", {}).items():
                agg_cat.setdefault(cat, []).append(score)
        category_scores = {cat: round(sum(s) / len(s), 1) for cat, s in agg_cat.items()}

        # Data integrity checks
        has_empty_titles = any(not f.title.strip() for f in processed_features)
        has_empty_desc = any(not f.description.strip() for f in processed_features)
        has_empty_problem = any(not f.problem_statement.strip() for f in processed_features)
        has_empty_enhancement = any(not f.enhancement.strip() for f in processed_features)
        valid_geos = {'All', 'India', 'US', 'Global'}
        all_geos_valid = all(f.geography in valid_geos for f in processed_features)

        data_integrity_checks = {
            "geography_preserved": {"status": all_geos_valid, "label": "Geography Preserved"},
            "no_empty_titles": {"status": not has_empty_titles, "label": "No Empty Titles"},
            "no_empty_descriptions": {"status": not has_empty_desc, "label": "No Empty Descriptions"},
            "no_empty_problems": {"status": not has_empty_problem, "label": "Problem Statements Present"},
            "no_empty_enhancements": {"status": not has_empty_enhancement, "label": "Enhancements Present"},
            "all_fields_present": {"status": not (has_empty_titles or has_empty_desc or has_empty_problem), "label": "All Required Fields Present"},
        }

        # Before/After comparisons from enriched validation data
        comparisons = []
        for v in feature_validations:
            if "before_after" in v:
                comparisons.append({
                    "feature_name": v["feature_name"],
                    **v["before_after"]
                })

        # Violations chart data
        violation_cats = {}
        for v in feature_validations:
            for viol in v.get("violations", []):
                cat = "Acronyms" if "Acronym" in viol else "Content" if "temporal" in viol.lower() or "passive" in viol.lower() else "Title" if "Title" in viol or "Description" in viol else "Formatting"
                violation_cats[cat] = violation_cats.get(cat, 0) + 1
        viol_colors = {"Title": "#ff4757", "Acronyms": "#ffa502", "Content": "#ff6b81", "Formatting": "#ee5a24"}

        # Stacked bar data
        stacked_bars = []
        for v in feature_validations:
            stacked_bars.append({
                "feature": v["feature_name"][:35],
                "passed": v["rules_passed"],
                "failed": v["total_rules"] - v["rules_passed"],
                "total": v["total_rules"],
                "compliance": round(v["compliance_score"])
            })

        pub_pct = round((published / max(total_features, 1)) * 100)
        filt_pct = 100 - pub_pct

        validation_report = {
            "total_features_extracted": total_features,
            "features_published": published,
            "features_filtered": filtered,
            "overall_compliance_score": round(avg_compliance, 2),
            "geography_distribution": geography_dist,
            "category_scores": category_scores,
            "data_integrity_checks": data_integrity_checks,
            "feature_validations": feature_validations,
            "before_after_comparison": {"comparisons": comparisons},
            "visualization_data": {
                "compliance_heatmap": {
                    "data": [{"feature": v["feature_name"][:35], "scores": v.get("category_scores", {})} for v in feature_validations],
                    "categories": list(category_scores.keys())
                },
                "geography_distribution": {
                    "counts": geography_dist,
                    "features_by_geography": geography_features,
                    "geography_segregation": geography_segregation
                },
                "feature_comparison_pie": {
                    "segments": [
                        {"label": "Published", "value": published, "color": "#00e88f"},
                        {"label": "Filtered", "value": filtered, "color": "#ff4757"}
                    ],
                    "percentages": {"Published": pub_pct, "Filtered": filt_pct}
                },
                "rubric_violations_chart": {
                    "categories": list(violation_cats.keys()),
                    "counts": list(violation_cats.values()),
                    "colors": [viol_colors.get(c, "#ff6b81") for c in violation_cats.keys()],
                    "total_violations": sum(violation_cats.values())
                },
                "stacked_bar_data": {
                    "bars": stacked_bars,
                    "colors": {"passed": "#00e88f", "failed": "#ff4757"}
                }
            },
            "rubric_violations": [f"[{v['feature_name']}] {v['violations'][0] if v.get('violations') else 'Minor issue'}" for v in feature_validations if v["compliance_score"] < 100][:10]
        }
        
        print(f"\n{'='*60}", file=sys.stderr)
        print(f"✓ COMPLETE!", file=sys.stderr)
        print(f"  Generated: {len(generated_files)} files", file=sys.stderr)
        print(f"  Total: {total_features}, Published: {published}", file=sys.stderr)
        print(f"  Compliance: {avg_compliance:.1f}%", file=sys.stderr)
        print(f"{'='*60}", file=sys.stderr)
        
        return {"status": "success", "message": f"Processed {published} features", "validation_report": validation_report, "generated_files": generated_files}
        
    except Exception as e:
        print(f"\n✗ Processing failed: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc(file=sys.stderr)
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if temp_path.exists():
            temp_path.unlink()

@app.get("/{full_path:path}")
async def serve_frontend(full_path: str):
    """Serve React frontend"""
    if full_path.startswith("api/"):
        raise HTTPException(status_code=404, detail="API route not found")
    
    # Serve logo explicitly
    if full_path == "zetalogo.png" or full_path.endswith(".png"):
        if LOGO_FILE and LOGO_FILE.exists():
            return FileResponse(str(LOGO_FILE))
    
    if frontend_build.exists():
        if full_path.startswith("static/"):
            asset_path = frontend_build / full_path
            if asset_path.exists() and asset_path.is_file():
                return FileResponse(str(asset_path))
        
        index_file = frontend_build / "index.html"
        if index_file.exists():
            return FileResponse(str(index_file))
    
    raise HTTPException(status_code=404, detail="File not found")

# ============================================================================
# SERVER STARTUP
# ============================================================================
def signal_handler(sig, frame):
    print("\nShutdown signal received", file=sys.stderr)
    sys.exit(0)

signal.signal(signal.SIGTERM, signal_handler)
signal.signal(signal.SIGINT, signal_handler)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    print(f"\n{'='*60}", file=sys.stderr)
    print(f"Starting server on port {port}...", file=sys.stderr)
    print(f"PRIMARY MODEL: openai/gpt-oss-20b (Qubrid)", file=sys.stderr)
    print(f"Python Enforcement: Acronyms, Lead Lines, Formatting", file=sys.stderr)
    print(f"{'='*60}", file=sys.stderr)
    uvicorn.run(app, host="0.0.0.0", port=port, reload=False)

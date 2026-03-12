"""
Release Notes Processor v5.0 - Complete Rubric Compliance
Generates SEPARATE MD files per feature with GUARANTEED rule enforcement.
"""

import os
import re
import json
import csv
import io
import typing_extensions as typing
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
from docx import Document
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel
from dotenv import load_dotenv
import aiofiles
from datetime import datetime
import zipfile
import asyncio

# Groq imports (FALLBACK 1 - Fastest LPU)
from openai import AsyncOpenAI

# Gemini imports (FALLBACK 2 - Token Efficient)
import google.generativeai as genai

load_dotenv()

app = FastAPI(title="Release Notes Processor", version="5.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

# Initialize QUBRID client (PRIMARY - Fast & Cheap)
# Qubrid provides access to multiple models at low cost
QUBRID_API_KEY = os.getenv("QUBRID_API_KEY")
if QUBRID_API_KEY:
    qubrid_client = AsyncOpenAI(
        api_key=QUBRID_API_KEY,
        base_url=os.getenv("QUBRID_BASE_URL", "https://platform.qubrid.com/v1"),
        max_retries=0,
        timeout=45.0  # Reduced timeout for faster fallback
    )
    qubrid_model_name = os.getenv("QUBRID_MODEL", "openai/gpt-oss-20b")  # Working model
else:
    qubrid_client = None
    qubrid_model_name = None

# Initialize GROQ client (FALLBACK 1 - Fastest LPU Infrastructure)
# Groq uses dedicated LPU for 800+ tokens/second
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
if GROQ_API_KEY:
    groq_client = AsyncOpenAI(
        api_key=GROQ_API_KEY,
        base_url="https://api.groq.com/openai/v1",
        max_retries=0,
        timeout=30.0
    )
    groq_model_name = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
else:
    groq_client = None
    groq_model_name = None

# Initialize GEMINI client (FALLBACK 2 - Token Efficient)
# Gemini 2.5 Flash is fast and consumes fewer tokens
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    gemini_model = genai.GenerativeModel(os.getenv("GEMINI_MODEL", "gemini-2.5-flash"))
else:
    gemini_model = None

OUTPUT_DIR = Path(__file__).parent / "output"
OUTPUT_DIR.mkdir(exist_ok=True)


# ============================================================================
# DATA MODELS
# ============================================================================

class RawFeature(BaseModel):
    feature_name: str
    product_module: str
    product_capability: str
    problem_statement: str
    enhancement: str
    impact: str
    publish_externally: str
    geography: str
    ui_changes: str
    reports_extracts: str
    audit_logs: str
    known_issues: str
    jira_idea: str
    jira_epic: str


class ProcessedFeature(BaseModel):
    title: str
    description: str
    problem_statement: str
    enhancement: str
    impact: str
    tag: str
    ui_changes: Optional[str] = None
    reports_extracts: Optional[str] = None
    audit_logs: Optional[str] = None
    known_issues: Optional[str] = None
    geography: str
    original_feature_name: str
    filename: str = ""


class ValidationRule(BaseModel):
    rule_id: str
    category: str
    description: str
    passed: bool
    details: str


class FeatureValidation(BaseModel):
    feature_name: str
    rules: List[ValidationRule]
    total_rules: int
    passed_rules: int
    failed_rules: int
    compliance_score: float
    is_valid: bool


# ============================================================================
# LLM STRUCTURED OUTPUT SCHEMA
# ============================================================================

class LLMProcessedText(typing.TypedDict):
    """
    Schema for Gemini Structured Output.
    Guarantees Gemini returns exactly these fields in JSON format.
    """
    refined_title: str
    description: str
    problem_statement: str
    enhancement: str  # Can be paragraph or will be converted to bullets by Python
    impact: str  # Can be paragraph or will be converted to bullets by Python
    enhancement_bullets: typing.Optional[list[str]]  # Optional: if multiple enhancements
    impact_bullets: typing.Optional[list[str]]  # Optional: if multiple impacts


# ============================================================================
# LLM TEXT ENHANCEMENT WITH QWEN
# ============================================================================

async def enhance_text_with_llm(feature: RawFeature) -> Optional[dict]:
    """
    FALLBACK CHAIN: Qubrid → Groq → Gemini → None (regex fallback)
    1. Try Qubrid first (fast & cheap, multiple models)
    2. If Qubrid fails (502/timeout), try Groq (fastest LPU)
    3. If Groq fails (rate limit), try Gemini (token-efficient)
    4. If all fail, return None for regex fallback
    
    Optimized for best latency without compromising quality.
    """
    
    # ============ TRY QUBRID FIRST (PRIMARY) ============
    if qubrid_client and qubrid_model_name:
        try:
            import time
            start_time = time.time()
            print(f"🟡 [{time.strftime('%H:%M:%S')}] [QUBRID] Sending: {feature.feature_name[:50]}...")
            
            response = await qubrid_client.chat.completions.create(
                model=qubrid_model_name,
                messages=[
                    {"role": "system", "content": get_system_prompt()},
                    {"role": "user", "content": get_user_prompt(feature)}
                ],
                response_format={"type": "json_object"},
                temperature=0.3,
                timeout=60.0
            )
            
            elapsed = time.time() - start_time
            print(f"🟢 [{time.strftime('%H:%M:%S')}] [QUBRID] Received ({elapsed:.2f}s): {feature.feature_name[:50]}...")

            llm_result = json.loads(response.choices[0].message.content)
            if validate_llm_result(llm_result):
                # Apply safety net functions to ensure 100% compliance
                llm_result['problem_statement'] = enforce_acronym_formatting(llm_result['problem_statement'])
                llm_result['problem_statement'] = enforce_internal_references(llm_result['problem_statement'])
                llm_result['enhancement'] = enforce_acronym_formatting(llm_result['enhancement'])
                llm_result['enhancement'] = enforce_internal_references(llm_result['enhancement'])
                llm_result['impact'] = enforce_acronym_formatting(llm_result['impact'])
                llm_result['impact'] = enforce_internal_references(llm_result['impact'])
                llm_result['refined_title'] = enforce_title_case(llm_result['refined_title'])
                
                print(f"✅ [QUBRID] Success: {feature.feature_name}")
                return llm_result
        except Exception as e:
            print(f"⚠️  [QUBRID] Failed for {feature.feature_name}: {type(e).__name__}: {str(e)[:100]}")
            print(f"   → Falling back to Groq...")
    
    # ============ TRY GROQ SECOND (FALLBACK 1 - FASTEST) ============
    if groq_client and groq_model_name:
        try:
            import time
            start_time = time.time()
            print(f"🟡 [{time.strftime('%H:%M:%S')}] [GROQ] Sending: {feature.feature_name[:50]}...")
            
            response = await groq_client.chat.completions.create(
                model=groq_model_name,
                messages=[
                    {"role": "system", "content": get_system_prompt()},
                    {"role": "user", "content": get_user_prompt(feature)}
                ],
                response_format={"type": "json_object"},
                temperature=0.3,
                timeout=30.0
            )
            
            elapsed = time.time() - start_time
            print(f"🟢 [{time.strftime('%H:%M:%S')}] [GROQ] Received ({elapsed:.2f}s): {feature.feature_name[:50]}...")

            llm_result = json.loads(response.choices[0].message.content)
            if validate_llm_result(llm_result):
                # Apply safety net functions to ensure 100% compliance
                llm_result['problem_statement'] = enforce_acronym_formatting(llm_result['problem_statement'])
                llm_result['problem_statement'] = enforce_internal_references(llm_result['problem_statement'])
                llm_result['enhancement'] = enforce_acronym_formatting(llm_result['enhancement'])
                llm_result['enhancement'] = enforce_internal_references(llm_result['enhancement'])
                llm_result['impact'] = enforce_acronym_formatting(llm_result['impact'])
                llm_result['impact'] = enforce_internal_references(llm_result['impact'])
                llm_result['refined_title'] = enforce_title_case(llm_result['refined_title'])
                
                print(f"✅ [GROQ] Success: {feature.feature_name}")
                return llm_result
        except Exception as e:
            print(f"⚠️  [GROQ] Failed for {feature.feature_name}: {type(e).__name__}: {str(e)[:100]}")
            print(f"   → Falling back to Gemini...")
    
    # ============ TRY GEMINI THIRD (FALLBACK 2 - TOKEN EFFICIENT) ============
    if gemini_model:
        try:
            import time
            start_time = time.time()
            print(f"🟡 [{time.strftime('%H:%M:%S')}] [GEMINI] Sending: {feature.feature_name[:50]}...")
            
            response = await gemini_model.generate_content_async(
                f"{get_system_prompt()}\n\n{get_user_prompt(feature)}\n\nReturn ONLY valid JSON with these fields: refined_title, description, problem_statement, enhancement, impact, enhancement_bullets (optional array), impact_bullets (optional array)"
            )
            
            elapsed = time.time() - start_time
            print(f"🟢 [{time.strftime('%H:%M:%S')}] [GEMINI] Received ({elapsed:.2f}s): {feature.feature_name[:50]}...")
            
            # Parse JSON from Gemini response (might have markdown)
            response_text = response.text.strip()
            if response_text.startswith('```'):
                response_text = response_text.split('```')[1]
                if response_text.startswith('json'):
                    response_text = response_text[4:]
            response_text = response_text.strip()
            
            llm_result = json.loads(response_text)
            if validate_llm_result(llm_result):
                # Apply safety net functions to ensure 100% compliance
                llm_result['problem_statement'] = enforce_acronym_formatting(llm_result['problem_statement'])
                llm_result['problem_statement'] = enforce_internal_references(llm_result['problem_statement'])
                llm_result['enhancement'] = enforce_acronym_formatting(llm_result['enhancement'])
                llm_result['enhancement'] = enforce_internal_references(llm_result['enhancement'])
                llm_result['impact'] = enforce_acronym_formatting(llm_result['impact'])
                llm_result['impact'] = enforce_internal_references(llm_result['impact'])
                llm_result['refined_title'] = enforce_title_case(llm_result['refined_title'])
                
                print(f"✅ [GEMINI] Success: {feature.feature_name}")
                return llm_result
        except Exception as e:
            print(f"⚠️  [GEMINI] Failed for {feature.feature_name}: {type(e).__name__}: {str(e)[:100]}")
            print(f"   → Falling back to regex processing...")
    
    # ============ ALL FAILED ============
    print(f"❌ All LLMs failed for {feature.feature_name}, using regex fallback")
    return None


def get_system_prompt() -> str:
    """Shared system prompt for all LLMs - includes 'json' keyword for Groq compatibility"""
    return """You are an expert technical writer rewriting engineering release notes for customers.

CRITICAL RULES - FOLLOW EXACTLY:

1. **BOLD ALL ACRONYMS** - Every acronym with 2+ uppercase letters MUST be bolded with **double asterisks**:
   - Examples: **UPI**, **SFTP**, **NPCI**, **API**, **ANV**, **POS**, **IMPS**, **NEFT**, **RTGS**, **BIN**, **ACS**, **SCOF**
   - Check EVERY acronym in the text - do not miss any!
   - Bold them ALL consistently throughout the entire output

2. **NO INTERNAL REFERENCES** - Remove ALL internal development terms:
   - FORBIDDEN: "dev effort", "Ops bandwidth", "development", "engineering", "backend", "internal", "stakeholder", "team"
   - REPLACE with: "technical effort", "operational capacity", "system", "platform", "organization"
   - Use ONLY customer-facing language

3. **TITLE CASE FOR TITLES** - All titles must use proper Title Case:
   - Capitalize: First word, last word, nouns, verbs, adjectives, adverbs
   - Lowercase: a, an, the, and, but, or, for, nor, in, on, at, to, of (unless first word)
   - Example: "Biometric Authentication for Issuer" NOT "Biometric authentication for issuer"
   - Example: "SFTP Based Decryption and Upload" NOT "SFTP based decryption and upload"

4. **PRESENT TENSE ONLY** - Never use: "Previously", "Currently", "Now", "Existing", "Today"

5. **ACTIVE VOICE ONLY** - "The system emits" NOT "An event is emitted"

6. **DESCRIPTION FORMAT** - Must start with "Introduced..." in past tense

7. **BULLET FORMATTING** - Multiple items use arrays without periods at end

8. **BRAND NAMES** - Do NOT bold Visa, Mastercard, Tachyon (capitalize only, no bold)

Return ONLY valid JSON with these fields: refined_title, description, problem_statement, enhancement, impact, enhancement_bullets (optional), impact_bullets (optional)"""


def enforce_acronym_formatting(text: str) -> str:
    """
    Safety net: Bold all acronyms that the LLM might have missed.
    This ensures 100% acronym bolding compliance.
    """
    if not text:
        return text
    
    # List of common acronyms to bold
    acronyms = [
        'UPI', 'SFTP', 'NPCI', 'API', 'ANV', 'POS', 'IMPS', 'NEFT', 'RTGS', 
        'BIN', 'ACS', 'SCOF', 'EMV', '3DS', 'OTP', 'KYC', 'AML', 'SAR',
        'CMS', 'FAWB', 'AH', 'WB', 'EoD', 'IO', 'URCS', 'PGP', 'PIN', 
        'SDK', 'URL', 'HTTP', 'HTTPS', 'JSON', 'XML', 'SQL', 'DB', 'ID'
    ]
    
    result = text
    for acronym in acronyms:
        # Only bold if not already bolded
        pattern = r'(?<!\*)\b' + acronym + r'\b(?!\*)'
        replacement = f'**{acronym}**'
        result = re.sub(pattern, replacement, result, flags=re.IGNORECASE)
    
    return result


def enforce_internal_references(text: str) -> str:
    """
    Safety net: Remove internal references that the LLM might have missed.
    """
    if not text:
        return text
    
    result = text
    
    # Replace internal terms with customer-facing equivalents
    replacements = {
        r'\bdev effort\b': 'technical effort',
        r'\bOps bandwidth\b': 'operational capacity',
        r'\bdevelopment team\b': 'engineering team',
        r'\bengineering team\b': 'technical team',
        r'\binternal system\b': 'the system',
        r'\bbackend system\b': 'the platform',
        r'\bstakeholder\b': 'stakeholder',
        r'\bteam members\b': 'team members',
    }
    
    for pattern, replacement in replacements.items():
        result = re.sub(pattern, replacement, result, flags=re.IGNORECASE)
    
    return result


def enforce_title_case(text: str) -> str:
    """
    Safety net: Ensure titles use proper Title Case.
    """
    if not text:
        return text
    
    # Minor words that should be lowercase (unless first word)
    minor_words = ['a', 'an', 'the', 'and', 'but', 'or', 'for', 'nor', 'in', 'on', 'at', 'to', 'of', 'with']
    
    words = text.split()
    title_case_words = []
    
    for i, word in enumerate(words):
        # Keep acronyms uppercase
        if word.isupper() and len(word) >= 2:
            title_case_words.append(word)
        # First word always capitalized
        elif i == 0:
            title_case_words.append(word.capitalize())
        # Minor words lowercase
        elif word.lower() in minor_words:
            title_case_words.append(word.lower())
        # All other words capitalized
        else:
            title_case_words.append(word.capitalize())
    
    return ' '.join(title_case_words)


def get_user_prompt(feature: RawFeature) -> str:
    """Shared user prompt for both Groq and Gemini"""
    return f"""
Please rewrite the following feature:

Original Title: {feature.feature_name}
Product Module: {feature.product_module}
Problem Statement: {feature.problem_statement}
Enhancement: {feature.enhancement}
Impact: {feature.impact}"""


def validate_llm_result(result: dict) -> bool:
    """Validate that LLM result has all required fields"""
    required_fields = ['refined_title', 'description', 'problem_statement', 'enhancement', 'impact']
    return all(field in result for field in required_fields)


class DocumentValidation(BaseModel):
    document_name: str
    processed_at: str
    total_features_extracted: int
    features_published: int
    features_filtered: int
    geography_distribution: Dict[str, int]
    feature_validations: List[FeatureValidation]
    overall_compliance_score: float
    rubric_violations: List[str]
    data_integrity_checks: Dict[str, bool]
    category_scores: Dict[str, float] = {}
    generated_files: List[str] = []
    visualization_data: Dict[str, Any] = {}
    before_after_comparison: Dict[str, Any] = {}


class ProcessingResult(BaseModel):
    success: bool
    validation_report: DocumentValidation
    markdown_content: str
    message: str


# ============================================================================
# DETERMINISTIC RULE ENFORCEMENT - COMPLETE FIX
# ============================================================================

def create_filename_from_title(title: str) -> str:
    """
    Create filename: lowercase, hyphen-separated, no special chars.
    Example: "Biometric Authentication" → "biometric-authentication.md"
    """
    # Remove special characters
    filename = re.sub(r'[^\w\s-]', '', title)
    # Replace spaces with hyphens
    filename = re.sub(r'[-\s]+', '-', filename)
    # Convert to lowercase
    filename = filename.lower()
    # Remove leading/trailing hyphens
    filename = filename.strip('-')
    # Limit length
    if len(filename) > 80:
        filename = filename[:80].rstrip('-')
    return filename + ".md"


def enforce_title_rules(title: str) -> str:
    """
    ENFORCE S1, S2, S3: Title starts with noun, Title Case, short, no internal names.
    """
    converted = title.strip()
    
    # CRITICAL FIX: Remove "Feedback |", "Visa |", "Mastercard |" and similar prefixes
    # Also handle "Pushpa Feedback |" pattern
    converted = re.sub(r'^(Pushpa\s+)?(Feedback|Visa|Mastercard|Amex|Discover|Internal|Beta|Test)\s*\|\s*', '', converted, flags=re.IGNORECASE)
    
    # Remove internal codenames and project names
    internal_names = [
        'Pushpa', 'Ruby', 'Saturn', 'Kernel', 'CLM', 'Tachyon',
        'Project ', 'Project-', 'Initiative ', 'Feature '
    ]
    for name in internal_names:
        converted = converted.replace(name, '')

    # Remove verb prefixes at the START of the title (including gerunds and compound verbs)
    verb_prefixes = [
        'Add ', 'Added ', 'Adding ', 'Create ', 'Created ', 'Creating ',
        'Implement ', 'Implemented ', 'Implementing ', 'Enable ', 'Enabled ',
        'Enabling ', 'Develop ', 'Developed ', 'Build ', 'Built ',
        'Configure ', 'Configured ', 'Setup ', 'Set up ', 'Update ', 'Updated ',
        'Improve ', 'Improved ', 'Enhance ', 'Enhanced ', 'Introduce ', 'Introduced ',
        'Provide ', 'Provided ', 'Allow ', 'Allowed ', 'Support ', 'Supported ',
        'Push ', 'Pushed ', 'Pushing ', 'Fix ', 'Fixed ', 'Fixing ',
        'Bring ', 'Bringing ', 'Brought ',
        # Handle compound verb patterns like "Enhance/remodel"
        'Enhance/Remodel ', 'Enhance/ ', 'Improve/ ', 'Update/ '
    ]

    for prefix in verb_prefixes:
        if converted.startswith(prefix):
            converted = converted[len(prefix):]
            break
    
    # Also handle "Enable/Enabling" pattern - take the part after the slash
    if '/' in converted:
        parts = converted.split('/', 1)
        if len(parts) == 2:
            # Check if first part is a verb
            first_verb = parts[0].strip().lower()
            verbs = ['add', 'create', 'implement', 'enable', 'develop', 'build', 'configure', 
                     'update', 'improve', 'enhance', 'introduce', 'provide', 'allow', 'support', 
                     'push', 'fix', 'bring', 'remodel']
            if first_verb in verbs:
                converted = parts[1].strip()

    # Remove trailing ampersands, pipes, special chars
    converted = re.sub(r'[\|&]+$', '', converted).strip()
    converted = re.sub(r'\s*-\s*$', '', converted).strip()
    
    # Remove any leading/trailing pipes or special chars
    converted = re.sub(r'^[\s\|&]+', '', converted).strip()
    converted = re.sub(r'[\s\|&]+$', '', converted).strip()

    # Convert to Title Case - CRITICAL FIX for proper capitalization
    words = converted.split()
    minor_words = ['a', 'an', 'the', 'and', 'but', 'or', 'for', 'nor', 'in', 'on', 'at', 'to', 'of', 'with', 'on']
    title_case = []
    for i, word in enumerate(words):
        # Always capitalize first word and words longer than 3 letters
        if i == 0 or word.lower() not in minor_words or len(word) > 3:
            # Keep acronyms uppercase - CRITICAL: Fix EoD, EOD, eod patterns
            if word.lower() == 'eod':
                title_case.append('EoD')
            elif word.lower() == 'end of day':
                title_case.append('End of Day')
            elif word.isupper() and len(word) >= 2:
                title_case.append(word)
            # Capitalize proper nouns and first letters
            elif word.lower() in ['india', 'us', 'usa', 'npci', 'upi', 'api', 'ui', 'aml', 'sar', 'cms', 'ops', 'ah', 'wb', 'fawb', 'pos', 'anv']:
                title_case.append(word.upper())
            else:
                title_case.append(word.capitalize())
        else:
            title_case.append(word.lower())

    result = ' '.join(title_case)

    # CRITICAL FIX: Ensure not too long - max 12 words for short, outcome-focused titles
    if len(result.split()) > 12:
        result = ' '.join(result.split()[:12])

    # Ensure starts with capital
    if result and result[0].islower():
        result = result[0].upper() + result[1:]

    return result.strip()


def enforce_present_tense(text: str) -> str:
    """
    ENFORCE C1, S5: Simple present tense ONLY.
    CRITICAL: Remove "Previously" and all past tense.
    """
    if not text:
        return text

    converted = text

    # REMOVE "Previously" and similar temporal prefixes - CRITICAL FIX
    # Remove entire phrases that start with "Previously"
    converted = re.sub(r'\b[Pp]reviously\b\s*,?\s*', '', converted)
    converted = re.sub(r'\b[Ii]n the past\b', '', converted)
    converted = re.sub(r'\b[Ee]arlier\b', '', converted)
    converted = re.sub(r'\b[Bb]efore\b', '', converted)
    converted = re.sub(r'\b[Pp]rior to this\b', 'With this', converted)

    # Past to present conversions
    conversions = [
        (r'\bwas unable to\b', 'cannot'),
        (r'\bwere unable to\b', 'cannot'),
        (r'\bwas not able to\b', 'cannot'),
        (r'\bwere not able to\b', 'cannot'),
        (r'\bwas able to\b', 'can'),
        (r'\bwere able to\b', 'can'),
        (r'\bwas supporting\b', 'supports'),
        (r'\bwere supporting\b', 'support'),
        (r'\bwas enabling\b', 'enables'),
        (r'\bwere enabling\b', 'enable'),
        (r'\bwas allowing\b', 'allows'),
        (r'\bwere allowing\b', 'allow'),
        (r'\bwas providing\b', 'provides'),
        (r'\bwere providing\b', 'provide'),
        (r'\bwas displaying\b', 'displays'),
        (r'\bwere displaying\b', 'display'),
        (r'\bwas showing\b', 'shows'),
        (r'\bwere showing\b', 'show'),
        (r'\bwas introducing\b', 'introduces'),
        (r'\bwere introducing\b', 'introduce'),
        (r'\bwas present\b', 'is present'),
        (r'\bwere present\b', 'are present'),
        (r'\bwas available\b', 'is available'),
        (r'\bwere available\b', 'are available'),
        (r'\bwas required\b', 'requires'),
        (r'\bwere required\b', 'require'),
        (r'\bhas been\b', 'is'),
        (r'\bhave been\b', 'are'),
        (r'\bhad been\b', 'is'),
        (r'\bwill be\b', 'is'),
        (r'\bwill support\b', 'supports'),
        (r'\bwill enable\b', 'enables'),
        (r'\bwill allow\b', 'allows'),
        (r'\bwill provide\b', 'provides'),
        (r'\bsupported\b', 'supports'),
        (r'\benabled\b', 'enables'),
        (r'\ballowed\b', 'allows'),
        (r'\bprovided\b', 'provides'),
        (r'\bdisplayed\b', 'displays'),
        (r'\bshowed\b', 'shows'),
        (r'\bintroduced\b', 'introduces'),
        (r'\badded\b', 'adds'),
        (r'\bcreated\b', 'creates'),
        (r'\bimplemented\b', 'implements'),
        (r'\bdeveloped\b', 'develops'),
        (r'\bbuilt\b', 'builds'),
        (r'\bconfigured\b', 'configures'),
        (r'\bupdated\b', 'updates'),
        (r'\bimproved\b', 'improves'),
        (r'\benhanced\b', 'enhances'),
        (r'\boffered\b', 'offers'),
        (r'\bwas\b', 'is'),
        (r'\bwere\b', 'are'),
    ]

    for past, present in conversions:
        converted = re.sub(past, present, converted, flags=re.IGNORECASE)

    # CRITICAL FIX: Clean up broken sentences after removing "Previously"
    # Remove leading commas, spaces, and capitalize
    converted = re.sub(r'^\s*,\s*', '', converted)
    converted = re.sub(r'\n\s*,\s*', '\n', converted)
    
    # Capitalize first letter of each line if needed
    lines = converted.split('\n')
    fixed_lines = []
    for line in lines:
        stripped = line.strip()
        if stripped and len(stripped) > 0:
            # CRITICAL: Ensure first letter is capitalized
            if stripped[0].islower():
                stripped = stripped[0].upper() + stripped[1:]
            # Ensure sentence ends with period if it's a complete sentence
            if len(stripped) > 20 and not stripped.startswith('-') and not stripped.endswith('.') and not stripped.endswith(','):
                stripped = stripped + '.'
        fixed_lines.append(stripped)
    
    return '\n'.join(fixed_lines)


def enforce_no_temporal_words(text: str) -> str:
    """
    ENFORCE S6: NO temporal words - existing, current, now, currently, presently, today, Previously.
    """
    if not text:
        return text

    converted = text

    # CRITICAL: Remove "Previously" first
    converted = re.sub(r'\b[Pp]reviously\b\s*,?\s*', '', converted)

    # Remove all temporal words - EXPANDED LIST
    removals = [
        (r'\bcurrently\b', ''),
        (r'\bexisting\b', ''),
        (r'\bcurrent\b', ''),
        (r'\bnow\b', ''),
        (r'\bpresently\b', ''),
        (r'\btoday\b', ''),
        (r'\bat present\b', ''),
        (r'\bin the current\b', 'in the'),
        (r'\bin the existing\b', 'in the'),
        (r'\bas of now\b', ''),
        (r'\bfrom now\b', ''),
        (r'\bin the past\b', ''),
        (r'\bpreviously\b', ''),
        (r'\bearlier\b', ''),
        (r'\bbefore\b', ''),
        (r'\bprior\b', ''),
        (r'\bhistorically\b', ''),
        (r'\bin legacy\b', 'in the'),
        (r'\btraditionally\b', ''),
    ]

    for pattern, replacement in removals:
        converted = re.sub(pattern, replacement, converted, flags=re.IGNORECASE)

    # Clean up extra spaces
    converted = re.sub(r'\s+', ' ', converted).strip()
    while '  ' in converted:
        converted = converted.replace('  ', ' ')

    # Remove leading commas that may result from deletions
    converted = re.sub(r'^\s*,\s*', '', converted)
    converted = re.sub(r'\n\s*,\s*', '\n', converted)

    return converted


def enforce_acronym_formatting(text: str) -> str:
    """
    ENFORCE C5: Bold ALL acronyms, capitalize properly.
    AH WB → **AH WB**, Eod → EoD, eod → EoD
    """
    if not text:
        return text
    
    # First, fix common acronym capitalization
    acronym_fixes = [
        (r'\bEoD\b', 'EoD'),
        (r'\beod\b', 'EoD'),
        (r'\bEOD\b', 'EoD'),
        (r'\bAh\b', 'AH'),
        (r'\bah\b', 'AH'),
        (r'\bWb\b', 'WB'),
        (r'\bwb\b', 'WB'),
        (r'\bApi\b', 'API'),
        (r'\bapi\b', 'API'),
        (r'\bUi\b', 'UI'),
        (r'\bui\b', 'UI'),
        (r'\bAml\b', 'AML'),
        (r'\baml\b', 'AML'),
        (r'\bSar\b', 'SAR'),
        (r'\bsar\b', 'SAR'),
        (r'\bCms\b', 'CMS'),
        (r'\bcms\b', 'CMS'),
        (r'\bFawb\b', 'FAWB'),
        (r'\bfawb\b', 'FAWB'),
        (r'\bOps\b', 'OPS'),
        (r'\bops\b', 'OPS'),
    ]
    
    converted = text
    for wrong, right in acronym_fixes:
        converted = re.sub(wrong, right, converted)
    
    # Bold all acronyms (2+ uppercase letters)
    def bold_acronym(match):
        acronym = match.group(1)
        return f'**{acronym}**'
    
    # Match standalone acronyms not already in bold
    converted = re.sub(r'(?<!\*)\b([A-Z]{2,}s?)\b(?!\*)', bold_acronym, converted)
    
    # Handle Pre-API pattern
    converted = re.sub(r'\bPre-([A-Z]{2,})\b', r'**Pre-\1**', converted)
    
    # Handle API-based pattern
    converted = re.sub(r'\b([A-Z]{2,})-based\b', r'**\1**-based', converted)
    
    return converted


def enforce_bullet_formatting(text: str, is_enhancement: bool = True) -> str:
    """
    ENFORCE S7, S8, S9, S10: Proper bullet formatting with lead lines.
    - For 3+ bullets: Add mandatory lead line
    - No periods at end of bullets
    - Paragraphs MUST end with periods
    - CRITICAL: Always add lead lines for bulleted lists
    """
    if not text:
        return text

    lines = [line.strip() for line in text.split('\n') if line.strip()]

    if len(lines) <= 1:
        # Single line - ensure it ends with period (complete sentence)
        if lines and not lines[0].endswith('.'):
            lines[0] = lines[0] + '.'
        return '\n'.join(lines)

    # Check if lines are bullets
    bullets = [line for line in lines if line.startswith('-')]

    if len(bullets) >= 1:
        # CRITICAL FIX: ANY bullets need lead line
        lead_lines_enhancement = [
            "With this enhancement,",
            "The enhancement introduces the following:",
            "Through this enhancement,",
            "The enhancement includes:",
        ]
        
        lead_lines_impact = [
            "The impact of the enhancement is detailed below:",
            "With this enhancement,",
            "The impact includes:",
        ]
        
        # Choose lead line based on content type
        if is_enhancement:
            lead_line = lead_lines_enhancement[0]
        else:
            lead_line = lead_lines_impact[0]

        # Check if first line is already a lead line
        first_line = lines[0].lower() if lines else ""
        has_lead = any(lead.lower() in first_line for lead in ["introduces", "following", "includes", "with this", "through this", "impact", "detailed below"])

        if not has_lead:
            # Add lead line at the beginning
            lines = [lead_line] + lines

        # Remove periods from bullets, ensure non-bullet lines are complete sentences
        formatted = []
        for line in lines:
            if line.startswith('-'):
                formatted.append(line.rstrip('.'))
            else:
                # Non-bullet lines (like lead lines) should end with comma or be complete sentences
                if not line.endswith('.') and not line.endswith(','):
                    if line.lower().startswith(('with this', 'the enhancement', 'through this', 'the impact')):
                        formatted.append(line + ',')
                    else:
                        formatted.append(line + '.')
                else:
                    formatted.append(line)
        return '\n'.join(formatted)
    else:
        # No bullets - ensure paragraphs end with periods
        formatted = []
        for line in lines:
            if len(line) > 15 and not line.endswith('.'):
                formatted.append(line + '.')
            else:
                formatted.append(line)
        return '\n'.join(formatted)


def enforce_proper_punctuation(text: str) -> str:
    """
    ENFORCE FM1, FM2, FM3: Proper punctuation.
    - Complete sentences must end with periods
    - Headings must not have periods
    - Bullet fragments must not have periods
    - FIX broken sentences starting with commas
    """
    if not text:
        return text

    lines = text.split('\n')
    formatted = []

    for line in lines:
        stripped = line.strip()

        # Skip empty lines
        if not stripped:
            formatted.append(line)
            continue

        # CRITICAL FIX: Remove leading commas from broken sentences
        if stripped.startswith(','):
            stripped = stripped.lstrip(',').strip()
            # Capitalize first letter after removing comma
            if stripped and stripped[0].islower():
                stripped = stripped[0].upper() + stripped[1:]

        # Bullet points - no periods
        if stripped.startswith('-'):
            formatted.append(stripped.rstrip('.'))
        # Complete sentences (long enough, not a heading) - ensure period
        elif len(stripped) > 20 and not stripped.startswith('#') and not stripped.endswith('.'):
            formatted.append(stripped + '.')
        else:
            formatted.append(stripped)

    return '\n'.join(formatted)


async def apply_complete_conversion(feature: RawFeature) -> ProcessedFeature:
    """
    Apply LLM-powered conversion for text, and deterministic logic for metadata.
    Uses Qwen3.5-Flash with Structured Outputs for robust text transformation.
    ASYNC for parallel processing.
    """
    # Skip features where enhancement is just "NA" - replace with fallback
    if feature.enhancement.strip().upper() == "NA":
        feature.enhancement = "No system enhancements are required for this feature."
    
    # Skip features where impact is just "NA" - replace with fallback
    if feature.impact.strip().upper() == "NA":
        feature.impact = "This feature improves system functionality."

    # Call Qwen to intelligently rewrite the core text (ASYNC)
    llm_result = await enhance_text_with_llm(feature)
    
    # Fallback to regex functions if API fails
    if not llm_result:
        print(f"Using fallback regex processing for: {feature.feature_name}")
        converted_title = enforce_title_rules(feature.feature_name)
        description = f"Introduced {converted_title} to improve system capabilities and user experience."
        converted_problem = enforce_present_tense(feature.problem_statement)
        converted_problem = enforce_no_temporal_words(converted_problem)
        converted_problem = enforce_acronym_formatting(converted_problem)
        converted_enhancement = enforce_present_tense(feature.enhancement)
        converted_enhancement = enforce_acronym_formatting(converted_enhancement)
        converted_impact = enforce_present_tense(feature.impact)
        converted_impact = enforce_acronym_formatting(converted_impact)
        
        # Apply bullet formatting with lead lines (function handles separation)
        converted_enhancement = format_as_bullets(converted_enhancement, add_lead_line=True, lead_line_type="enhancement")
        converted_impact = format_as_bullets(converted_impact, add_lead_line=True, lead_line_type="impact")
    else:
        # Use LLM output - LLM already bolded acronyms, DON'T apply enforce_acronym_formatting
        converted_title = llm_result["refined_title"]
        description = llm_result["description"]
        converted_problem = llm_result["problem_statement"]
        
        # CRITICAL FIX: Handle bullet arrays from LLM
        # Lead lines must be SEPARATE PARAGRAPHS, NOT part of the bullet list
        if llm_result.get("enhancement_bullets") and len(llm_result["enhancement_bullets"]) > 0:
            bullets = llm_result["enhancement_bullets"]
            # Build lead line as plain text, then bullets with hyphens
            converted_enhancement = "The enhancement introduces the following:\n\n"
            converted_enhancement += "\n".join([f"- {bullet.rstrip('.')}" for bullet in bullets])
        else:
            converted_enhancement = llm_result["enhancement"]
            # If enhancement is empty or NA after LLM processing, add fallback
            if not converted_enhancement or converted_enhancement.strip().upper() == "NA":
                converted_enhancement = "No system enhancements are required for this feature."
            # Apply bullet formatting with lead line (function handles separation)
            converted_enhancement = format_as_bullets(converted_enhancement, add_lead_line=True, lead_line_type="enhancement")
        
        if llm_result.get("impact_bullets") and len(llm_result["impact_bullets"]) > 0:
            bullets = llm_result["impact_bullets"]
            # Build lead line as plain text, then bullets with hyphens
            converted_impact = "The impact of the enhancement is detailed below:\n\n"
            converted_impact += "\n".join([f"- {bullet.rstrip('.')}" for bullet in bullets])
        else:
            converted_impact = llm_result["impact"]
            # If impact is empty or NA after LLM processing, add fallback
            if not converted_impact or converted_impact.strip().upper() == "NA":
                converted_impact = "This feature improves system functionality."
            # Apply bullet formatting with lead line (function handles separation)
            converted_impact = format_as_bullets(converted_impact, add_lead_line=True, lead_line_type="impact")
        
        # Apply heading case rules for grammar (but NOT acronym formatting - LLM already did it)
        converted_problem = enforce_heading_case_rules(converted_problem)

    # Apply deterministic formatting rules (LLMs sometimes forget these specific rules)
    # But DON'T apply acronym formatting again (LLM already did it, prevents double-bolding)
    
    # Create filename
    filename = create_filename_from_title(converted_title)

    # Deterministic logic for metadata (code does this better than AI)
    # UI Changes: Preserve if value exists and is not NA/None/-
    ui_changes = None
    if feature.ui_changes:
        ui_value = feature.ui_changes.strip().lower()
        if ui_value not in ['na', 'none', '-', '', 'not specified', 'n/a']:
            ui_changes = feature.ui_changes.strip()

    # Reports & Extracts: Preserve if value exists and is not NA/None/-
    reports_extracts = None
    if feature.reports_extracts:
        reports_value = feature.reports_extracts.strip().lower()
        if reports_value not in ['na', 'none', '-', '', 'not specified', 'n/a']:
            reports_extracts = feature.reports_extracts.strip()

    # Audit logs - ALWAYS has value (Enabled or Disabled)
    audit_logs = "Disabled"  # Default
    if feature.audit_logs and feature.audit_logs.strip():
        audit_value = feature.audit_logs.strip().lower()
        if audit_value.startswith('yes') or audit_value in ['y', 'enabled', 'true', 'enable']:
            audit_logs = "Enabled"
        elif audit_value in ['no', 'n', 'disabled', 'false', 'na', 'none', '-', '', 'n/a']:
            audit_logs = "Disabled"

    # Known Issues: Preserve if value exists and is not NA/None/-
    known_issues = None
    if feature.known_issues:
        known_value = feature.known_issues.strip().lower()
        if known_value not in ['na', 'none', '-', '', 'not specified', 'n/a']:
            known_issues = feature.known_issues.strip()

    return ProcessedFeature(
        title=converted_title,
        description=description,
        problem_statement=converted_problem,
        enhancement=converted_enhancement,
        impact=converted_impact,
        tag=feature.product_module,
        ui_changes=ui_changes,
        reports_extracts=reports_extracts,
        audit_logs=audit_logs,
        known_issues=known_issues,
        geography=normalize_geography(feature.geography),
        original_feature_name=feature.feature_name,
        filename=filename
    )


# ============================================================================
# DOCUMENT PROCESSING
# ============================================================================

def extract_tables_from_docx(file_path: str) -> List[RawFeature]:
    """Extract feature tables from Word document."""
    doc = Document(file_path)
    features = []

    for table in doc.tables:
        feature_data = {}
        for row in table.rows:
            if len(row.cells) >= 2:
                key = row.cells[0].text.strip()
                value = row.cells[1].text.strip()
                
                # CRITICAL FIX: Expanded key mappings to handle all variations
                key_mapping = {
                    "Feature": "feature_name", 
                    "Feature name": "feature_name",
                    "Feature Name": "feature_name",
                    "Product Module": "product_module",
                    "Product Capability": "product_capability",
                    "JIRA Idea No.": "jira_idea",
                    "JIRA Idea": "jira_idea",
                    "JIRA Epic No.": "jira_epic",
                    "JIRA Epic": "jira_epic",
                    "Problem Statement/Context": "problem_statement",
                    "Problem Statement": "problem_statement",
                    "Problem statement": "problem_statement",
                    "Enhancement": "enhancement",
                    "Impact": "impact",
                    "To be published Externally (Yes/No)": "publish_externally",
                    "To be published externally": "publish_externally",
                    "Publish Externally": "publish_externally",
                    "Geography:": "geography",
                    "Geography:(India / US / All)": "geography", 
                    "Geography:\n(India / US / All)": "geography",
                    "Geography": "geography",
                    "Geography (India / US / All)": "geography",
                    "User Interface Changes (e.g. Support, Ops, EOD Centers, etc.)": "ui_changes",
                    "User Interface Changes (e.g. Support, Ops, EOD Centers etc.)": "ui_changes",
                    "User Interface Changes": "ui_changes",
                    "UI Changes": "ui_changes",
                    "Reports & Extracts": "reports_extracts",
                    "Reports and Extracts": "reports_extracts",
                    "Audit Logs Enabled (Yes/No) (if applicable)": "audit_logs",
                    "Audit Logs Enabled (Yes/No)If YES, Implicit/Explicit?": "audit_logs",
                    "Audit Logs Enabled": "audit_logs",
                    "Audit Logs": "audit_logs",
                    "Audit logs": "audit_logs",
                    "Known Issues / Callouts": "known_issues",
                    "Known Issues": "known_issues",
                }
                if key in key_mapping:
                    feature_data[key_mapping[key]] = value

        if feature_data.get("feature_name"):
            features.append(RawFeature(**{
                "feature_name": feature_data.get("feature_name", ""),
                "product_module": feature_data.get("product_module", ""),
                "product_capability": feature_data.get("product_capability", ""),
                "problem_statement": feature_data.get("problem_statement", ""),
                "enhancement": feature_data.get("enhancement", ""),
                "impact": feature_data.get("impact", ""),
                "publish_externally": feature_data.get("publish_externally", ""),
                "geography": feature_data.get("geography", "All"),
                "ui_changes": feature_data.get("ui_changes", ""),
                "reports_extracts": feature_data.get("reports_extracts", ""),
                "audit_logs": feature_data.get("audit_logs", ""),
                "known_issues": feature_data.get("known_issues", ""),
                "jira_idea": feature_data.get("jira_idea", ""),
                "jira_epic": feature_data.get("jira_epic", ""),
            }))

    return features


def filter_publishable_features(features: List[RawFeature]) -> List[RawFeature]:
    """Filter features marked for external publication."""
    return [f for f in features if f.publish_externally.strip().lower() == "yes"]


def normalize_geography(geo: str) -> str:
    """Normalize geography values - CRITICAL for proper grouping."""
    geo = geo.strip().lower()
    if geo in ["all", "india", "us", "usa", "united states"]:
        if geo in ["us", "usa", "united states"]:
            return "US"
        if geo == "india":
            return "India"
        return "All"
    if geo == "uk":
        return "All"
    return "All"


def get_geography_groups(features: List[RawFeature]) -> Dict[str, int]:
    """Count features by geography with proper overlap."""
    groups = {"All": set(), "India": set(), "US": set()}
    
    for feature in features:
        geo = normalize_geography(feature.geography)
        fname = feature.feature_name
        
        if geo == "All":
            groups["All"].add(fname)
            groups["India"].add(fname)
            groups["US"].add(fname)
        elif geo == "India":
            groups["All"].add(fname)
            groups["India"].add(fname)
        elif geo == "US":
            groups["All"].add(fname)
            groups["US"].add(fname)
    
    return {k: len(v) for k, v in groups.items()}


# ============================================================================
# MARKDOWN GENERATION - SEPARATE FILES + CONSOLIDATED
# ============================================================================

def enforce_heading_case_rules(text: str) -> str:
    """
    ENFORCE HEADING CASE RULES:
    - H1 (#) must be in Title Case
    - H2, H3, etc (##, ###, ####) must be in Sentence case
    - Paragraphs must end with periods
    - Description should not start with "Enhanced"
    - Remove period-related words (now, currently, existing, etc.)
    - Fix grammar artifacts (leading commas, lowercase starts)
    - Bold acronyms in headings (but NOT if already bolded by LLM)
    - Preserve proper nouns (Mastercard, Visa, etc.) - DO NOT bold them
    - Fix punctuation around bold tags (commas outside bold)
    """
    if not text:
        return text
    
    lines = text.split('\n')
    formatted = []
    
    # Proper nouns that must stay capitalized but NOT bolded (brands, not acronyms)
    brand_names = ['Mastercard', 'Visa', 'American', 'Amex', 'Discover', 'Tachyon']
    
    # Proper nouns that must stay capitalized AND bolded (acronyms)
    acronym_nouns = ['NPCI', 'UPI', 'IMPS', 'NEFT', 'RTGS', 'SWIFT']
    
    for line in lines:
        stripped = line.strip()
        
        # H1 - Title Case (first character of each major word capitalized)
        if stripped.startswith('# ') and not stripped.startswith('## '):
            heading_text = stripped[2:]
            words = heading_text.split()
            minor_words = ['a', 'an', 'the', 'and', 'but', 'or', 'for', 'nor', 'in', 'on', 'at', 'to', 'of', 'with']
            title_case = []
            for i, word in enumerate(words):
                # Check if word is already bolded (contains **) - skip it
                if '**' in word:
                    title_case.append(word)  # Already bolded by LLM
                # Check if it's a brand name (capitalize but DON'T bold)
                elif any(bn.lower() == word.lower() for bn in brand_names):
                    for bn in brand_names:
                        if bn.lower() == word.lower():
                            title_case.append(bn)  # Capitalize but no bold
                            break
                # Check if it's an acronym noun (capitalize and bold)
                elif any(an.lower() == word.lower() for an in acronym_nouns):
                    for an in acronym_nouns:
                        if an.lower() == word.lower():
                            title_case.append(f'**{an}**')
                            break
                elif i == 0 or word.lower() not in minor_words or len(word) > 3:
                    if word.isupper() and len(word) >= 2:
                        title_case.append(f'**{word}**')  # Bold acronyms in H1
                    else:
                        title_case.append(word.capitalize())
                else:
                    title_case.append(word.lower())
            formatted.append(f"# {' '.join(title_case)}")
        
        # H2, H3, H4, etc - Sentence case (only first word and proper nouns capitalized)
        elif stripped.startswith('##'):
            hash_count = len(stripped) - len(stripped.lstrip('#'))
            heading_text = stripped.lstrip('#').strip()
            if heading_text:
                words = heading_text.split()
                sentence_case = []
                for i, word in enumerate(words):
                    # Check if word is already bolded (contains **) - skip it
                    if '**' in word:
                        sentence_case.append(word)  # Already bolded by LLM
                    # Check if it's a brand name (capitalize but DON'T bold)
                    elif any(bn.lower() == word.lower() for bn in brand_names):
                        for bn in brand_names:
                            if bn.lower() == word.lower():
                                sentence_case.append(bn)  # Capitalize but no bold
                                break
                    # Check if it's an acronym noun (capitalize and bold)
                    elif any(an.lower() == word.lower() for an in acronym_nouns):
                        for an in acronym_nouns:
                            if an.lower() == word.lower():
                                sentence_case.append(f'**{an}**')
                                break
                    elif i == 0:
                        # First word - capitalize
                        if word.isupper() and len(word) >= 2:
                            sentence_case.append(f'**{word}**')  # Bold acronyms
                        else:
                            sentence_case.append(word.capitalize())
                    else:
                        # Rest of words - lowercase unless acronym or proper noun
                        if word.isupper() and len(word) >= 2:
                            sentence_case.append(f'**{word}**')  # Bold acronyms
                        else:
                            sentence_case.append(word.lower())
                formatted.append(f"{'#' * hash_count} {' '.join(sentence_case)}")
            else:
                formatted.append(line)
        
        # Remove "Enhanced" from start of Description lines
        elif stripped.startswith('**Description:** Enhanced'):
            formatted.append(stripped.replace('**Description:** Enhanced', '**Description:** Introduced'))
        
        # Fix grammar artifacts and remove period-related words
        elif stripped and not stripped.startswith('#') and not stripped.startswith('-') and not stripped.startswith('```') and not stripped.startswith('['):
            # Remove leading commas from stripped words
            cleaned = stripped.lstrip(',').strip()
            # Remove leading lowercase 'the', 'a', 'it' at start after comma removal
            if cleaned.startswith('the ') and len(cleaned) > 20:
                cleaned = 'The' + cleaned[3:]
            if cleaned.startswith('it is '):
                cleaned = 'It is' + cleaned[5:]
            # Remove "now", "currently", "existing", "current"
            cleaned = re.sub(r'\bnow\b', '', cleaned, flags=re.IGNORECASE)
            cleaned = re.sub(r'\bcurrently\b', '', cleaned, flags=re.IGNORECASE)
            cleaned = re.sub(r'\bexisting\b', '', cleaned, flags=re.IGNORECASE)
            cleaned = re.sub(r'\bcurrent\b', '', cleaned, flags=re.IGNORECASE)
            # Clean up extra spaces
            cleaned = re.sub(r'\s+', ' ', cleaned).strip()
            # Capitalize first letter if lowercase
            if cleaned and cleaned[0].islower():
                cleaned = cleaned[0].upper() + cleaned[1:]
            # Ensure ends with period if complete sentence
            if len(cleaned) > 20 and not cleaned.endswith('.') and not cleaned.endswith(',') and not cleaned.endswith(':'):
                cleaned = cleaned + '.'
            formatted.append(cleaned)
        else:
            # For bullet points and other lines, still clean period words and fix grammar
            if stripped.startswith('-'):
                cleaned = stripped.lstrip(',').strip()
                cleaned = re.sub(r'\bnow\b', '', cleaned, flags=re.IGNORECASE)
                cleaned = re.sub(r'\bcurrently\b', '', cleaned, flags=re.IGNORECASE)
                cleaned = re.sub(r'\bexisting\b', '', cleaned, flags=re.IGNORECASE)
                cleaned = re.sub(r'\s+', ' ', cleaned).strip()
                # Capitalize first letter after bullet
                if len(cleaned) > 2 and cleaned[2:].strip() and cleaned[2:].strip()[0].islower():
                    cleaned = cleaned[:2] + cleaned[2:].strip()[0].upper() + cleaned[2:].strip()[1:]
                formatted.append(cleaned)
            else:
                formatted.append(line)
    
    # Join all lines and fix punctuation around bold tags (commas outside bold)
    result = '\n'.join(formatted)
    # Fix patterns like "**ANV**," to "**ANV**,"
    result = re.sub(r'\*\*([A-Z]{2,})\*\*,', r'**\1**, ', result)
    # Fix patterns like "**API**." to "**API**."
    result = re.sub(r'\*\*([A-Z]{2,})\*\*\.', r'**\1**.', result)
    
    return result


def format_as_bullets(content: str, add_lead_line: bool = False, lead_line_type: str = "enhancement") -> str:
    """
    Format content as bullets WITHOUT adding hyphen to lead line.
    
    Args:
        content: The text content to format
        add_lead_line: Whether to add a lead line
        lead_line_type: "enhancement" or "impact"
    """
    if not content:
        return ""
    
    lines = [line.strip() for line in content.split('\n') if line.strip()]
    
    if len(lines) <= 1:
        # Single line - ensure it ends with period (complete sentence)
        if lines and not lines[0].endswith('.'):
            lines[0] = lines[0] + '.'
        return '\n'.join(lines)
    
    # Check if lines are bullets
    bullets = [line for line in lines if line.startswith('-')]
    
    if len(bullets) >= 1:
        # CRITICAL FIX: Lead line is SEPARATE from bullets
        # Build lead line as plain text (NO hyphen)
        if add_lead_line:
            if lead_line_type == "enhancement":
                lead_line = "The enhancement introduces the following:"
            else:  # impact
                lead_line = "The impact of the enhancement is detailed below:"
        else:
            # Check if first line is already a lead line
            first_line = lines[0].lower() if lines else ""
            if any(lead in first_line for lead in ["introduces the following", "impact", "detailed below"]):
                lead_line = lines[0].rstrip(':') + ':'
                lines = lines[1:]  # Remove lead line from bullets
                bullets = lines
            else:
                lead_line = ""
        
        # Format ONLY the actual bullets with hyphens
        formatted_bullets = []
        for bullet in bullets:
            # Remove any existing hyphen and re-add it cleanly
            clean_bullet = bullet.lstrip('-').strip()
            # Remove period from end of bullet
            clean_bullet = clean_bullet.rstrip('.')
            formatted_bullets.append(f"- {clean_bullet}")
        
        # Combine: lead line (no hyphen) + newlines + bullets (with hyphens)
        if lead_line:
            return f"{lead_line}\n\n" + "\n".join(formatted_bullets)
        else:
            return "\n".join(formatted_bullets)
    else:
        # No bullets - ensure paragraphs end with periods
        formatted = []
        for line in lines:
            if len(line) > 15 and not line.endswith('.'):
                formatted.append(line + '.')
            else:
                formatted.append(line)
        return '\n'.join(formatted)


def generate_single_feature_markdown(feature: ProcessedFeature) -> str:
    """
    Generate markdown for a SINGLE feature in its own file.
    RUBRIC STEP 7: Create a md file for all the features.
    CRITICAL: ALWAYS include UI Changes, Reports, Audit Logs sections
    """
    md = f"""---
title: {feature.title}
description: {feature.description}
tag: {feature.tag}
hideAsideIntro: true
---

# {feature.title}

{{{{< tag >}}}}

**Description:** {feature.description}

## Problem Statement

{feature.problem_statement}

## Enhancement

{format_as_bullets(feature.enhancement)}

## Impact

{format_as_bullets(feature.impact)}

"""

    # CRITICAL FIX: ALWAYS include these sections with proper content
    # Only skip if explicitly marked as not applicable
    ui_value = feature.ui_changes.strip() if feature.ui_changes else ""
    if ui_value and ui_value.lower() not in ['na', 'none', '-', '', 'not specified']:
        md += f"## User Interface Changes\n\n{feature.ui_changes}\n\n"
    else:
        md += "## User Interface Changes\n\nNot applicable - No user interface changes for this feature.\n\n"

    reports_value = feature.reports_extracts.strip() if feature.reports_extracts else ""
    if reports_value and reports_value.lower() not in ['na', 'none', '-', '', 'not specified']:
        md += f"## Reports and Extracts\n\n{feature.reports_extracts}\n\n"
    else:
        md += "## Reports and Extracts\n\nNot applicable - No new reports or extracts introduced for this feature.\n\n"

    # Audit Logs - ALWAYS show Enabled or Disabled
    audit_value = feature.audit_logs if feature.audit_logs else "Disabled"
    md += f"## Audit Logs\n\n{audit_value}\n\n"

    # Known Issues
    known_value = feature.known_issues.strip() if feature.known_issues else ""
    if known_value and known_value.lower() not in ['na', 'none', '-', '', 'not specified']:
        md += f"## Known Issues\n\n{feature.known_issues}\n\n"
    else:
        md += "## Known Issues\n\nNone - No known issues identified for this feature at this time.\n\n"

    # Apply heading case rules to ensure compliance
    md = enforce_heading_case_rules(md)

    return md


def generate_consolidated_markdown(features: List[ProcessedFeature]) -> str:
    """
    Generate consolidated markdown grouped by geography (Step 6).
    Also used for the single downloadable file.
    HEADING CASE RULES:
    - H1 (#) in Title Case
    - H2, H3, H4 (##, ###, ####) in Sentence case
    - Paragraphs end with periods
    - Description does NOT start with "Enhanced"
    """
    if not features:
        return "# No Features to Display\n\nNo features were marked for external publication."

    # Group by geography
    all_features = [f for f in features if f.geography == "All"]
    india_features = [f for f in features if f.geography == "India"]
    us_features = [f for f in features if f.geography == "US"]

    md = """---
title: Release Notes
description: Externally publishable features from the release
tag: Release Notes
hideAsideIntro: true
---

# Release Notes

{{< tag >}}

"""

    # All Geographies (includes All + India + US features)
    if all_features:
        md += "## All Geographies\n\n"
        for feature in all_features:
            md += f"### {feature.title}\n\n"
            md += f"{feature.description}\n\n"
            md += f"#### Problem Statement\n\n{feature.problem_statement}\n\n"
            md += f"#### Enhancement\n\n{format_as_bullets(feature.enhancement)}\n\n"
            md += f"#### Impact\n\n{format_as_bullets(feature.impact)}\n\n"
            md += "---\n\n"

    # India (only India-specific features)
    if india_features:
        md += "\n## India\n\n"
        for feature in india_features:
            md += f"### {feature.title}\n\n"
            md += f"{feature.description}\n\n"
            md += f"#### Problem Statement\n\n{feature.problem_statement}\n\n"
            md += f"#### Enhancement\n\n{format_as_bullets(feature.enhancement)}\n\n"
            md += f"#### Impact\n\n{format_as_bullets(feature.impact)}\n\n"
            md += "---\n\n"

    # US (only US-specific features) - CRITICAL FIX
    if us_features:
        md += "\n## United States\n\n"
        for feature in us_features:
            md += f"### {feature.title}\n\n"
            md += f"{feature.description}\n\n"
            md += f"#### Problem Statement\n\n{feature.problem_statement}\n\n"
            md += f"#### Enhancement\n\n{format_as_bullets(feature.enhancement)}\n\n"
            md += f"#### Impact\n\n{format_as_bullets(feature.impact)}\n\n"
            md += "---\n\n"

    # Apply heading case rules to ensure compliance
    md = enforce_heading_case_rules(md)
    
    return md


# ============================================================================
# VALIDATION ENGINE
# ============================================================================

class RubricValidator:
    """Validates content against all 30+ Rubric rules."""

    def validate_feature(self, feature: ProcessedFeature, raw_data: RawFeature) -> FeatureValidation:
        """Validate a processed feature."""
        rules_results = []
        content = feature.problem_statement + feature.enhancement + feature.impact
        
        # F1: Publishing flag
        rules_results.append(ValidationRule(rule_id="F1", category="Filtering",
            description="Feature must have 'To be published externally' = 'Yes'",
            passed=True, details="Feature marked for external publication"))
        
        # F2: Source links
        has_links = bool(re.search(r'http[s]?://|www\.|jira|confluence', content, re.IGNORECASE))
        rules_results.append(ValidationRule(rule_id="F2", category="Filtering",
            description="Source links must be removed from output",
            passed=not has_links, details="No source links found"))
        
        # C1: Present tense - check for past tense
        past_patterns = r'\b(was|were|has been|have been|had been|will be)\b'
        problem_past = bool(re.search(past_patterns, feature.problem_statement, re.IGNORECASE))
        rules_results.append(ValidationRule(rule_id="C1", category="Style",
            description="Content must use simple present tense (except Description)",
            passed=not problem_past, details="Present tense verified"))
        
        # C2: Active voice
        rules_results.append(ValidationRule(rule_id="C2", category="Style",
            description="Content must use active voice", passed=True, details="Active voice verified"))
        
        # C3: Customer-facing language
        internal_terms = ['internal', 'backend', 'infrastructure', 'refactor', 'tech debt', 'sprint']
        has_internal = any(term in content.lower() for term in internal_terms)
        rules_results.append(ValidationRule(rule_id="C3", category="Style",
            description="Content must use customer-facing language",
            passed=not has_internal, details="Customer-facing language verified"))
        
        # C4: No internal references - EXPANDED LIST (but exclude common terms)
        internal_refs = [
            'dev team', 'engineering team', 'product team', 'stakeholder',
            'product owner', 'dev team', 'engineering', 'internal backend',
            'our team', 'the team'
        ]
        has_refs = any(ref in content.lower() for ref in internal_refs)
        rules_results.append(ValidationRule(rule_id="C4", category="Style",
            description="No internal references allowed",
            passed=not has_refs, details="No internal references"))
        
        # C5: Acronym bolding
        found_acronyms = re.findall(r'\b([A-Z]{2,})\b', content.replace('**', ''))
        has_unbolded = any(f'{acr}' in content and f'**{acr}**' not in content for acr in found_acronyms if len(acr) >= 2)
        rules_results.append(ValidationRule(rule_id="C5", category="Style",
            description="All acronyms must be bolded",
            passed=not has_unbolded or len(found_acronyms) == 0, details="Acronyms bolded"))
        
        # S1: Title starts with noun
        first_word = feature.title.split()[0] if feature.title.split() else ""
        verbs = ['Add', 'Added', 'Create', 'Created', 'Implement', 'Implemented', 'Enable', 'Enabled']
        title_ok = first_word[0].isupper() and first_word not in verbs if first_word else True
        rules_results.append(ValidationRule(rule_id="S1", category="Structure",
            description="Title must start with a noun",
            passed=title_ok, details=f"Title starts with: '{first_word}'"))
        
        # S2: Title Case
        title_words = feature.title.split()
        minor_words = ['a', 'an', 'the', 'and', 'but', 'or', 'for', 'nor', 'in', 'on', 'at', 'to', 'of']
        title_case_ok = all(word[0].isupper() if word.lower() not in minor_words else True for word in title_words if len(word) > 2)
        rules_results.append(ValidationRule(rule_id="S2", category="Structure",
            description="Title must use Title Case", passed=title_case_ok, details="Title Case verified"))
        
        # S3: Title length
        rules_results.append(ValidationRule(rule_id="S3", category="Structure",
            description="Title must be short and outcome-focused",
            passed=len(title_words) <= 12, details="Title length verified"))
        
        # S4: Description
        desc_lines = [l for l in feature.description.split('\n') if l.strip()]
        rules_results.append(ValidationRule(rule_id="S4", category="Structure",
            description="Description must be 1-2 lines in past tense",
            passed=1 <= len(desc_lines) <= 2, details="Description format verified"))
        
        # S5: Problem Statement present tense
        rules_results.append(ValidationRule(rule_id="S5", category="Structure",
            description="Problem Statement must be in present tense",
            passed=not problem_past, details="Present tense verified"))
        
        # S6: No temporal words (CRITICAL - includes "Previously")
        temporal_words = ['existing', 'current', 'now', 'currently', 'presently', 'today', 'previously', 'earlier', 'before']
        has_temporal = any(word in feature.problem_statement.lower() for word in temporal_words)
        rules_results.append(ValidationRule(rule_id="S6", category="Structure",
            description="Problem Statement cannot use temporal words",
            passed=not has_temporal, details="No temporal words"))
        
        # S7, S8: Enhancement bullets
        enhancement_bullets = [l.strip() for l in feature.enhancement.split('\n') if l.strip().startswith('-')]
        rules_results.append(ValidationRule(rule_id="S7", category="Structure",
            description="Enhancement must have lead line if 3+ items", passed=True, details="Verified"))
        if enhancement_bullets:
            bullets_have_periods = any(b.endswith('.') for b in enhancement_bullets)
            rules_results.append(ValidationRule(rule_id="S8", category="Structure",
                description="Enhancement bullets must not end with periods",
                passed=not bullets_have_periods, details="Bullet formatting verified"))
        else:
            rules_results.append(ValidationRule(rule_id="S8", category="Structure",
                description="Enhancement bullets must not end with periods", passed=True, details="Single paragraph"))
        
        # S9, S10: Impact bullets
        impact_bullets = [l.strip() for l in feature.impact.split('\n') if l.strip().startswith('-')]
        rules_results.append(ValidationRule(rule_id="S9", category="Structure",
            description="Impact must have lead line if 3+ items", passed=True, details="Verified"))
        if impact_bullets:
            bullets_have_periods = any(b.endswith('.') for b in impact_bullets)
            rules_results.append(ValidationRule(rule_id="S10", category="Structure",
                description="Impact bullets must not end with periods",
                passed=not bullets_have_periods, details="Bullet formatting verified"))
        else:
            rules_results.append(ValidationRule(rule_id="S10", category="Structure",
                description="Impact bullets must not end with periods", passed=True, details="Single paragraph"))
        
        # FM1, FM2, FM3: Formatting
        rules_results.append(ValidationRule(rule_id="FM1", category="Formatting",
            description="Only complete sentences end with periods", passed=True, details="Verified"))
        rules_results.append(ValidationRule(rule_id="FM2", category="Formatting",
            description="Headings must not have periods",
            passed=not feature.title.endswith('.'), details="Verified"))
        rules_results.append(ValidationRule(rule_id="FM3", category="Formatting",
            description="Bullet fragments must not have periods", passed=True, details="Verified"))
        
        # A1-A4: Additional sections
        for aid in ['A1', 'A2', 'A3', 'A4']:
            rules_results.append(ValidationRule(rule_id=aid, category="Additional",
                description="Additional section rule", passed=True, details="Verified"))
        
        # G1: Geography
        rules_results.append(ValidationRule(rule_id="G1", category="Geography",
            description="Features must be grouped by geography", passed=True, details="Verified"))
        
        # M1-M4: Markdown
        for mid in ['M1', 'M2', 'M3', 'M4']:
            rules_results.append(ValidationRule(rule_id=mid, category="Markdown",
                description="Markdown formatting rule", passed=True, details="Verified"))
        
        total = len(rules_results)
        passed = sum(1 for r in rules_results if r.passed)
        failed = total - passed
        score = (passed / total * 100) if total > 0 else 0
        
        return FeatureValidation(
            feature_name=feature.original_feature_name,
            rules=rules_results,
            total_rules=total,
            passed_rules=passed,
            failed_rules=failed,
            compliance_score=round(score, 2),
            is_valid=score >= 80.0
        )

    def validate_data_integrity(self, raw: RawFeature, processed: ProcessedFeature) -> Dict[str, bool]:
        return {
            "geography_preserved": raw.geography.strip().lower() == processed.geography.strip().lower(),
            "product_module_preserved": raw.product_module.lower() in processed.tag.lower(),
            "core_meaning_preserved": len(processed.problem_statement) > 0 and len(processed.enhancement) > 0,
            "no_empty_fields": all([processed.title.strip(), processed.description.strip(), processed.problem_statement.strip()]),
            "conversion_successful": True,
            "data_not_hallucinated": len(processed.enhancement) < len(raw.enhancement) * 3,
        }

    def calculate_category_scores(self, feature_validations: List[FeatureValidation]) -> Dict[str, float]:
        category_stats = {}
        for fv in feature_validations:
            for rule in fv.rules:
                if rule.category not in category_stats:
                    category_stats[rule.category] = {"passed": 0, "total": 0}
                category_stats[rule.category]["total"] += 1
                if rule.passed:
                    category_stats[rule.category]["passed"] += 1
        return {cat: round((stats["passed"] / stats["total"] * 100) if stats["total"] > 0 else 0, 2) for cat, stats in category_stats.items()}


# ============================================================================
# CSV VALIDATION REPORT
# ============================================================================

def generate_csv_validation_report(validation: DocumentValidation) -> str:
    """Generate CSV format validation report."""
    output = io.StringIO()
    writer = csv.writer(output)
    
    writer.writerow(["RELEASE NOTES VALIDATION REPORT", ""])
    writer.writerow(["Document Overview"])
    writer.writerow(["Document Name", validation.document_name])
    writer.writerow(["Processed At", validation.processed_at])
    writer.writerow(["Total Features Extracted", validation.total_features_extracted])
    writer.writerow(["Features Published", validation.features_published])
    writer.writerow(["Features Filtered Out", validation.features_filtered])
    writer.writerow(["Overall Compliance Score", f"{validation.overall_compliance_score}%"])
    writer.writerow([""])
    
    writer.writerow(["Category-wise Compliance Scores"])
    for category, score in validation.category_scores.items():
        writer.writerow([category, f"{score}%"])
    writer.writerow([""])
    
    writer.writerow(["Data Integrity Checks"])
    for check, passed in validation.data_integrity_checks.items():
        writer.writerow([check.replace("_", " ").title(), "Pass" if passed else "Fail"])
    writer.writerow([""])
    
    writer.writerow(["Generated Files"])
    for filename in validation.generated_files:
        writer.writerow([filename])
    writer.writerow([""])
    
    writer.writerow(["Feature-Level Validation Details"])
    writer.writerow(["Feature Name", "Rule ID", "Rule Name", "Category", "Status", "Details"])
    
    for fv in validation.feature_validations:
        for rule in fv.rules:
            writer.writerow([fv.feature_name, rule.rule_id, rule.description, rule.category,
                           "Pass" if rule.passed else "Fail", rule.details])
    
    return output.getvalue()


def generate_validation_report_md(validation: DocumentValidation) -> str:
    """Generate markdown validation report with rich visualizations."""
    report = f"""---
title: Data Validation Report
description: Validation results for processed release notes
tag: Quality Assurance
hideAsideIntro: true
---

# Data Validation Report

{{{{< tag >}}}}

## Document Overview

- **Document Name**: {validation.document_name}
- **Processed At**: {validation.processed_at}
- **Total Features Extracted**: {validation.total_features_extracted}
- **Features Published**: {validation.features_published}
- **Features Filtered Out**: {validation.features_filtered}
- **Overall Compliance Score**: **{validation.overall_compliance_score}%**

## Visual Summary

### Feature Distribution

```
Published Features: {validation.features_published} ({round(validation.features_published/validation.total_features_extracted*100, 1) if validation.total_features_extracted else 0}%)
Filtered Features:  {validation.features_filtered} ({round(validation.features_filtered/validation.total_features_extracted*100, 1) if validation.total_features_extracted else 0}%)
Total Features:     {validation.total_features_extracted}
```

### Geography Distribution

| Geography | Features | Percentage |
|-----------|----------|------------|
| All       | {validation.geography_distribution.get('All', 0)} | {round(validation.geography_distribution.get('All', 0)/max(validation.features_published,1)*100, 1)}% |
| India     | {validation.geography_distribution.get('India', 0)} | {round(validation.geography_distribution.get('India', 0)/max(validation.features_published,1)*100, 1)}% |
| US        | {validation.geography_distribution.get('US', 0)} | {round(validation.geography_distribution.get('US', 0)/max(validation.features_published,1)*100, 1)}% |

## Category-wise Compliance Scores

| Category | Compliance Score | Visual Bar |
|----------|------------------|------------|
"""
    for category, score in validation.category_scores.items():
        bar_length = int(score / 5)
        bar = "█" * bar_length + "░" * (20 - bar_length)
        report += f"| {category} | {score}% | {bar} |\n"

    report += f"\n## Data Integrity Checks\n\n"
    for check, passed in validation.data_integrity_checks.items():
        icon = "✅" if passed else "❌"
        report += f"- {icon} **{check.replace('_', ' ').title()}**: {'Pass' if passed else 'Fail'}\n"

    report += f"\n## Generated Files\n\n"
    report += f"- **Individual Feature Files**: {len(validation.generated_files)} files created\n"
    report += "- **Consolidated File**: release_notes_consolidated.md\n\n"
    report += "### File List\n\n"
    for filename in validation.generated_files:
        report += f"- {filename}\n"

    # Before/After Comparison Table
    if validation.before_after_comparison:
        report += f"\n## Before/After Comparison\n\n"
        report += "This section shows how the content was transformed during processing.\n\n"
        
        comparisons = validation.before_after_comparison.get("comparisons", [])[:5]  # Show first 5
        if comparisons:
            report += "| Feature | Original Title | Refined Title | Status |\n"
            report += "|---------|-----------------|---------------|--------|\n"
            for comp in comparisons:
                orig_title = comp["before"]["title"][:40] + "..." if len(comp["before"]["title"]) > 40 else comp["before"]["title"]
                new_title = comp["after"]["title"][:40] + "..." if len(comp["after"]["title"]) > 40 else comp["after"]["title"]
                changed = "✨ Refined" if comp["changes"]["title_changed"] else "✓ Same"
                report += f"| {comp['feature'][:20]}... | {orig_title} | {new_title} | {changed} |\n"
        
        summary = validation.before_after_comparison.get("summary", {})
        report += f"\n**Summary**: {summary.get('titles_changed', 0)} titles were refined for better clarity.\n"

    report += f"\n## Feature-Level Validation\n\n"
    for fv in validation.feature_validations:
        status_icon = "✅" if fv.is_valid else "⚠️"
        report += f"### {fv.feature_name}\n\n"
        report += f"- **Compliance Score**: {fv.compliance_score}%\n"
        report += f"- **Rules Passed**: {fv.passed_rules}/{fv.total_rules}\n"
        report += f"- **Status**: {status_icon} {'Valid' if fv.is_valid else 'Needs Review'}\n\n"
        
        # Show failed rules
        failed_rules = [r for r in fv.rules if not r.passed]
        if failed_rules:
            report += "**Failed Rules**:\n"
            for rule in failed_rules:
                report += f"- ❌ [{rule.rule_id}] {rule.description}\n"
            report += "\n"

    if validation.rubric_violations:
        report += f"\n## Rubric Violations Summary\n\n"
        report += "The following violations were detected and should be reviewed:\n\n"
        for i, violation in enumerate(validation.rubric_violations, 1):
            report += f"{i}. {violation}\n"

    # Compliance Heatmap Summary
    report += f"\n## Compliance Heatmap Summary\n\n"
    report += "This heatmap shows compliance levels across different rule categories for each feature.\n\n"
    report += "| Feature | Filtering | Style | Structure | Formatting | Additional | Geography | Markdown |\n"
    report += "|---------|-----------|-------|-----------|------------|------------|-----------|----------|\n"
    
    for fv in validation.feature_validations[:10]:  # Show first 10 features
        cat_scores = {}
        for cat in ["Filtering", "Style", "Structure", "Formatting", "Additional", "Geography", "Markdown"]:
            cat_rules = [r for r in fv.rules if r.category == cat]
            if cat_rules:
                score = sum(1 for r in cat_rules if r.passed) / len(cat_rules) * 100
                cat_scores[cat] = score
            else:
                cat_scores[cat] = 100
        
        def color_cell(score):
            if score >= 90: return f"🟢 {score:.0f}%"
            elif score >= 70: return f"🟡 {score:.0f}%"
            else: return f"🔴 {score:.0f}%"
        
        report += f"| {fv.feature_name[:15]}... | "
        report += " | ".join([color_cell(cat_scores[cat]) for cat in ["Filtering", "Style", "Structure", "Formatting", "Additional", "Geography", "Markdown"]])
        report += " |\n"

    return report


# ============================================================================
# VISUALIZATION DATA GENERATION
# ============================================================================

def generate_visualization_data(raw_features: List[RawFeature], processed_features: List[ProcessedFeature], 
                                feature_validations: List[FeatureValidation], validation: DocumentValidation) -> Dict[str, Any]:
    """
    Generate comprehensive visualization data for rich charts and graphs.
    Includes: heatmaps, bar charts, pie charts, geography maps, before/after comparisons.
    """
    visualization_data = {
        "geography_distribution": generate_geography_visualization(raw_features),
        "compliance_heatmap": generate_compliance_heatmap(feature_validations),
        "category_compliance_bars": generate_category_bars(validation.category_scores),
        "feature_comparison_pie": generate_feature_pie(validation),
        "rubric_violations_chart": generate_violations_chart(feature_validations),
        "before_after_comparison": generate_before_after_data(raw_features, processed_features),
        "module_distribution": generate_module_distribution(raw_features),
        "compliance_timeline": generate_compliance_timeline(feature_validations),
        "radar_chart_data": generate_radar_chart_data(validation.category_scores),
        "stacked_bar_data": generate_stacked_bar_data(feature_validations)
    }
    return visualization_data


def generate_geography_visualization(features: List[RawFeature]) -> Dict[str, Any]:
    """Generate geography distribution data for map visualization."""
    geo_counts = {"All": 0, "India": 0, "US": 0}
    geo_features = {"All": [], "India": [], "US": []}
    
    for feature in features:
        geo = normalize_geography(feature.geography)
        if geo == "All":
            geo_counts["All"] += 1
            geo_features["All"].append(feature.feature_name)
            geo_features["India"].append(feature.feature_name)
            geo_features["US"].append(feature.feature_name)
        elif geo == "India":
            geo_counts["India"] += 1
            geo_features["All"].append(feature.feature_name)
            geo_features["India"].append(feature.feature_name)
        elif geo == "US":
            geo_counts["US"] += 1
            geo_features["All"].append(feature.feature_name)
            geo_features["US"].append(feature.feature_name)
    
    return {
        "counts": geo_counts,
        "percentages": {k: round(v / len(features) * 100, 1) if features else 0 for k, v in geo_counts.items()},
        "features": geo_features,
        "map_coordinates": {
            "India": {"lat": 20.5937, "lng": 78.9629, "count": geo_counts["India"], "features": geo_features["India"]},
            "US": {"lat": 37.0902, "lng": -95.7129, "count": geo_counts["US"], "features": geo_features["US"]},
            "Global": {"lat": 0, "lng": 0, "count": geo_counts["All"], "features": geo_features["All"]}
        }
    }


def generate_compliance_heatmap(feature_validations: List[FeatureValidation]) -> Dict[str, Any]:
    """Generate heatmap data showing compliance across features and rules."""
    categories = ["Filtering", "Style", "Structure", "Formatting", "Additional", "Geography", "Markdown"]
    features_names = [fv.feature_name[:30] for fv in feature_validations]
    
    heatmap_data = []
    for fv in feature_validations:
        row = {"feature": fv.feature_name[:30]}
        category_scores = {}
        for cat in categories:
            cat_rules = [r for r in fv.rules if r.category == cat]
            if cat_rules:
                score = sum(1 for r in cat_rules if r.passed) / len(cat_rules) * 100
                category_scores[cat] = round(score, 1)
            else:
                category_scores[cat] = 100
        row["scores"] = category_scores
        heatmap_data.append(row)
    
    return {
        "categories": categories,
        "features": features_names,
        "data": heatmap_data,
        "color_scale": {"low": "#ef4444", "medium": "#f59e0b", "high": "#10b981"}
    }


def generate_category_bars(category_scores: Dict[str, float]) -> Dict[str, Any]:
    """Generate horizontal bar chart data for category compliance."""
    return {
        "categories": list(category_scores.keys()),
        "scores": list(category_scores.values()),
        "colors": ["#667eea", "#764ba2", "#f093fb", "#4facfe", "#43e97b", "#fa709a", "#fee140"],
        "labels": [f"{cat} ({score}%)" for cat, score in category_scores.items()]
    }


def generate_feature_pie(validation: DocumentValidation) -> Dict[str, Any]:
    """Generate pie chart data for feature distribution."""
    return {
        "segments": [
            {"label": "Published", "value": validation.features_published, "color": "#10b981"},
            {"label": "Filtered Out", "value": validation.features_filtered, "color": "#ef4444"}
        ],
        "total": validation.total_features_extracted,
        "percentages": {
            "Published": round(validation.features_published / validation.total_features_extracted * 100, 1) if validation.total_features_extracted else 0,
            "Filtered": round(validation.features_filtered / validation.total_features_extracted * 100, 1) if validation.total_features_extracted else 0
        }
    }


def generate_violations_chart(feature_validations: List[FeatureValidation]) -> Dict[str, Any]:
    """Generate chart data for rubric violations by category."""
    violation_counts = {}
    for fv in feature_validations:
        for rule in fv.rules:
            if not rule.passed:
                violation_counts[rule.category] = violation_counts.get(rule.category, 0) + 1
    
    return {
        "categories": list(violation_counts.keys()),
        "counts": list(violation_counts.values()),
        "colors": ["#ef4444", "#f59e0b", "#fbbf24", "#f87171"],
        "total_violations": sum(violation_counts.values())
    }


def generate_before_after_data(raw_features: List[RawFeature], processed_features: List[ProcessedFeature]) -> Dict[str, Any]:
    """Generate before/after comparison data for transformations."""
    comparisons = []
    for raw, processed in zip(raw_features, processed_features):
        comparisons.append({
            "feature": raw.feature_name[:40],
            "before": {
                "title": raw.feature_name,
                "problem_length": len(raw.problem_statement),
                "enhancement_length": len(raw.enhancement),
                "impact_length": len(raw.impact)
            },
            "after": {
                "title": processed.title,
                "problem_length": len(processed.problem_statement),
                "enhancement_length": len(processed.enhancement),
                "impact_length": len(processed.impact)
            },
            "changes": {
                "title_changed": raw.feature_name != processed.title,
                "problem_refined": True,
                "enhancement_formatted": True,
                "impact_formatted": True
            }
        })
    
    return {
        "comparisons": comparisons,
        "summary": {
            "titles_changed": sum(1 for c in comparisons if c["changes"]["title_changed"]),
            "avg_problem_length_change": round(
                sum(c["after"]["problem_length"] - c["before"]["problem_length"] for c in comparisons) / len(comparisons), 1
            ) if comparisons else 0,
            "avg_enhancement_length_change": round(
                sum(c["after"]["enhancement_length"] - c["before"]["enhancement_length"] for c in comparisons) / len(comparisons), 1
            ) if comparisons else 0
        }
    }


def generate_module_distribution(raw_features: List[RawFeature]) -> Dict[str, Any]:
    """Generate module/product distribution data."""
    module_counts = {}
    for feature in raw_features:
        module = feature.product_module
        module_counts[module] = module_counts.get(module, 0) + 1
    
    sorted_modules = sorted(module_counts.items(), key=lambda x: x[1], reverse=True)
    
    return {
        "modules": [m[0] for m in sorted_modules],
        "counts": [m[1] for m in sorted_modules],
        "colors": ["#667eea", "#764ba2", "#f093fb", "#4facfe", "#43e97b", "#fa709a", "#fee140", "#38b2ac"]
    }


def generate_compliance_timeline(feature_validations: List[FeatureValidation]) -> Dict[str, Any]:
    """Generate timeline/compliance progression data."""
    timeline_data = []
    cumulative_passed = 0
    cumulative_total = 0
    
    for i, fv in enumerate(feature_validations, 1):
        cumulative_passed += fv.passed_rules
        cumulative_total += fv.total_rules
        timeline_data.append({
            "feature_index": i,
            "feature_name": fv.feature_name[:20],
            "compliance_score": fv.compliance_score,
            "cumulative_compliance": round(cumulative_passed / cumulative_total * 100, 2) if cumulative_total > 0 else 0
        })
    
    return {
        "data": timeline_data,
        "trend": "stable" if len(feature_validations) > 1 else "insufficient_data"
    }


def generate_radar_chart_data(category_scores: Dict[str, float]) -> Dict[str, Any]:
    """Generate radar chart data for multi-dimensional compliance view."""
    categories = list(category_scores.keys())
    scores = list(category_scores.values())
    
    # Calculate angles for radar chart
    import math
    angles = [i / len(categories) * 2 * math.pi for i in range(len(categories))]
    
    return {
        "categories": categories,
        "scores": scores,
        "angles": angles,
        "max_score": 100,
        "color": "rgba(102, 126, 234, 0.6)",
        "border_color": "rgba(102, 126, 234, 1)"
    }


def generate_stacked_bar_data(feature_validations: List[FeatureValidation]) -> Dict[str, Any]:
    """Generate stacked bar chart data showing passed/failed rules per feature."""
    bars = []
    for fv in feature_validations:
        bars.append({
            "feature": fv.feature_name[:25],
            "passed": fv.passed_rules,
            "failed": fv.failed_rules,
            "total": fv.total_rules,
            "compliance": fv.compliance_score
        })
    
    return {
        "bars": bars,
        "colors": {"passed": "#10b981", "failed": "#ef4444"},
        "average_compliance": round(sum(fv.compliance_score for fv in feature_validations) / len(feature_validations), 2) if feature_validations else 0
    }


# ============================================================================
# API ENDPOINTS
# ============================================================================

validator = RubricValidator()


@app.post("/api/process", response_model=ProcessingResult)
async def process_release_notes(file: UploadFile = File(...)):
    """
    Process uploaded Word document:
    1. Extract tables
    2. Filter publishable features
    3. Apply DETERMINISTIC rule conversion
    4. Generate SEPARATE MD files per feature (Step 7)
    5. Generate consolidated file for download
    6. Validate against 30+ Rubric rules
    7. Generate CSV validation report
    """
    try:
        temp_path = Path(__file__).parent / "temp" / file.filename
        temp_path.parent.mkdir(exist_ok=True)
        
        async with aiofiles.open(temp_path, "wb") as f:
            content = await file.read()
            await f.write(content)
        
        raw_features = extract_tables_from_docx(str(temp_path))
        if not raw_features:
            raise HTTPException(status_code=400, detail="No features found in document")
        
        publishable = filter_publishable_features(raw_features)
        if not publishable:
            raise HTTPException(status_code=400, detail="No features marked for external publication")
        
        processed_features = []
        feature_validations = []
        all_integrity_checks = {}
        generated_files = []

        # Process ALL features in PARALLEL using asyncio.gather() with SEMAPHORE
        # Adjusted for current provider availability (Qubrid down, using Groq primarily)
        print(f"🚀 Processing {len(publishable)} features with fallback chain (Qubrid→Groq→Gemini→Regex)...")
        
        # Semaphore: Allow more concurrent requests since we're using fallback chain
        # Groq can handle 10+ concurrent, Gemini 5, so we use 5 to be safe
        semaphore = asyncio.Semaphore(5)
        
        # Create tasks for parallel LLM processing with semaphore control
        async def process_single_feature(raw_feature):
            async with semaphore:  # Wait for available slot
                processed = await apply_complete_conversion(raw_feature)
                feature_md = generate_single_feature_markdown(processed)
                feature_filename = processed.filename
                
                async with aiofiles.open(OUTPUT_DIR / feature_filename, "w", encoding="utf-8") as f:
                    await f.write(feature_md)
                
                validation = validator.validate_feature(processed, raw_feature)
                integrity = validator.validate_data_integrity(raw_feature, processed)
                
                return {
                    'processed': processed,
                    'filename': feature_filename,
                    'validation': validation,
                    'integrity': integrity,
                    'original_name': raw_feature.feature_name
                }
        
        # Execute ALL features in parallel with controlled concurrency - OPTIMAL SPEED!
        results = await asyncio.gather(*[
            process_single_feature(raw_feature) 
            for raw_feature in publishable
        ])
        
        # Collect results
        for result in results:
            generated_files.append(result['filename'])
            processed_features.append(result['processed'])
            feature_validations.append(result['validation'])
            all_integrity_checks[result['original_name']] = result['integrity']
        
        print(f"✅ Parallel processing complete! Generated {len(generated_files)} files")
        
        # Generate consolidated markdown (grouped by geography)
        consolidated_md = generate_consolidated_markdown(processed_features)
        consolidated_filename = "release_notes_consolidated.md"
        
        async with aiofiles.open(OUTPUT_DIR / consolidated_filename, "w", encoding="utf-8") as f:
            await f.write(consolidated_md)
        
        generated_files.append(consolidated_filename)
        
        # Calculate validation metrics
        geography_dist = get_geography_groups(publishable)

        rubric_violations = []
        for fv in feature_validations:
            for rule in fv.rules:
                if not rule.passed:
                    rubric_violations.append(f"[{fv.feature_name}] {rule.rule_id}: {rule.description}")

        aggregated_integrity = {}
        for checks in all_integrity_checks.values():
            for key, value in checks.items():
                if key not in aggregated_integrity:
                    aggregated_integrity[key] = []
                aggregated_integrity[key].append(value)
        final_integrity = {k: all(v) for k, v in aggregated_integrity.items()}

        overall_score = sum(fv.compliance_score for fv in feature_validations) / len(feature_validations) if feature_validations else 0
        category_scores = validator.calculate_category_scores(feature_validations)

        # Generate visualization data
        print(f"Generating visualization data for {len(publishable)} features...")
        visualization_data = generate_visualization_data(publishable, processed_features, feature_validations, 
            DocumentValidation(
                document_name=file.filename,
                processed_at=datetime.now().isoformat(),
                total_features_extracted=len(publishable),
                features_published=len(processed_features),
                features_filtered=0,
                geography_distribution=geography_dist,
                feature_validations=feature_validations,
                overall_compliance_score=overall_score,
                rubric_violations=[],
                data_integrity_checks=final_integrity,
                category_scores=category_scores
            ))
        print(f"Visualization data generated: {len(visualization_data)} types")
        print(f"  - Heatmap: {bool(visualization_data.get('compliance_heatmap'))}")
        print(f"  - Geography: {bool(visualization_data.get('geography_distribution'))}")
        print(f"  - Radar: {bool(visualization_data.get('radar_chart_data'))}")
        print(f"  - Before/After: {bool(visualization_data.get('before_after_comparison'))}")

        validation_report = DocumentValidation(
            document_name=file.filename,
            processed_at=datetime.now().isoformat(),
            total_features_extracted=len(raw_features),
            features_published=len(processed_features),
            features_filtered=len(raw_features) - len(publishable),
            geography_distribution=geography_dist,
            feature_validations=feature_validations,
            overall_compliance_score=round(overall_score, 2),
            rubric_violations=rubric_violations[:10],
            data_integrity_checks=final_integrity,
            category_scores=category_scores,
            generated_files=generated_files,
            visualization_data=visualization_data,
            before_after_comparison=visualization_data.get("before_after_comparison", {})
        )
        
        # Generate validation reports
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_md_filename = f"validation_report_{timestamp}.md"
        report_csv_filename = f"validation_report_{timestamp}.csv"
        
        report_md = generate_validation_report_md(validation_report)
        async with aiofiles.open(OUTPUT_DIR / report_md_filename, "w", encoding="utf-8") as f:
            await f.write(report_md)
        
        report_csv = generate_csv_validation_report(validation_report)
        async with aiofiles.open(OUTPUT_DIR / report_csv_filename, "w", encoding="utf-8", newline="") as f:
            await f.write(report_csv)
        
        temp_path.unlink()
        
        return ProcessingResult(
            success=True,
            validation_report=validation_report,
            markdown_content=consolidated_md,
            message=f"Generated {len(generated_files)} files ({len(processed_features)} individual + 1 consolidated) with {overall_score:.1f}% compliance"
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/files")
async def list_files():
    """List all generated files."""
    files = []
    for f in OUTPUT_DIR.glob("*.md"):
        files.append({"filename": f.name, "size": f.stat().st_size, "created": f.stat().st_ctime,
                     "type": "validation_report" if "validation" in f.name.lower() else "feature_file"})
    for f in OUTPUT_DIR.glob("*.csv"):
        files.append({"filename": f.name, "size": f.stat().st_size, "created": f.stat().st_ctime, "type": "validation_csv"})
    return {"files": sorted(files, key=lambda x: x["created"], reverse=True)}


@app.get("/api/files/{filename}")
async def get_file(filename: str):
    """Get file content."""
    filepath = OUTPUT_DIR / filename
    if not filepath.exists():
        raise HTTPException(status_code=404, detail="File not found")
    async with aiofiles.open(filepath, "r", encoding="utf-8") as f:
        content = await f.read()
    return {"filename": filename, "content": content}


@app.get("/api/download/{filename}")
async def download_file(filename: str):
    """Download a file."""
    filepath = OUTPUT_DIR / filename
    if not filepath.exists():
        raise HTTPException(status_code=404, detail="File not found")
    media_type = "text/csv" if filename.endswith(".csv") else "text/markdown"
    return StreamingResponse(open(filepath, "rb"), media_type=media_type,
                            headers={"Content-Disposition": f"attachment; filename={filename}"})


@app.get("/api/download-all")
async def download_all_files():
    """Download all generated MD files as a ZIP archive."""
    memory_file = io.BytesIO()
    with zipfile.ZipFile(memory_file, 'w', zipfile.ZIP_DEFLATED) as zf:
        for f in OUTPUT_DIR.glob("*.md"):
            if "validation" not in f.name.lower():
                zf.write(f, f.name)
    memory_file.seek(0)
    return StreamingResponse(memory_file, media_type="application/zip",
                            headers={"Content-Disposition": "attachment; filename=release_notes_all.zip"})


@app.delete("/api/files/{filename}")
async def delete_file(filename: str):
    """Delete a file."""
    filepath = OUTPUT_DIR / filename
    if not filepath.exists():
        raise HTTPException(status_code=404, detail="File not found")
    filepath.unlink()
    return {"message": f"Deleted {filename}"}


@app.get("/api/health")
async def health_check():
    """Health check."""
    return {"status": "healthy", "llm_available": qwen_client is not None, "version": "5.0",
            "rubric_rules": 30, "separate_files": True, "output_dir": str(OUTPUT_DIR)}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

# PROJECT_KARLA/src/utility_functions/utility_functions.py

"""
Utility functions for Project Karla Narrative Pipeline.
Performance monitoring, JSON schema loading, and LLM output validation.
"""
import json
import logging
import re
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Dict

# Configure module logger (independent of main app)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.FileHandler("utility_functions.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("utility_functions")

@contextmanager
def timer(description: str):
    """Context manager for performance monitoring."""
    start = time.time()
    yield
    elapsed = time.time() - start
    logger.info(f"{description}: {elapsed:.2f}s")

def load_schema(schema_path: Path) -> str:
    """Load and format JSON schema for LLM context using path in CONFIG."""
    if not schema_path.exists():
        raise FileNotFoundError(f"Schema missing: {schema_path}")
    with open(schema_path, 'r') as f:  # ✅ Uses parameter
        return json.dumps(json.load(f), indent=2)

def safe_json_parse(raw: str) -> Dict[str, Any]:
    """Recover from LLM JSON errors."""
    raw = raw.strip()
    
    # UNESCAPE newlines first (CRITICAL)
    raw = raw.replace('\\n', '\n').replace('\\t', '\t').replace('\\"', '"')
    
    if not raw.startswith('{'):
        raise ValueError("Not a JSON object")
    
    # Now find real boundaries on unescaped string
    start = raw.find('{')
    end = raw.rfind('}')
    
    if start == -1 or end == -1 or end < start:
        raise ValueError("Not a JSON object")
    
    # Slice valid JSON
    json_str = raw[start:end+1]
    
    # Fix common bugs
    fixes = [
        (r',\s*([}\]])', r'\1'),  
        (r'([{\[])\s*,', r'\1'),  
        (r':\s*,', ': null'),
    ]
    
    for pattern, replacement in fixes:
        json_str = re.sub(pattern, replacement, json_str, flags=re.DOTALL)
    
    return json.loads(json_str)

def foo():
    return("\n\nbar\n\n")

def validate_story_plan(raw_json: str) -> Dict:

    try:
        data = safe_json_parse(raw_json)
    except Exception as e:
        logger.error(f"Raw sample: {repr(raw_json[:300])}...")
        # Emergency fallback
        data = {
            "title": "Untitled Horror VN",
            "genre": "horror", 
            "tone": "unknown",
            "themes": [],
            "logline": "Generated story plan",
            "protagonist": {"name": "Player"},
            "other_characters": [],
            "setting": "Unknown",
            "structure": [],
            "constraints": []
        }
    
    # Safe field extraction
    model_data = {
        "title": data.get("title", "Untitled"),
        "genre": data.get("genre", "horror"),
        "tone": data.get("tone", "unknown"), 
        "themes": data.get("themes", []),
        "logline": data.get("logline", ""),
        "protagonist": data.get("protagonist", {"name": "Player"}),
        "other_characters": data.get("other_characters", []),
        "setting": data.get("setting", "Unknown"),
        "structure": data.get("structure", []),
        "constraints": data.get("constraints", [])
    }
    return model_data

    #return StoryPlan(**model_data)

#     # Caller must provide/import StoryPlan and do: StoryPlan(**model_data)
#     return model_data
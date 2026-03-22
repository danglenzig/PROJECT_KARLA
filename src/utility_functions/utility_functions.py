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
from pydantic import ValidationError

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
    
    if not raw.startswith('{'):
        raise ValueError("Not a JSON object")
    
    # Now find real boundaries on unescaped string
    start = raw.find('{')
    end = raw.rfind('}')
    
    if start == -1 or end == -1 or end < start:
        raise ValueError("Not a JSON object")
    
    # Slice valid JSON
    json_str = raw[start:end+1]

    fixes = [
        # Fix "naked" backslashes that aren't followed by valid JSON escape chars
        # This looks for a \ NOT followed by ["\/bfnrtu] and replaces it with \\
        (r'\\(?![\\\"\/bfnrtu])', r'\\\\'),

        # remove trailing braces commas
        (r',\s*}', '}'),
        # remove trailing bracket commas
        (r',\s*\]', ']'),
        # remove leading braces commas
        (r'{\s*,', '{'),
        # remove leading bracket commas
        (r'\[\s*,', '['),
        # fix "empty" values (:,)
        (r':\s*}', ': null}'),
        # fix "empty" values followed by another key (:,)
        (r':\s*,', ': null,'),
        # clean up double commas
        (r',\s*,', ','),
    ]


    FIX_ITER_MAX = 10
    fix_count = 0
    while fix_count < FIX_ITER_MAX:

        fix_count += 1
        logger.info(f"JSON fix pass: {fix_count}")
        print(f"\nJSON fix pass: {fix_count}\n")
        
        original = json_str

        for pattern, replacement in fixes:

            json_str, count = re.subn(pattern, replacement, json_str, flags=re.DOTALL)
            if count > 0:
                msg = f"Rule [{pattern}] fixed {count} occurrence(s) on pass {fix_count}"
                logger.info(msg)
                print(msg)
            # if ^^this actually makes a substitution, I want to see it in the log.
            # I want to know what errors are being fixed, so I can deal with it 
            # upstream in the system prompt for the agent generating this data.

        if json_str == original:
            break
    if fix_count >= FIX_ITER_MAX:
        raise ValidationError("Hopelessly broken JSON")
    
    try:
        return json.loads(json_str)
    except Exception as e:
        logger.error(f"JSON Validation error: {e}")
        print(f"JSON Validation error: {e}")




def foo():
    return("\n\nbar\n\n")

def validate_story_plan(raw_json: str) -> Dict:

    data = safe_json_parse(raw_json)


    # FAILSAFE logic. Use later. For now, we want to fail hard and see the JSON problem.
    # try:
    #     data = safe_json_parse(raw_json)
    # except Exception as e:
    #     logger.error(f"Raw sample: {repr(raw_json[:300])}...")
    #     # Emergency fallback
    #     data = {
    #         "title": "Untitled Horror VN",
    #         "genre": "horror", 
    #         "tone": "unknown",
    #         "themes": [],
    #         "logline": "Generated story plan",
    #         "protagonist": {"name": "Player"},
    #         "other_characters": [],
    #         "setting": "Unknown",
    #         "structure": [],
    #         "constraints": []
    #     }
    
    # Fail-Safe field extraction
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
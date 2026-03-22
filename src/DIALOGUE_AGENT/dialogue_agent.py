import sys
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from dotenv import load_dotenv
from pydantic import BaseModel, Field, ValidationError
from openai import OpenAI

CLI_MODE: bool = True

# PROJECT_KARLA/src/
SRC_ROOT = Path(__file__).parent.parent  # src/TESTING -> src

# PROJECT_KARLA/src/utility_functions/
UTILITY_PATH = SRC_ROOT / "utility_functions" 
sys.path.insert(0, str(UTILITY_PATH))

# PROJECT_KARLA/src/qdrant_tools/
QDRANT_PATH = SRC_ROOT / "qdrant_tools"
sys.path.insert(0, str(QDRANT_PATH))

# PROJECT_KARLA/src/prompt_builder
PROMPT_BLDR_PATH = SRC_ROOT / "prompt_builder"
sys.path.insert(0, str(PROMPT_BLDR_PATH))

# PROJECT_KARLA/src/core_data_models
CORE_DATA_MODELS_PATH = SRC_ROOT / "core_data_models"
sys.path.insert(0, str(CORE_DATA_MODELS_PATH))

from utility_functions import timer, load_schema, foo, validate_story_plan
from qdrant_tools import qdrant_foo, search_genre_examples, search_genre_howto
from prompt_builder import prompt_builder_foo, build_system_prompt
from core_data_models import dm_foo, StepType, ReasoningStep, StoryPlan, AgentConfig



def get_dialogue():
    pass
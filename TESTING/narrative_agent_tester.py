
"""
Narrative Agent v2.0 - Production-Ready Visual Novel Story Planner
Transforms user prompts into validated StoryPlan JSON via structured reasoning.
Part of Project Karla's Narrative Studio pipeline.
"""

import os
import sys
import json
import logging
import re
import time
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from dotenv import load_dotenv
from pydantic import BaseModel, Field, ValidationError
from enum import Enum
from openai import OpenAI
from contextlib import contextmanager
from langchain_qdrant import QdrantVectorStore
from langchain_openai import OpenAIEmbeddings
from qdrant_client import QdrantClient

PROJECT_ROOT = Path(__file__).parent.parent  # TESTING -> PROJECT_KARLA
UTILITY_PATH = PROJECT_ROOT / "UTILITY_FUNCTIONS"
sys.path.insert(0, str(UTILITY_PATH))

from utility_functions import foo, timer, load_schema, safe_json_parse

print(foo())



# configure logging first -- production best practice
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.FileHandler("narrative_agent_tester.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("narrative_agent_tester")

# load environment variables
load_dotenv()

# ===========================================================
# CORE DATA MODELS
# ===========================================================

class StepType(str, Enum):
    """Agent reasoning steps - finite state machine transitions."""
    START = "START"           # Echo user input
    CONTEXTUALIZE = "CONTEXTUALIZE"  # Identify genre
    PLAN = "PLAN"             # Outline reasoning
    TOOL = "TOOL"             # Request tool call  
    OBSERVE = "OBSERVE"        # Process tool result
    OUTPUT = "OUTPUT"         # Final validated JSON

class ReasoningStep(BaseModel):
    """Single step in agent's reasoning chain."""
    step: StepType = Field(..., description="Current reasoning phase")
    content: Optional[str] = Field(None, description="Text content or JSON")
    tool: Optional[str] = Field(None, description="Tool name if TOOL step")
    tool_input: Optional[str] = Field(None, description="JSON string tool params")
    tool_output: Optional[str] = Field(None, description="Raw tool result")

@dataclass(frozen=True)
class StoryPlan:
    """Validated output schema - feeds downstream VN generator."""
    title: str
    genre: str
    tone: str
    themes: List[str]
    logline: str
    protagonist: Dict[str, Any]
    other_characters: List[Dict[str, Any]]
    setting: str
    structure: List[Dict[str, Any]]
    constraints: List[str]

# ===========================================================
# CONFIGURATION
# ===========================================================

@dataclass(frozen=True)
class Config:
    """Centralized, type-safe configuration."""
    openai_model: str = "gpt-4.1"
    qdrant_url: str = "http://localhost:6333"
    max_iterations: int = 20
    max_tokens: int = 4000


    schemas_dir: Path = field(default_factory=lambda: Path(__file__).parent.parent / "SCHEMAS") # relative lovation of the SCHEMAS folder

    # QDRANT COLLECTIONS
    howto_collections: Dict[str, str] = field(init=False)
    examples_collections: Dict[str, str] = field(init=False)

    def __post_init__(self):
        """Runtime initialization for computed properties."""
        object.__setattr__(
            self,
            "howto_collections", {
                "horror": "horror_howto",
                "mystery": "mystery_howto",
                "romance": "romance_howto"
            }
        )
        object.__setattr__(
            self,
            "examples_collections", {
                "horror": "horror_examples",
                "mystery": "mystery_examples",
                "romance": "romance_examples"
            }
        )

    @property
    def schema_path(self) -> Path:
        """Computed: Full path to narrative_spec.json."""
        return self.schemas_dir / "narrative_spec.json"
    
    @property
    def project_root(self) -> Path:
        """Computed: PROJECT_KARLA/ root directory."""
        return self.schemas_dir.parent  # SCHEMAS → PROJECT_KARLA
    
    def validate_paths(self) -> None:
        """Production check: Ensure all paths exist."""
        paths = [
            self.schema_path,
            self.project_root / "TESTING"
        ]
        for path in paths:
            if not path.exists():
                raise FileNotFoundError(f"Missing: {path}")
            
CONFIG = Config()
CONFIG.validate_paths()
logger.info(f"CONFIG LOADED: {CONFIG.schema_path}")

# ===========================================================
# UTILITY FUNCTIONS
# ===========================================================



# @contextmanager
# def timer(description: str):
#     """Context manager for performance monitoring."""
#     start = time.time()
#     yield
#     elapsed = time.time() - start
#     logger.info(f"{description}: {elapsed:.2f}s")

# def load_schema(schema_path: Path) -> str:
#     """Load and format JSON schema for LLM context using path in CONFIG."""
#     if not schema_path.exists():
#         raise FileNotFoundError(f"Schema missing: {schema_path}")
#     with open(schema_path, 'r') as f:  # ✅ Uses parameter
#         return json.dumps(json.load(f), indent=2)
    
# def safe_json_parse(raw: str) -> Dict[str, Any]:
#     """Recover from LLM JSON errors."""
#     raw = raw.strip()
    
#     # UNESCAPE newlines first (CRITICAL)
#     raw = raw.replace('\\n', '\n').replace('\\t', '\t').replace('\\"', '"')
    
#     if not raw.startswith('{'):
#         raise ValueError("Not a JSON object")
    
#     # Now find real boundaries on unescaped string
#     start = raw.find('{')
#     end = raw.rfind('}')
    
#     if start == -1 or end == -1 or end < start:
#         raise ValueError("Not a JSON object")
    
#     # Slice valid JSON
#     json_str = raw[start:end+1]
    
#     # Fix common bugs
#     fixes = [
#         (r',\s*([}\]])', r'\1'),  
#         (r'([{\[])\s*,', r'\1'),  
#         (r':\s*,', ': null'),
#     ]
    
#     for pattern, replacement in fixes:
#         json_str = re.sub(pattern, replacement, json_str, flags=re.DOTALL)
    
#     return json.loads(json_str)

def validate_story_plan(raw_json: str) -> StoryPlan:

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

    return StoryPlan(**model_data)


# # =============================================================================
# # QDRANT TOOLS
# # =============================================================================

qdrant_url = CONFIG.qdrant_url
qdrant_client = QdrantClient(qdrant_url)
embedding_model = OpenAIEmbeddings(model="text-embedding-3-large")

def collection_exists(client: QdrantClient, collection_name: str) -> bool:
    try:
        client.get_collection(collection_name)
        return True
    except:
        return False
    
def get_genre_howto_db(genre_name: str):

    howto_name = CONFIG.howto_collections[genre_name]
    
    if not collection_exists(qdrant_client, howto_name):
        raise ValueError(f"ERROR: Can't find howto for genre: {genre_name}")
    
    return QdrantVectorStore.from_existing_collection(
        url=qdrant_url,
        collection_name=howto_name,
        embedding=embedding_model
    )

def get_genre_examples_db(genre_name: str):

    examples_name = CONFIG.examples_collections[genre_name]

    if not collection_exists(qdrant_client, examples_name):
        raise ValueError(f"ERROR: Can't find examples for genre: {genre_name}")
    
    return QdrantVectorStore.from_existing_collection(
        url=qdrant_url,
        collection_name=examples_name,
        embedding=embedding_model
    )

def search_genre_howto(genre_name: str, search_query: str):
    howto_db = get_genre_howto_db(genre_name)
    search_result = howto_db.similarity_search(query=search_query)
    return "\n\n\n".join(
        [ f"Context chunk {i+1}:\n{doc.page_content}"  for i, doc in enumerate(search_result)]
    )


def search_genre_examples(genre_name: str, search_query: str):
    examples_db = get_genre_examples_db(genre_name)
    search_result = examples_db.similarity_search(query=search_query)
    return "\n\n\n".join(
        [ f"Context chunk {i+1}:\n{doc.page_content}"  for i, doc in enumerate(search_result)]
    )

TOOLS = {
    "search_genre_howto": search_genre_howto,
    "search_genre_examples": search_genre_examples
}

# =============================================================================
# NARRATIVE AGENT (Main Logic)
# =============================================================================

class NarrativeAgent:
    """Production narrative planning agent."""
    def __init__(self, config_: Config):
        self.config = config_
        self.openai_client = OpenAI()
        self.schema = load_schema(config_.schema_path)
        self.messages_: List[Dict[str, str]] = []
        self.iteration = 0
        self.messages_.append(
            {"role": "system", "content": self._build_system_prompt()}
        )

    def _build_system_prompt(self) -> str:
        return f"""You are an expert narrative design AI assistant helping design short visual novel stories.

You operate as a small state machine using the following STEP types:
- START
- CONTEXTUALIZE
- PLAN
- TOOL
- OBSERVE
- OUTPUT

## ReasoningStep Schema Example
{{
  "step": "TOOL",
  "content": null,
  "tool": "search_genre_howto", 
  "tool_input": '{{"genre_name": "romance", "search_query": "slow-burn"}}',
  "tool_output": null
}}

### High-level behavior

1. START
   - Restate the user input in your own words in `content`.
   - Do NOT call tools in this step.

2. CONTEXTUALIZE
   - Briefly explain what kind of visual novel story is being requested.
   - Identify the **primary genre**. It MUST be one of:
     - "romance"
     - "mystery"
     - "horror"
   - Put the chosen genre name as a lowercase string into `content`, e.g. "romance".
   - Do NOT call tools in this step.

3. PLAN
   - Describe, in `content`, what you intend to do next (e.g. "Call howto + examples tools to gather genre context, then draft a Story Plan").
   - A PLAN step MAY request a TOOL call, or may just refine the plan.
   - If you intend to call a tool, emit a TOOL step in the NEXT turn, not in the same one.

4. TOOL
   - Use only the following tools:

     - search_genre_howto(genre_name: str, search_query: str)
     - search_genre_examples(genre_name: str, search_query: str)

   - `tool` MUST be exactly "search_genre_howto" or "search_genre_examples".
   - `tool_input` MUST be a JSON string of the form:
     - {{"genre_name": "romance" | "mystery" | "horror", "search_query": "<short natural language query>"}}

     Example:
     {{"genre_name": "romance", "search_query": "first kiss scene structure"}}

   - In a TOOL step:
     - `content` MUST be null.
     - `tool_output` MUST be null (the caller will fill it later).
     - `tool_input` MUST be a single JSON object string. Never use multiple braces, never use sets, arrays, or other formats.

5. OBSERVE
   - The caller will execute the tool and pass the raw text result back to you.
   - In an OBSERVE step:
     - Copy the tool name into `tool`.
     - Copy the same JSON string you used in `tool_input`.
     - Put the raw tool result into `tool_output`.
     - In `content`, briefly summarize what you learned from the tool output for the current story.

6. OUTPUT
   - This is the final result that will be sent to the schematizer.
   - In the OUTPUT step, `content` MUST be a JSON string describing a **Story Plan** the schematizer can work from.

   The Story Plan JSON MUST have the shape of the following OUTPUT schema (all keys required)

   OUTPUT Schema:
   {self.schema}

   - The OUTPUT step must NOT call tools.
   - Do not include any explanatory text outside this JSON in the OUTPUT `content`.
   - The schematizer will take this JSON and expand it into a full VN spec.

### General rules

- Always consult both the howto and examples tools before drafting your story plan.
- Always emit syntactically valid JSON for the ReasoningStep wrapper.
- Never mix multiple steps in one response.
- Never invent genre names outside: "romance", "mystery", "horror".
- Use tools for genre writing advice or stylistic examples.
- Use a three-act story structure.
- Each MUST consist of at least 2, and at most 4 scenes.
- Indicate which character is the main point-of-view character of the story. This will be the player character of the visual novel.
- Include detailed visual descriptions of all characters -- face, body, and clothing. These details will be used later as image generation prompts by another agent.
- Include detailed visual descriptions of all scene environments -- location, colors, lighting, etc. These details will be used later as image generation prompts by another agent.
- Include samples of narration, dialogue and/or monologue for each scene. These samples will be used later as example prompts for a dialogue generation agent.
"""
    def process_user_input(self, prompt: str) -> StoryPlan:
        """Prompt -> Narrative Spec"""
        self.messages_.append(
            {"role": "user", "content": prompt}
        )
        self.iteration = 0

        with timer("Full reasoning"):
            while self.iteration < self.config.max_iterations:
                self.iteration += 1
                step = self._take_step()

                if step.step == StepType.OUTPUT:
                    return self._handle_output(step)
                elif step.step == StepType.TOOL:
                    self._handle_tool_call(step)
            raise RuntimeError(f"Max iterations exceeded")
    
    def _take_step(self) -> ReasoningStep:

        response = self.openai_client.chat.completions.create(
            model = self.config.openai_model,
            messages = self.messages_,
            max_tokens = self.config.max_tokens,
            temperature = 0.1
        )

        raw_content = response.choices[0].message.content
        self.messages_.append(
            {"role": "assistant", "content": raw_content}
        )

        # tolerant parsing
        try:
            # Case 1: Proper ReasoningStep (your prompt works)
            step = ReasoningStep.model_validate_json(raw_content)
        except ValidationError:
        # Case 2: LLM output StoryPlan JSON directly (crash cause)
            logger.warning("LLM skipped wrapper - forcing OUTPUT step")
            step = ReasoningStep(
                step=StepType.OUTPUT,
                content=raw_content,  # Raw StoryPlan JSON
                tool=None, 
                tool_input=None, 
                tool_output=None
            )
        logger.info(f"Iter {self.iteration}: {step.step}, \nCONTENT:\n{step.content}\n")

        return step
    
    def _handle_tool_call(self, step: ReasoningStep):
        """Execute + inject OBSERVE"""
        _tool_name = step.tool
        _tool_input_dict = json.loads(step.tool_input)
        _tool_fn = TOOLS[_tool_name]
        _result = _tool_fn(_tool_input_dict["genre_name"], _tool_input_dict["search_query"])

        observe_step = ReasoningStep(
            step = StepType.OBSERVE,
            content = "Tool results processed",
            tool = _tool_name,
            tool_input = step.tool_input,
            tool_output = _result
        )
        self.messages_.append(
            {"role": "assistant", "content": observe_step.model_dump_json()}
        )

    def _handle_output(self, step: ReasoningStep) -> StoryPlan:
        """Final validation"""
        plan = validate_story_plan(step.content)
        logger.info("StoryPlan validated")
        return plan
    
def main():
    print("🎭 Narrative Agent v2.1 - Enter prompts below:")
    agent = NarrativeAgent(CONFIG)

    try:
        while True:
            prompt = input("---> ").strip()
            if not prompt:
                continue

            print("Thinking...")
            plan = agent.process_user_input(prompt)

            print("\n---STORY PLAN---\n")
            print(json.dumps(plan.__dict__, indent=2))
    except KeyboardInterrupt:
        print("\nExiting")
    except Exception as e:
        logger.error(f"Fatal: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()

# PROJECT_KARLA/src/NARRATIVE_AGENT/narrative_agent.py
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
from langchain_qdrant import QdrantVectorStore
from langchain_openai import OpenAIEmbeddings
from qdrant_client import QdrantClient


# PROJECT_KARLA/src/
SRC_ROOT = Path(__file__).parent.parent  # src/TESTING -> src

# PROJECT_KARLA/src/utility_functions/
UTILITY_PATH = SRC_ROOT / "utility_functions" 
sys.path.insert(0, str(UTILITY_PATH))

# PROJECT_KARLA/src/qdrant_tools/
QDRANT_PATH = SRC_ROOT / "qdrant_tools"
sys.path.insert(0, str(QDRANT_PATH))

# PROJECT_KARLA/src/prompt/builder
PROMPT_BLDR_PATH = SRC_ROOT / "prompt_builder"
sys.path.insert(0, str(PROMPT_BLDR_PATH))

from utility_functions import timer, load_schema, foo, validate_story_plan
from qdrant_tools import qdrant_foo, search_genre_examples, search_genre_howto
from prompt_builder import prompt_builder_foo, build_system_prompt

print(foo()) # should print "bar"
print(qdrant_foo()) # --> "qdrant_bar"
print(prompt_builder_foo()) # --> "prompt_builder_bar"

# configure logging first -- production best practice
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.FileHandler("narrative_agent.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("narrative_agent")

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

    schemas_dir: Path = field(default_factory=lambda: Path(__file__).parent.parent.parent / "SCHEMAS") # relative lovation of the SCHEMAS folder

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
            #self.project_root / "TESTING"
        ]
        for path in paths:
            if not path.exists():
                raise FileNotFoundError(f"Missing: {path}")
            
CONFIG = Config()
CONFIG.validate_paths()
logger.info(f"CONFIG LOADED: {CONFIG.schema_path}")

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
            {"role": "system", "content": build_system_prompt("narrative_agent")}
        )

    
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
        model_data = validate_story_plan(step.content)
        plan = StoryPlan(**model_data)
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

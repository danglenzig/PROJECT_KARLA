from enum import Enum
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from pathlib import Path

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

@dataclass(frozen=True)
class AgentConfig:
    openai_model: str = "gpt-4.1" # <--better creative writing & structured output
    qdrant_url: str = "http://localhost:6333"
    max_iterations: int = 20
    max_tokens: int = 4000

    #schemas_dir: Path = field(default_factory=lambda: Path(__file__).parent.parent.parent / "SCHEMAS") # relative lovation of the SCHEMAS folder

    # @property
    # def schema_path(self) -> Path:
    #     """Computed: Full path to narrative_spec.json."""
    #     return self.schemas_dir / "narrative_spec.json"
    
    # @property
    # def project_root(self) -> Path:
    #     """Computed: PROJECT_KARLA/ root directory."""
    #     return self.schemas_dir.parent  # SCHEMAS → PROJECT_KARLA
    
    # def validate_paths(self) -> None:
    #     """Production check: Ensure all paths exist."""
    #     paths = [
    #         self.schema_path,
    #         #self.project_root / "TESTING"
    #     ]
    #     for path in paths:
    #         if not path.exists():
    #             raise FileNotFoundError(f"Missing: {path}")

def dm_foo():
    print("\n\ndm_bar\n\n")

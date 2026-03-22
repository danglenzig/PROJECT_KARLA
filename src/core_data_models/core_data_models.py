from enum import Enum
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from dataclasses import dataclass

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

def dm_foo():
    print("\n\ndm_bar\n\n")

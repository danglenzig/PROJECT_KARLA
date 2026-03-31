# PROJECT_KARLA/src/prompt_builder/prompt_builder.py

from dataclasses import field
from pathlib import Path
from typing import Dict, Optional
import sys


# PROJECT_KARLA/src/
SRC_ROOT = Path(__file__).parent.parent  # src/TESTING -> src

# PROJECT_KARLA/src/utility_functions/
UTILITY_PATH = SRC_ROOT / "utility_functions" 
sys.path.insert(0, str(UTILITY_PATH))
from utility_functions import load_schema



schemas_dir = SRC_ROOT.parent / "SCHEMAS"
schema_paths_dict: Dict[str, Path] = {
    "draft_story": schemas_dir / "narrative_spec.json",
    #"dialogue_agent": schemas_dir / "dialogue_spec.json" TODO
}

def get_schema(schema_name: str) -> str:
    if (schema_name not in list(schema_paths_dict.keys())):
        raise ValueError(f"Invalid schema name: {schema_name}")
    s_path = schema_paths_dict[schema_name]
    return load_schema(s_path)

def prompt_builder_foo():
    return("\n\nprompt_builder_bar\n\n")

def build_dialogue_agent_system_prompt(schema: str, genre: str, research: str, user_prompt: str) -> str:
    return f"""
TODO: system prompt
"""

def build_draft_story_prompt(schema: str, genre: str, research: str, user_prompt: str) -> str:
    """Simplified prompt for drafting the story plan"""
    return f"""
GENRE: {genre}

USER PROMPT: {user_prompt}

RESEARCH CONTEXT: {research}

TASK: Generate complete StoryPlan JSON for a short visual novel based on the above user prompt, genre, and research context.

Output ONLY valid JSON matching this schema:
{schema}

Use the research context as needed for genre-specific howto advice and examples. Follow a three-act structure with 2-4 scenes per act.

Each scene MAY include a dialogue choice with 2 outcomes, but this is not required. If there are no choices, then the value of that scene's "choice" item MUST be "NONE", and the value of the "outcomes" item MUST be an empty list [].

Provide detailed visual descriptions of all characters -- these descriptions will be used as image generation prompts by another agent whose output will be used as dialogue portraits in the visual novel.

Provide detailed visual descriptions of all scene environments -- these descriptions will be used as image generation prompts by another agent whose output will be used as backgrounds in the visual novel.

Generate samples of narration, dialogue and/or monologue for each scene -- these samples will be used as example prompts for a dialogue generation agent.

IMPORTANT:
JSON structure (keys and string delimiters) MUST use standard double quotes ".
Inside all string values, use ONLY single quotes ' for any quoted text
DO NOT escape single quotes.
DO NOT use double quotes inside any values — if needed, replace them with single quotes.
"""

builder_dict = {
    "dialogue_agent": build_dialogue_agent_system_prompt,
    "draft_story": build_draft_story_prompt
}

def build_system_prompt(
        agent_name: str,
        genre: Optional[str] = None,
        research: Optional[str] = None,
        user_prompt: Optional[str] = None
) -> str:
    if not agent_name in list(builder_dict.keys()):
        raise ValueError(f"Unknown agent name (functions): {agent_name}")
    if not agent_name in list(schema_paths_dict.keys()):
        raise ValueError(f"Unknown agent name (schemas) : {agent_name}")
    schema: str = get_schema(agent_name)
    
    fn = builder_dict[agent_name]
    return fn(schema, genre, research, user_prompt)
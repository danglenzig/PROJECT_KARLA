####################
# Narrative Tester #
####################

from langchain_qdrant import QdrantVectorStore
from langchain_openai import OpenAIEmbeddings
from qdrant_client import QdrantClient
from enum import Enum
from pydantic import BaseModel, ValidationError, Field
from typing import Optional
import json
import os
import sys
from dotenv import load_dotenv
from openai import OpenAI


sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__)))) # makes the following imports possible
from SCHEMAS.get_schema import get_schema



load_dotenv()
openai_client: OpenAI = OpenAI()
#openai_model: str = "gpt-4o-mini"
openai_model: str = "gpt-4.1"
qdrant_url = "http://localhost:6333"
qdrant_client = QdrantClient("http://localhost:6333")
embedding_model = OpenAIEmbeddings(model="text-embedding-3-large")

class StepType(str, Enum):
    START           = "START"
    CONTEXTUALIZE   = "CONTEXTUALIZE"
    PLAN            = "PLAN"
    TOOL            = "TOOL"
    OBSERVE         = "OBSERVE"
    OUTPUT          = "OUTPUT"

class GenreName(str, Enum):
    HORROR  = "horror"
    MYSTERY = "mystery"
    ROMANCE = "romance"
    # more later...

class ReasoningStep(BaseModel):
    step: StepType
    content: Optional[str] = Field(None, description = "The string content of the step")
    tool: Optional[str] = Field(None, description = "The ID of the tool to call")
    tool_input: Optional[str] = Field(None, description = "The input parameters to the tool, if this is a TOOL step")
    tool_output: Optional[str] = Field(None, description = "The string output of the tool, if this is an OBSERVE step")

class StoryPlan(BaseModel):
    title: str
    genre: str
    tone: str
    themes: list[str]
    logline: str
    protagonist: dict
    other_characters: Optional[list[dict]]
    setting: str
    structure: list[dict]
    constraints: Optional[list[str]]

howto_collection_dict = {
    # GenreName.HORROR: "horror_howto",
    # GenreName.MYSTERY: "mystery_howto",
    # GenreName.ROMANCE: "romance_howto"
    "horror": "horror_howto",
    "mystery": "mystery_howto",
    "romance": "romance_howto"
    
}

examples_collection_dict = {
    # GenreName.HORROR: "horror_examples",
    # GenreName.MYSTERY: "mystery_examples",
    # GenreName.ROMANCE: "romance_examples"
    "horror": "horror_examples",
    "mystery": "mystery_examples",
    "romance": "romance_examples"
}



def collection_exists(
        client: QdrantClient,
        collection_name_: str
):
    try:
        client.get_collection(collection_name_)
        return True
    except Exception:
        return False

def get_genre_howto_db(genre_name: str):

    howto_name = howto_collection_dict[genre_name]
    
    if not collection_exists(qdrant_client, howto_name):
        raise ValueError(f"ERROR: Can't find howto for genre: {genre_name}")
    
    return QdrantVectorStore.from_existing_collection(
        url=qdrant_url,
        collection_name=howto_name,
        embedding=embedding_model
    )

def get_genre_examples_db(genre_name: str):

    examples_name = examples_collection_dict[genre_name]

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

AVAILABLE_TOOLS = {
    "search_genre_howto": search_genre_howto,
    "search_genre_examples": search_genre_examples
}

NARRATIVE_SCHEMA = get_schema("narrative_spec.json")

SYSTEM_PROMPT = f"""
You are an expert narrative design AI assistant helping design short visual novel stories.

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
   {NARRATIVE_SCHEMA}

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


# create embedding model
embedding_model: OpenAIEmbeddings = OpenAIEmbeddings(
    model = "text-embedding-3-large"
)


def collection_exists(
        client: QdrantClient,
        collection_name_: str
):
    try:
        client.get_collection(collection_name_)
        return True
    except Exception:
        return False

def fix_llm_json(raw:str) -> str:
    """Fix LLM-generated JSON: trailing commas, duplicate keys, whitespace"""
    lines = raw.strip().split('\n')
    fixed = []

    for line in lines:
        line = line.strip()
        if not line: continue

        # remove trailing commas before ) or ]
        line = line.rstrip(',')
        if line.endswith(',') and (line.count('{') != line.count('}') or line.count('[') != line.count(']')):
            line = line[:-1]
        
        # clean up common llm artifacts
        line = line.replace(',,', ',').replace(',}', '}').replace(',]', ']')
        fixed.append(line)

        if 'setting' in raw and raw.strip().endswith('...'):
            raw += '"setting": "Default setting description.", "structure": [], "constraints": []}'

    return ' '.join(fixed)

message_history = [
    { "role": "system", "content": SYSTEM_PROMPT }
]

user_input: str = input("\n\n--> ")
message_history.append(
    { "role": "user", "content": user_input }
)

WHILE_MAX = 500
failsafe = 0


while failsafe < WHILE_MAX:
    failsafe += 1

    response = openai_client.chat.completions.parse(
        model           =openai_model,
        response_format =ReasoningStep,
        messages        =message_history
    )

    raw_result = response.choices[0].message.content

    message_history.append(
        { "role": "assistant", "content": raw_result }
    )

    try:
        # check that the raw result conforms to the ResoningStep schema
        step_data = ReasoningStep.model_validate_json(raw_result)
        

        if (step_data.step == StepType.CONTEXTUALIZE) or (step_data.step == StepType.PLAN) or (step_data.step == StepType.START):
            print(f"\n{step_data.step}: {step_data.content}\n")
            continue

        if (step_data.step == StepType.TOOL):
            print(f"Calling tool: {step_data.tool} tool with input {step_data.tool_input}")
            print(f"DEBUG tool_input type: {type(step_data.tool_input)}")

            try:

                # force to str
                tool_input_str = str(step_data.tool_input)

                tool_args = json.loads(tool_input_str)
                genre_name = tool_args["genre_name"]
                search_query = tool_args["search_query"]

                tool_fn = AVAILABLE_TOOLS[step_data.tool]
                tool_response = tool_fn(genre_name, search_query)

                message_history.append(
                    {
                        "role": "assistant",
                        "content": json.dumps(
                            {
                                "step": "OBSERVE",
                                "content": f"Observed output from tool {step_data.tool}",
                                "tool": step_data.tool,
                                "tool_input": tool_input_str,
                                "tool_output": tool_response,
                            }
                        )
                    }
                )
                print(f"\n{step_data.step}: {step_data.tool}\n")
                print(f"\nTOOL RESPONSE: {tool_response}\n")
                continue
            except Exception as err:
                print(f"Tool error: {err}")
                break

        if step_data.step == StepType.OUTPUT:

            stripped_raw = step_data.content.strip()

            fixed_json = fix_llm_json(stripped_raw)



            try:
                story_plan = StoryPlan.model_validate_json(fixed_json)
                print("---StoryPlan VALIDATION SUCCEEDS---\n")
                print(story_plan.model_dump_json(indent=2))


            except Exception as pydantic_err:
                try:
                    print("---PYDANTIC VALIDATION FAIL---\n---RAW JSON (UNVALIDATED)---\n")
                    data = json.loads(fixed_json)
                    print(json.dumps(data, indent=2))
                    print(f"{pydantic_err}")

                except json.JSONDecodeError as json_err:
                    print("---MALFORMED JSON---\n")
                    print(stripped_raw[:2000] + "..." if len(stripped_raw) > 2000 else stripped_raw)
                    print(f"JSON ERROR: {json_err}")

            break

    except ValidationError as v_err:
        print(f"The LLM went off-script: {v_err.json()}")
        break

if failsafe >= WHILE_MAX:
    print("Reasoning recurrsion limit reached")
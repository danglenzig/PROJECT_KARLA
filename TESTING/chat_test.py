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

from dotenv import load_dotenv
from openai import OpenAI

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

    # validate that genre_name is a valid key in howto_collection_dict -- how?

    howto_db = get_genre_howto_db(genre_name)
    search_result = howto_db.similarity_search(query=search_query)
    return "\n\n\n".join(
        [ f"Context chunk {i+1}:\n{doc.page_content}"  for i, doc in enumerate(search_result)]
    )


def search_genre_examples(genre_name: str, search_query: str):

    # validate that genre_name is a valid key in examples_collection_dict -- how?

    examples_db = get_genre_examples_db(genre_name)
    search_result = examples_db.similarity_search(query=search_query)
    return "\n\n\n".join(
        [ f"Context chunk {i+1}:\n{doc.page_content}"  for i, doc in enumerate(search_result)]
    )

AVAILABLE_TOOLS = {
    "search_genre_howto": search_genre_howto,
    "search_genre_examples": search_genre_examples
}


SYSTEM_PROMPT = """
You are an expert narrative design AI assistant helping design short visual novel stories.

You operate as a small state machine using the following STEP types:
- START
- CONTEXTUALIZE
- PLAN
- TOOL
- OBSERVE
- OUTPUT

At each model call you MUST emit exactly ONE JSON object matching the ReasoningStep schema:
{"step": "START" | "CONTEXTUALIZE" | "PLAN" | "TOOL" | "OBSERVE" | "OUTPUT",
 "content": "string or null",
 "tool": "string or null",
 "tool_input": "string or null",
 "tool_output": "string or null"
}

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
     - {"genre_name": "romance" | "mystery" | "horror", "search_query": "<short natural language query>"}

     Example:
     {"genre_name": "romance", "search_query": "first kiss scene structure"}

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

   The Story Plan JSON MUST have this shape (all keys required):

    {
    "title": "Short working title for the VN",
    "genre": "genre name", 
    "tone": "short phrase (e.g. 'bittersweet, slow-burn')",
    "themes": ["theme 1", "theme 2"],
    "logline": "1-2 sentence high-level premise",
    "protagonist": {
        "name": "string or null",
        "age": "approximate age or null",
        "role": "short phrase",
        "visual_description": "face, body, clothing, etc"
    },
    "other_characters": [
        {
        "name": "string",
        "age": "approximate age or null",
        "role": "short phrase",
        "visual_description": "description"
        }
    ],
    "setting": "1-3 sentences describing time and place",
    "structure": [
        {
        "act_id": "a1",
        "scenes": [
            {
            "scene_id": "s1",
            "label": "Scene Label",
            "summary": "2-3 sentences of action",
            "choice": "description of the main player choice",
            "outcomes": ["Outcome A", "Outcome B"],
            "dialogue_samples": ["Character: 'Line of dialogue'"]
            },
            {
            "scene_id": "s2",
            "label": "Next Scene Label",
            "summary": "Summary content...",
            "choice": "choice content...",
            "outcomes": ["Outcome A", "Outcome B"],
            "dialogue_samples": ["Character: 'Line'"]
            }
        ]
        },
        {
        "act_id": "a2",
        "scenes": [
            { "scene_id": "s1", "label": "Scene Label", "summary": "...", "choice": "...", "outcomes": [], "dialogue_samples": [] },
            { "scene_id": "s2", "label": "Scene Label", "summary": "...", "choice": "...", "outcomes": [], "dialogue_samples": [] },
            { "scene_id": "s3", "label": "Scene Label", "summary": "...", "choice": "...", "outcomes": [], "dialogue_samples": [] }
        ]
        },
        {
        "act_id": "a3",
        "scenes": [
            { "scene_id": "s1", "label": "Scene Label", "summary": "...", "choice": "...", "outcomes": [], "dialogue_samples": [] },
            { "scene_id": "s2", "label": "Scene Label", "summary": "...", "choice": "...", "outcomes": [], "dialogue_samples": [] }
        ]
        }
    ],
    "constraints": [
        "List of narrative constraints applied"
    ]
    }

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

def get_vector_store(collection_name_: str):

    if not collection_exists(collection_name_):
        raise ValueError(f"ERROR: {collection_name_} does not exist.")
    
    vector_db: QdrantVectorStore = QdrantVectorStore.from_existing_collection(
        url             = qdrant_client,
        collection_name = "karla_collection",
        embedding       = embedding_model
    )
    return vector_db


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

        # if step_data.step == StepType.OBSERVE:
        #     print(f"\n{step_data.step}: {step_data.content}\n")
        #     continue
        if step_data.step == StepType.OUTPUT:
            try:
                story_plan = json.loads(step_data.content)
                print("\n\n------STORY PLAN------\n")
                print(json.dumps(story_plan, indent=2))
            except Exception as err:
                print("\n\n------STORY PLAN------\n")
                print(f"\nRAW OUTPUT...\n{step_data.content}\nError: {err}")
            break
            # print(f"\nOUTPUT: {step_data.content}")
            # break

    except ValidationError as v_err:
        print(f"The LLM went off-script: {v_err.json()}")
        break

if failsafe >= WHILE_MAX:
    print("Reasoning recurrsion limit reached")
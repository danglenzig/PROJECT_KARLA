# PROJECT_KARLA/src/async/server.py

from fastapi import FastAPI, Query
from pathlib import Path



# PROJECT_KARLA/src/
SRC_ROOT = Path(__file__).parent.parent
# PROJECT_KARLA/src/async/rq_client
RQ_PATH = SRC_ROOT / "rq_client"
# PROJECT_KARLA/src/
NARRATIVE_AGENT_PATH = SRC_ROOT / "NARRATIVE_AGENT"

from NARRATIVE_AGENT import get_story_plan
from rq_client import rq_queue


app = FastAPI()

@app.get('/')
def root():
    "The FastAPI server is up"

@app.post('/story_plan/')
def story_plan(
    plan_input: str = Query(...,"The story plan input")
):
    job = rq_queue.enqueue(get_story_plan, plan_input)
    return {"status": "queued", "job_id": job.id}


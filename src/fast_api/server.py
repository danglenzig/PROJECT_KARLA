# PROJECT_KARLA/src/fast_api/server.py

from fastapi import FastAPI, Query
from pathlib import Path
import sys

# PROJECT_KARLA/src/
SRC_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(SRC_ROOT))

# PROJECT_KARLA/src/fast_api/
FAPI_PATH = Path(__file__).parent
sys.path.insert(0, str(FAPI_PATH))

# PROJECT_KARLA/src/fast_api/rq_client
RQ_PATH = FAPI_PATH / "rq_client"
sys.path.insert(0, str(RQ_PATH))

# PROJECT_KARLA/src/fast_api/workers
WKR_PATH = FAPI_PATH / "workers"
sys.path.insert(0, str(WKR_PATH))

# PROJECT_KARLA/src/
#NARRATIVE_AGENT_PATH = SRC_ROOT / "NARRATIVE_AGENT"
#sys.path.insert(0,str(NARRATIVE_AGENT_PATH))

#from NARRATIVE_AGENT import get_story_plan
from rq_client.rq_queue import queue
#from workers import story_plan
from fast_api.workers.worker import story_plan

app = FastAPI()

@app.get('/')
def root():
    return {"status": "The FastAPI server is up"}

@app.get('/get-foo/')
def get_foo(input: str = Query(..., description="Foo")):
    return {"status": "get bar"}

@app.post('/post-foo/')
def post_foo(input: str = Query(..., description="Foo")):
    return {"status": "post bar"}


@app.post('/story_plan/')
def get_story_plan(
    plan_input: str = Query(..., description="The story plan input")
):
    job = queue.enqueue(story_plan, plan_input)
    return {"status": "queued", "job_id": job.id}

@app.get('/job-status/')
def get_result(
    _job_id: str = Query(...,description="Job ID")
):
    job = queue.fetch_job(
        job_id=_job_id
    )
    result = job.return_value()
    return {"result": result}


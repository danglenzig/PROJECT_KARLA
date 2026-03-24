# PROJECT_KARLA/src/fast_api/main.py
from .server import app
import uvicorn # a simple web server


# from the project root, run:
# PYTHONPATH=src python3 -m fast_api.main

def main():
    uvicorn.run(app, port= 8000, host="localhost")

main()
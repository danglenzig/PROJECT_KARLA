# get_schema.py

import os
import json

def get_schema(schema_name: str):

    schema_dir = os.path.dirname(__file__)
    schema_path = os.path.join(schema_dir,schema_name)

    if os.path.exists(schema_path):
        with open(schema_path, 'r') as f:
            return json.dumps(json.load(f), indent=2)
    raise FileNotFoundError(f"Schema missing: {schema_path}")

import re
import os
from snowflake import SnowflakeGenerator
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Node name, Pod uid, Pod name are injected by kubernetes into the containers (configured in statefulset.yaml)
# Node name, Pod uid are optional just used for debugging
NODE_NAME = os.getenv('NODE_NAME')
POD_UID = os.getenv('POD_UID')

# Pod name is required, as it contains the machine ID
POD_NAME = os.getenv('POD_NAME', 'id-generator-1023')

# Custom Epoch for Snowflake, can be changed to any date
EPOCH = 1739526270  # 2025-02-14 15:13:00

# Extract the machine ID from the pod name
MACHINE_ID = int(re.search(r"\d+", POD_NAME).group())

# Initialize snowflkae id generator
integer_id_generator = SnowflakeGenerator(instance=MACHINE_ID, epoch=EPOCH)


app = FastAPI()

app.add_middleware(
    CORSMiddleware, # type: ignore
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health_check():
    return {
        "status": "OK",
        'machine_id': MACHINE_ID,
        'pod_uid': POD_UID,
        'node_name': NODE_NAME,
        'pod_name': POD_NAME,
        "language": "Python"
    }

@app.get("/generate-id")
def generate_id_integer():
    """Generate a Snowflake-based integer ID."""
    return {"id": next(integer_id_generator)}


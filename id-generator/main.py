
import re
import os
from snowflake import SnowflakeGenerator
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware


NODE_NAME = os.getenv('NODE_NAME')
POD_NAME = os.getenv('POD_NAME', 'id-generator-1023')
POD_UID = os.getenv('POD_UID')
EPOCH = 1739526270  # 2025-02-14 15:13:00

# Extract the machine ID from the pod name
MACHINE_ID = int(re.search(r"\d+", POD_NAME).group())
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
    return {"status": "OK", 'machine_id': MACHINE_ID, 'pod_uid': POD_UID}

@app.get("/generate-id")
def generate_id_integer():
    """Generate a Snowflake-based integer ID."""
    return {"id": next(integer_id_generator)}



import os
import time
import requests
from snowflake import SnowflakeGenerator
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import threading


COORDINATOR_URL = os.getenv("COORDINATOR_URL", "http://localhost:5000")

CURRENT_POD = os.getenv("POD_NAME", "id-generator-0")
POD_UID = os.getenv('POD_UID', '0')  # Unique identifier for the pod

MACHINE_ID = None   # This will be assigned by the coordinator
EPOCH = 1739526270  # 2025-02-14 15:13:00
MACHINE_ID_REQUEST_INTERVAL = 30  # Time in seconds between machine ID requests

heartbeat_failures = 0              # Number of consecutive heartbeat failures
MAX_HEARTBEAT_FAILURES = 5          # Max number of consecutive heartbeat failures before releasing ID
HEARTBEAT_INTERVAL = 10             # Time in seconds between heartbeats
integer_id_generator : None | SnowflakeGenerator  = None  # Snowflake generator (initialized after machine ID assignment)


def request_machine_id():
    """Request a machine ID from the coordinator."""
    global MACHINE_ID, integer_id_generator
    while MACHINE_ID is None:
        try:
            query_params = {"pod_uid": POD_UID}
            response = requests.get(f"{COORDINATOR_URL}/request_id/", params=query_params)
            data = response.json()
            if "machine_id" in data:
                MACHINE_ID = data["machine_id"]
                print(f"Assigned Machine ID: {MACHINE_ID}")
                integer_id_generator = SnowflakeGenerator(instance=MACHINE_ID, epoch=EPOCH)
                return
        except Exception as e:
            print(f"Error requesting machine ID: {e}")

        print(f"No machine ID available, retrying in {MACHINE_ID_REQUEST_INTERVAL} seconds...")
        time.sleep(MACHINE_ID_REQUEST_INTERVAL)  # Wait before retrying


def send_heartbeat():
    """Send periodic heartbeats to the coordinator."""
    global heartbeat_failures, MACHINE_ID, integer_id_generator

    while True:
        if MACHINE_ID is None:
            continue
        try:
            response = requests.get(f"{COORDINATOR_URL}/heartbeat/", params={"machine_id": MACHINE_ID, "pod_uid": POD_UID})
            data = response.json()
            if data.get("status") == "duplicate_detected":
                print("Duplicate ID detected! Releasing and re-requesting ID...")
                MACHINE_ID = None
                integer_id_generator = None
                request_machine_id()
            elif data.get("status") == 'not_assigned':
                print("Machine ID not assigned. Re-requesting...")
                MACHINE_ID = None
                integer_id_generator = None
                request_machine_id()
            heartbeat_failures = 0

            print(f"Heartbeat sent for Machine ID: {MACHINE_ID}")
        except Exception as e:
            print(f"Error sending heartbeat: {e}")
            heartbeat_failures += 1
            print(f"Heartbeat failure {heartbeat_failures}/{MAX_HEARTBEAT_FAILURES}: {e}")

            if heartbeat_failures >= MAX_HEARTBEAT_FAILURES:
                print(f"Max heartbeat failures reached ({MAX_HEARTBEAT_FAILURES}). Releasing and re-requesting ID...")
                MACHINE_ID = None
                integer_id_generator = None

                heartbeat_failures = 0
                request_machine_id()

        time.sleep(HEARTBEAT_INTERVAL)  # Send heartbeat every 10 seconds


async def startup_event():
    request_machine_id()

    threading.Thread(target=send_heartbeat, daemon=True).start()


@asynccontextmanager
async def lifespan(_: FastAPI):
    # Startup logic
    await startup_event()
    yield
    # Shutdown logic
    # await some_shutdown_function()



app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware, # type: ignore
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
def health_check():
    return {"status": "OK", 'machine_id': MACHINE_ID, 'pod_uid': POD_UID, 'coordinator_url': COORDINATOR_URL}

@app.get("/generate-id")
def generate_id_integer():
    """Generate a Snowflake-based integer ID."""
    if integer_id_generator is None:
        return {"error": "Machine ID not assigned yet."}
    else:
        return {"id": next(integer_id_generator)}


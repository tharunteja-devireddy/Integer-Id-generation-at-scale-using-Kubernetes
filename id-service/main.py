import os
import time
import uuid
import requests
from datetime import datetime, timedelta
from dotenv import load_dotenv
from snowflake import SnowflakeGenerator
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import threading

load_dotenv(dotenv_path="dev.env")

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

COORDINATOR_URL = os.getenv("COORDINATOR_URL", "http://coordinator:8000")

CURRENT_POD = os.getenv("POD_NAME", "id-generator-0")
pod_uid = os.getenv('POD_UID', '0')  # Unique identifier for the pod

MACHINE_ID = None  # This will be assigned by the coordinator
EPOCH = 1739526270  # 2025-02-14 15:13:00

heartbeat_failures = 0
integer_id_generator = None  # Snowflake generator (initialized after machine ID assignment)
MAX_HEARTBEAT_FAILURES = 5  # Max number of consecutive heartbeat failures before releasing ID

def request_machine_id():
    """Request a machine ID from the coordinator."""
    global MACHINE_ID, integer_id_generator
    while MACHINE_ID is None:
        try:
            response = requests.post(f"{COORDINATOR_URL}/request_id/", json={"pod_uid": pod_uid})
            data = response.json()
            if "machine_id" in data:
                MACHINE_ID = data["machine_id"]
                print(f"Assigned Machine ID: {MACHINE_ID}")
                integer_id_generator = SnowflakeGenerator(instance=MACHINE_ID, epoch=EPOCH)
                return
        except Exception as e:
            print(f"Error requesting machine ID: {e}")

        print("No machine ID available, retrying in 5 minutes...")
        time.sleep(300)  # Wait 5 minutes before retrying


def send_heartbeat():
    """Send periodic heartbeats to the coordinator."""
    global heartbeat_failures, MACHINE_ID, integer_id_generator

    while True:
        if MACHINE_ID is None:
            continue
        try:
            response = requests.post(f"{COORDINATOR_URL}/heartbeat/", json={"machine_id": MACHINE_ID, "pod_uid": pod_uid})
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

        time.sleep(10)  # Send heartbeat every 10 seconds


def release_machine_id():
    """Release the assigned machine ID before shutdown."""
    global MACHINE_ID, integer_id_generator
    if MACHINE_ID is not None:
        requests.post(f"{COORDINATOR_URL}/release_id/", json={"machine_id": MACHINE_ID})
        MACHINE_ID = None
        integer_id_generator = None


@app.on_event("startup")
async def startup_event():
    request_machine_id()

    threading.Thread(target=send_heartbeat, daemon=True).start()



@app.get("/generate-id")
def generate_id_integer():
    """Generate a Snowflake-based integer ID."""
    if integer_id_generator is None:
        return {"error": "Machine ID not assigned yet."}
    return {"id": next(integer_id_generator)}


@app.on_event("shutdown")
async def shutdown_event():
    release_machine_id()

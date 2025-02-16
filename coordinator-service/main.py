from fastapi import FastAPI, BackgroundTasks, HTTPException
import asyncio
import time
from bidict import bidict

app = FastAPI()

# Constants
ID_POOL = set(range(1024))  # Pool of available machine IDs
ASSIGNED_ID_POOL = set()  # IDs currently assigned
ID_MAP = bidict({})  # Bi-directional map of machine ID <-> Pod UID
HEARTBEAT_TRACKER = {}  # Tracks last heartbeat time per machine ID
HEARTBEAT_DELAY = 30  # Time in seconds before marking a machine ID as dead
SHELVE_TIME = 300  # 5 minutes before reassigning a dead ID
LOCK = asyncio.Lock()


async def cleanup_expired_ids():
    """Background task that reclaims IDs if no heartbeat is received."""
    while True:
        now = time.time()
        for machine_id, last_heartbeat in list(HEARTBEAT_TRACKER.items()):
            if now - last_heartbeat > HEARTBEAT_DELAY:  # Mark as dead after 30s
                print(f"Machine ID {machine_id} is inactive, shelving for 5 minutes.")
                del HEARTBEAT_TRACKER[machine_id]
                del ID_MAP[machine_id]
                ASSIGNED_ID_POOL.remove(machine_id)

                # Wait 5 minutes before putting the ID back into the pool
                await asyncio.sleep(SHELVE_TIME)
                ID_POOL.add(machine_id)
                print(f"Machine ID {machine_id} is now available for reassignment.")
        await asyncio.sleep(10)  # Check every 10 seconds


@app.on_event("startup")
async def startup_event():
    """Start background cleanup task on service startup."""
    asyncio.create_task(cleanup_expired_ids())


@app.post("/request_id/")
async def request_machine_id(pod_uid: str):
    """Assign a new machine ID to a pod."""
    async with LOCK:
        if pod_uid in ID_MAP.inverse:
            return {"machine_id": ID_MAP.inverse[pod_uid], "status": "ID already assigned"}

        if ID_POOL:
            machine_id = ID_POOL.pop()
            ID_MAP[machine_id] = pod_uid
            ASSIGNED_ID_POOL.add(machine_id)
            HEARTBEAT_TRACKER[machine_id] = time.time()
            return {"machine_id": machine_id, "status": "ID assigned"}

    return {"status": "No ID available, retry in 5 minutes"}


@app.post("/heartbeat/")
async def heartbeat(machine_id: int, pod_uid: str):
    """Receive heartbeat from ID services."""
    if machine_id not in ASSIGNED_ID_POOL:
        return {"status": "not_assigned"}

    HEARTBEAT_TRACKER[machine_id] = time.time()

    # Check for duplicate ID usage
    assigned_pod_uid = ID_MAP[machine_id]
    if assigned_pod_uid != pod_uid:
        print(f"Duplicate machine ID detected for {machine_id}! Stopping {pod_uid}...")
        return {"status": "duplicate_detected"}

    return {"status": "alive"}


@app.post("/release_id/")
async def release_machine_id(machine_id: int):
    """Manually release a machine ID."""
    async with LOCK:
        # These checks are needed as we should release an id in the event of duplicate detection and un assigned use
        # and we dont know exactly in objects like ID_MAP and ASSIGNED_ID_POOL if the id is present or not
        if machine_id in HEARTBEAT_TRACKER:
            del HEARTBEAT_TRACKER[machine_id]
        if machine_id in ID_MAP:
            del ID_MAP[machine_id]
        if machine_id in ASSIGNED_ID_POOL:
            ASSIGNED_ID_POOL.remove(machine_id)
        if machine_id not in ID_POOL:
            ID_POOL.add(machine_id)

    raise HTTPException(status_code=404, detail="Machine ID not found")


async def shelve_id(machine_id: int):
    """Shelve an ID before making it available again."""
    await asyncio.sleep(SHELVE_TIME)
    ID_POOL.add(machine_id)
    print(f"Machine ID {machine_id} is available again.")


@app.get("/health/")
async def health():
    """Health check endpoint."""
    return {"status": "OK"}


import time
import asyncio
from bidict import bidict
from fastapi import FastAPI, HTTPException
from contextlib import asynccontextmanager



# ID management Constants
ID_POOL = set(range(1024))  # Pool of available machine IDs
ASSIGNED_ID_POOL = set()  # IDs currently assigned
ID_MAP = bidict({})  # Bidirectional map of machine ID <-> Pod UID

# Heartbeat tracking Constants
HEARTBEAT_TRACKER = {}            # Tracks last heartbeat time per machine ID
HEARTBEAT_DELAY = 30              # Time in seconds before marking a machine ID as dead
SHELVE_TIME = 120                 # 5 minutes before reassigning a dead ID
EXPIRED_ID_CLEANUP_INTERVAL = 20  # Time in seconds between cleanup checks


LOCK = asyncio.Lock()


async def cleanup_expired_ids():
    """Background task that reclaims IDs if no heartbeat is received."""
    while True:
        now = time.time()
        for machine_id, last_heartbeat in list(HEARTBEAT_TRACKER.items()):
            if now - last_heartbeat > HEARTBEAT_DELAY:
                print(f"Machine ID {machine_id} is inactive, shelving for {SHELVE_TIME} seconds.")
                del HEARTBEAT_TRACKER[machine_id]
                del ID_MAP[machine_id]
                ASSIGNED_ID_POOL.remove(machine_id)

                # Wait 5 minutes before putting the ID back into the pool
                await asyncio.sleep(SHELVE_TIME)
                ID_POOL.add(machine_id)
                print(f"Machine ID {machine_id} is now available for reassignment.")

        await asyncio.sleep(EXPIRED_ID_CLEANUP_INTERVAL)


async def shelve_id(machine_id: int):
    """Shelve an ID before making it available again."""
    await asyncio.sleep(SHELVE_TIME)
    ID_POOL.add(machine_id)
    print(f"Machine ID {machine_id} is available again.")


async def startup_event():
    """Start background cleanup task on service startup."""
    asyncio.create_task(cleanup_expired_ids())


@asynccontextmanager
async def lifespan(_: FastAPI):
    # Startup logic
    await startup_event()
    yield
    # Shutdown logic
    # await some_shutdown_function()



app = FastAPI(lifespan=lifespan)

@app.get("/health/")
async def health():
    """Health check endpoint."""
    return {"status": "OK"}



@app.get("/request_id/")
async def request_machine_id(pod_uid: str):
    """Assign a new machine ID to a pod."""
    async with LOCK:
        if pod_uid in ID_MAP.inverse:
            print(f"Pod UID {pod_uid} already has a machine ID assigned.")
            return {"machine_id": ID_MAP.inverse[pod_uid], "status": "ID already assigned"}

        if ID_POOL:
            machine_id = ID_POOL.pop()
            ID_MAP[machine_id] = pod_uid
            ASSIGNED_ID_POOL.add(machine_id)
            HEARTBEAT_TRACKER[machine_id] = time.time()

            print(f"Machine ID {machine_id} assigned to Pod UID {pod_uid}")
            return {"machine_id": machine_id, "status": "ID assigned"}

        else:
            print("ID Pool is empty. No IDs available.")
            return {"status": "No ID available"}


@app.get("/heartbeat/")
async def heartbeat(machine_id: int, pod_uid: str):
    """Receive heartbeat from ID services."""
    if machine_id not in ASSIGNED_ID_POOL:
        print(f"Machine ID {machine_id} not assigned. Ignoring heartbeat...")
        return {"status": "not_assigned"}

    HEARTBEAT_TRACKER[machine_id] = time.time()

    # Check for duplicate ID usage
    assigned_pod_uid = ID_MAP[machine_id]
    if assigned_pod_uid != pod_uid:
        print(f"Duplicate machine ID detected for {machine_id}! Stopping {pod_uid}...")
        return {"status": "duplicate_detected"}

    print(f"Heartbeat received for Machine ID: {machine_id}")
    return {"status": "alive"}


@app.post("/release_id/")
async def release_machine_id(machine_id: int):
    """Manually release a machine ID."""
    async with LOCK:
        # These checks are needed as we should release an id in the event of duplicate detection and un assigned use
        # , and we don't know exactly in objects like ID_MAP and ASSIGNED_ID_POOL if the id is present or not
        if machine_id in HEARTBEAT_TRACKER:
            del HEARTBEAT_TRACKER[machine_id]
        if machine_id in ID_MAP:
            del ID_MAP[machine_id]
        if machine_id in ASSIGNED_ID_POOL:
            ASSIGNED_ID_POOL.remove(machine_id)
        if machine_id not in ID_POOL:
            ID_POOL.add(machine_id)

    raise HTTPException(status_code=404, detail="Machine ID not found")


@app.get("/status/")
async def status():
    """Get the current status of the ID service."""
    return {
        "available_ids": len(ID_POOL),
        "assigned_ids": list(ASSIGNED_ID_POOL),
        "id_map": ID_MAP,
        "heartbeat_tracker": HEARTBEAT_TRACKER,
    }

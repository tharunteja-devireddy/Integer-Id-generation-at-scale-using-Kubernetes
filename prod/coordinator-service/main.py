
import os
import time
import uuid
import asyncio
import redis.asyncio as redis
from fastapi import FastAPI, Depends
from contextlib import asynccontextmanager

# Redis connection settings
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = os.getenv("REDIS_PORT", 6379)

async def get_redis():
    return redis.from_url(f"redis://{REDIS_HOST}:{REDIS_PORT}", decode_responses=True)

# Constants
HEARTBEAT_DELAY = 30              # Time in seconds before marking a machine ID as dead
SHELVE_TIME = 120                 # 2 minutes before reassigning a dead ID
EXPIRED_ID_CLEANUP_INTERVAL = 20  # Time in seconds between cleanup checks
LOCK_TIMEOUT = 5                   # Maximum time the lock is held to prevent deadlocks
LOCK_PREFIX = "lock:"              # Prefix for lock keys in Redis

async def acquire_lock(redis, lock_name):
    """Try to acquire a distributed lock with a unique value (UUID)."""
    lock_key = LOCK_PREFIX + lock_name
    lock_value = str(uuid.uuid4())  # Generate a unique identifier

    while True:
        if await redis.set(lock_key, lock_value, ex=LOCK_TIMEOUT, nx=True):  # SET if not exists
            return lock_value  # Return lock value to verify later
        await asyncio.sleep(0.1)  # Retry after a short delay

async def release_lock(redis, lock_name, lock_value):
    """Release the distributed lock only if the caller holds it."""
    lock_key = LOCK_PREFIX + lock_name
    lua_script = """
    if redis.call("get", KEYS[1]) == ARGV[1] then
        return redis.call("del", KEYS[1])
    else
        return 0
    end
    """
    await redis.eval(lua_script, 1, lock_key, lock_value)  # Ensure atomicity

async def cleanup_expired_ids(redis):
    """Background task that checks for expired machine IDs and reclaims them."""
    while True:
        now = time.time()
        expired_ids = []
        async for machine_id, last_heartbeat in redis.hscan_iter("HEARTBEAT_TRACKER"):
            last_heartbeat = float(last_heartbeat)
            if now - last_heartbeat > HEARTBEAT_DELAY:
                expired_ids.append(machine_id)

        for machine_id in expired_ids:
            lock_value = await acquire_lock(redis, f"cleanup:{machine_id}")
            if lock_value:
                try:
                    print(f"Machine ID {machine_id} is inactive, shelving for {SHELVE_TIME} seconds.")
                    await redis.hdel("HEARTBEAT_TRACKER", machine_id)
                    await redis.hdel("ID_MAP", machine_id)
                    await redis.srem("ASSIGNED_ID_POOL", machine_id)
                    asyncio.create_task(shelve_id(redis, machine_id))
                finally:
                    await release_lock(redis, f"cleanup:{machine_id}", lock_value)

        await asyncio.sleep(EXPIRED_ID_CLEANUP_INTERVAL)

async def shelve_id(redis, machine_id):
    """Re-add a machine ID to the available pool after a delay."""
    await asyncio.sleep(SHELVE_TIME)
    await redis.sadd("ID_POOL", machine_id)
    print(f"Machine ID {machine_id} is available again.")


async def startup_event():
    """Start the background task for cleaning expired IDs."""
    redis = await get_redis()
    asyncio.create_task(cleanup_expired_ids(redis))


@asynccontextmanager
async def lifespan(_: FastAPI):
    # Startup logic
    await startup_event()
    yield



app = FastAPI(lifespan=lifespan)



@app.get("/request_id/")
async def request_machine_id(pod_uid: str, redis=Depends(get_redis)):
    """Assign a new machine ID to a pod."""
    lock_value = await acquire_lock(redis, "id_request")  # Acquire lock with UUID
    if not lock_value:
        return {"status": "Lock acquisition failed, try again"}

    try:
        existing_id = await redis.hget("ID_MAP", pod_uid)
        if existing_id:
            return {"machine_id": existing_id, "status": "ID already assigned"}

        machine_id = await redis.spop("ID_POOL")
        if machine_id:
            await redis.hset("ID_MAP", machine_id, pod_uid)
            await redis.sadd("ASSIGNED_ID_POOL", machine_id)
            await redis.hset("HEARTBEAT_TRACKER", machine_id, time.time())

            return {"machine_id": machine_id, "status": "ID assigned"}

        return {"status": "No ID available"}
    finally:
        await release_lock(redis, "id_request", lock_value)  # Release lock safely

@app.get("/heartbeat/")
async def heartbeat(machine_id: str, pod_uid: str, redis=Depends(get_redis)):
    """Receive heartbeat from ID services."""
    assigned_pod_uid = await redis.hget("ID_MAP", machine_id)
    if not assigned_pod_uid:
        return {"status": "not_assigned"}

    if assigned_pod_uid != pod_uid:
        return {"status": "duplicate_detected"}

    await redis.hset("HEARTBEAT_TRACKER", machine_id, time.time())
    return {"status": "alive"}

@app.post("/release_id/")
async def release_machine_id(machine_id: str, redis=Depends(get_redis)):
    """Manually release a machine ID safely with proper locking."""
    lock_value = await acquire_lock(redis, f"release:{machine_id}")
    if not lock_value:
        return {"status": "Lock acquisition failed, try again"}

    try:
        await redis.hdel("HEARTBEAT_TRACKER", machine_id)
        await redis.hdel("ID_MAP", machine_id)
        await redis.srem("ASSIGNED_ID_POOL", machine_id)
        await redis.sadd("ID_POOL", machine_id)

        return {"status": "ID released"}
    finally:
        await release_lock(redis, f"release:{machine_id}", lock_value)  # Safe release

@app.get("/status/")
async def status(redis=Depends(get_redis)):
    """Get the current status of the ID service."""
    available_ids = await redis.scard("ID_POOL")
    assigned_ids = await redis.smembers("ASSIGNED_ID_POOL")
    id_map = await redis.hgetall("ID_MAP")
    heartbeat_tracker = await redis.hgetall("HEARTBEAT_TRACKER")

    return {
        "available_ids": available_ids,
        "assigned_ids": list(assigned_ids),
        "id_map": id_map,
        "heartbeat_tracker": heartbeat_tracker,
    }

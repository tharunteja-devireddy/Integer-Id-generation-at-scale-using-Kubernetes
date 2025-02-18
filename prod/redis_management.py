import os
import asyncio
import redis.asyncio as redis

# Redis connection settings
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))


# Initialize Redis client
async def get_redis():
    return redis.from_url(f"redis://{REDIS_HOST}:{REDIS_PORT}", decode_responses=True)


async def list_redis_data():
    """Fetch and print all keys and their values in Redis."""
    redis_client = await get_redis()
    keys = await redis_client.keys("*")  # Get all keys
    if not keys:
        print("Redis is empty.")
        return {}

    data = {}
    for key in keys:
        key_type = await redis_client.type(key)
        if key_type == "string":
            data[key] = await redis_client.get(key)
        elif key_type == "hash":
            data[key] = await redis_client.hgetall(key)
        elif key_type == "set":
            data[key] = await redis_client.smembers(key)
        elif key_type == "list":
            data[key] = await redis_client.lrange(key, 0, -1)
        elif key_type == "zset":
            data[key] = await redis_client.zrange(key, 0, -1, withscores=True)

    print("🔍 Redis Data:", data)
    return data


async def insert_id_map(machine_id: str, pod_uid: str):
    """Insert a Machine ID <-> Pod UID mapping into Redis."""
    redis_client = await get_redis()
    existing = await redis_client.hget("ID_MAP", machine_id)

    if existing:
        print(f"⚠️ Machine ID {machine_id} is already assigned to {existing}.")
        return {"status": "ID already assigned", "machine_id": machine_id, "pod_uid": existing}

    await redis_client.hset("ID_MAP", machine_id, pod_uid)
    print(f"✅ Assigned Machine ID {machine_id} to Pod UID {pod_uid}")
    return {"status": "ID assigned", "machine_id": machine_id, "pod_uid": pod_uid}



async def get_id_map():
    """Retrieve all Machine ID <-> Pod UID mappings from Redis."""
    redis_client = await get_redis()
    id_map = await redis_client.hgetall("ID_MAP")
    print("📜 ID_MAP:", id_map)
    return id_map



async def initialize_id_pool(machine_ids: list):
    """Insert multiple Machine IDs into `ID_POOL`."""
    redis_client = await get_redis()
    if not machine_ids:
        print("⚠️ No IDs provided to insert into ID_POOL.")
        return {"status": "No IDs provided"}

    await redis_client.sadd("ID_POOL", *machine_ids)  # Add multiple IDs
    print(f"✅ Inserted {len(machine_ids)} IDs into ID_POOL: {machine_ids}")
    return {"status": "IDs inserted", "count": len(machine_ids)}


async def list_available_ids():
    """List all available Machine IDs in the ID_POOL."""
    redis_client = await get_redis()
    id_pool = await redis_client.smembers("ID_POOL")
    print("🔢 ID_POOL:", id_pool)
    return id_pool


async def list_assigned_ids():
    """List all assigned Machine IDs."""
    redis_client = await get_redis()
    assigned_ids = await redis_client.smembers("ASSIGNED_ID_POOL")
    print("🔢 ASSIGNED_ID_POOL:", assigned_ids)
    return assigned_ids


async def delete_all_keys():
    """Delete all keys in Redis."""
    redis_client = await get_redis()
    keys = await redis_client.keys("*")
    if not keys:
        print("⚠️ No keys found in Redis.")
        return {"status": "No keys found"}

    await redis_client.delete(*keys)
    print("🗑 Deleted all keys from Redis.")
    return {"status": "All keys deleted"}




### 🏃‍♂️ Run as a standalone script ###
if __name__ == "__main__":

    # Delete all keys in Redis
    # delete_all_keys()

    # Insert multiple IDs
    initialize_id_pool(["1", "2", "3", "4", "5"])

    # List available IDs
    list_available_ids()

    # List assigned IDs
    list_assigned_ids()

    # List all Redis data
    list_redis_data()


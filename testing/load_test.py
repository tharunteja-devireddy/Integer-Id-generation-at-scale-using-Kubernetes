import time
import requests
import aiosqlite
import asyncio
from multiprocessing import Pool, Manager

ID_SERVICE_URL = 'http://localhost:8000' # on local
# ID_SERVICE_URL = 'http://localhost:80'   # on kubernetes

async def async_store_worker(queue):
    """Worker that writes IDs from the queue to SQLite asynchronously."""
    async with aiosqlite.connect("testing/generated_ids.db") as db:
        await db.execute("PRAGMA journal_mode=WAL")  # Enable WAL mode
        while True:
            id_value = await queue.get()
            if id_value is None:  # Stop condition
                break
            try:
                await db.execute("INSERT INTO ids (id) VALUES (?)", (id_value,))
                await db.commit()
            except aiosqlite.IntegrityError:
                pass  # Ignore duplicates
            queue.task_done()

async def async_truncate_table():
    """Asynchronously clear the database before running a new test."""
    async with aiosqlite.connect("testing/generated_ids.db") as db:
        await db.execute("DELETE FROM ids")
        await db.commit()

async def async_count_records():
    """Asynchronously count total records in the database."""
    async with aiosqlite.connect("testing/generated_ids.db") as db:
        async with db.execute("SELECT COUNT(*) FROM ids") as cursor:
            result = await cursor.fetchone()
            return result[0] if result else 0

async def async_count_ids():
    """Asynchronously count unique IDs in the database."""
    async with aiosqlite.connect("testing/generated_ids.db") as db:
        async with db.execute("SELECT COUNT(DISTINCT id) FROM ids") as cursor:
            result = await cursor.fetchone()
            return result[0] if result else 0

def generate_id(_):
    """Fetch an ID from the external service."""
    response = requests.get(f'{ID_SERVICE_URL}/generate-id')
    return response.json().get('id')

async def store_ids_async(ids):
    """Asynchronously store generated IDs using a queue."""
    queue = asyncio.Queue()

    # Start a single writer worker
    writer_task = asyncio.create_task(async_store_worker(queue))

    # Add IDs to the queue
    for id_value in ids:
        await queue.put(id_value)

    # Signal the writer to stop
    await queue.put(None)
    await writer_task  # Wait for the writer to finish

def load_test(num_requests=100, num_workers=4):
    """Run the load test with multiprocessing for ID generation and async for storing."""

    # Clear database asynchronously
    asyncio.run(async_truncate_table())

    start_time = time.time()

    with Pool(processes=num_workers) as pool:
        generated_ids = pool.map(generate_id, range(num_requests))

    end_time = time.time()
    exec_time = end_time - start_time

    # Store IDs asynchronously using an async queue
    asyncio.run(store_ids_async(generated_ids))

    # Fetch counts asynchronously
    generated_records = asyncio.run(async_count_records())
    unique_ids = asyncio.run(async_count_ids())

    if unique_ids != generated_records:
        print("⚠️ Duplicate IDs found in the database.")
    else:
        print(f"✅ Load test completed in {exec_time:.2f} seconds.")
        print(f"📊 Total records in the database    : {generated_records}")
        print(f"📊 Total unique IDs in the database : {unique_ids}")
        print(f"🚀 Throughput: {num_requests / exec_time:.2f} requests/sec")


def load_test_no_storage(num_requests=100, num_workers=8):
    """Run the load test with multiprocessing for ID generation only."""

    start_time = time.time()

    with Pool(processes=num_workers) as pool:
        generated_ids = pool.map(generate_id, range(num_requests))

    end_time = time.time()
    exec_time = end_time - start_time

    print(f"✅ Load test completed in {exec_time:.2f} seconds.")
    print(f"🚀 Throughput: {num_requests / exec_time:.2f} requests/sec")





# Example: Run the load test using only 4 CPU cores
load_test(num_requests=50_000, num_workers=12)
# load_test_no_storage(num_requests=100_000, num_workers=12)

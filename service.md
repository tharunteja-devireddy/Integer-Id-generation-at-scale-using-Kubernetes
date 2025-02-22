
  This documentation describes the **Coordinator Service** and **ID Generation Service**, their interactions, failure handling, and recovery mechanisms.  
  
## **Coordinator Service**  
The **Coordinator Service** is responsible for managing machine IDs, tracking heartbeats, and reclaiming IDs from inactive pods.    
  
### **Startup Behavior**  
- Initializes a **pool of 1024 unique machine IDs** (`ID_POOL`).  
- Maintains a **two-way mapping (`ID_MAP`)** between assigned IDs and unique pod identifiers (`POD_UID`).
- Tracks assigned IDs in **`ASSIGNED_ID_POOL`**.  
- Monitors heartbeats via **`HEARTBEAT_TRACKER`**, a map that maintains machine IDs and records the last heartbeat time for each corresponding device.
  
### **Machine ID Assignment**  
When a pod requests a machine ID:  
1. If a machine ID is already assigned to the requesting pod (`POD_UID`), return the existing assignment.  
2. If a machine ID is available in the **`ID_POOL`**, assign it, track it in **`ASSIGNED_ID_POOL`**, and update the heartbeat tracker.  
3. If no machine ID is available, the Coordinator Service does not return one. In this case, the ID Service enters a loop, retrying every `MACHINE_ID_REQUEST_INTERVAL` (default: 30s) until a machine ID becomes available. 
### **Heartbeat Monitoring**  
- Each `id service` pod sends a heartbeat **every `HEARTBEAT_INTERVAL` seconds** (default: 10s), prompting the Coordinator Service to update the heartbeat in `HEARTBEAT_TRACKER`.
- If no heartbeat is received within **`HEARTBEAT_DELAY` seconds (30s default)**, the pod is considered **dead**.  
- The associated **machine ID is removed from assigned IDs and temporarily shelved** for `SHELVE_TIME` (default: 120s) before it can be reassigned to the available ID pool.

## **ID Generation Service**  
The main role of the **ID Service** is to generate unique integer IDs. This can be achieved using the **Snowflake algorithm**, as demonstrated in the following code snippet:

```python
# pip install snowflake-id
from snowflake import SnowflakeGenerator, Snowflake  

# Machine ID uniquely identifies the machine generating the ID (must be between 0-1023)
MACHINE_ID = 23  

# Epoch time marks the start of ID generation (IDs will be unique for the next ~138 years)
EPOCH = 1739526270  # 2025-02-14 15:13:00  

# Create a Snowflake ID generator instance
integer_id_generator = SnowflakeGenerator(
    instance=MACHINE_ID,  
    epoch=EPOCH,  
)

# Generate a unique integer ID
integer_id = next(integer_id_generator)
```

**Preventing ID Collisions**

While this approach ensures efficient ID generation, **collisions can occur** if multiple instances use the same `MACHINE_ID`. Since the Snowflake algorithm relies on machine IDs to differentiate generators, running multiple instances with the same `MACHINE_ID` may lead to **duplicate IDs** being produced.

To prevent such conflicts, each instance is assigned a unique **machine ID (0-1023)**. The **Coordinator Service** is responsible for managing these assignments, ensuring that no two active instances share the same machine ID.

**Mapping Instances to Machine ID**
In order achieve this he **Coordinator Service** must uniquely identify each instance (pod or container). Since our architecture ensures only **one container per pod**, this can be achieved using:

- **`POD_UID`**: A unique identifier injected into the container by Kubernetes, allowing the **Coordinator Service** to track each instance reliably.
- **UUID**: In non-Kubernetes environments (e.g., local development), a randomly generated **UUID** can be used instead of `POD_UID` to uniquely identify the instance.

Regardless of the environment, this approach ensures that each **ID Service** instance receives a distinct **machine ID (0-1023)**, preventing duplicate ID generation and ensuring system consistency.

**Basic Working**
The **ID Generation Service** requests and maintains a unique machine ID from the **Coordinator Service**, using it to generate unique integer identifiers via the **Snowflake algorithm**.
### **Startup Behavior**  
- Requests a **machine ID from the Coordinator** (`COORDINATOR_URL`).  
- If an ID is assigned:  
  1. **Stores the machine ID**.  
  2. **Initializes the Snowflake ID generator (`integer_id_generator`)**.  
  3. Begins serving requests.  
- If an ID is not assigned, the service enters a loop, periodically requesting the Coordinator Service every **`MACHINE_ID_REQUEST_INTERVAL` (default: 30s)** to assign a machine ID.

### **ID Generation**  
- When requested, generate  a new **Snowflake integer ID** (`/generate-id-integer`).  
  
### **Heartbeat Mechanism**  
- Sends a **heartbeat every `HEARTBEAT_INTERVAL` (10s)**.  
- If the Coordinator does not receive a heartbeat for `HEARTBEAT_DELAY` (30s), the **machine ID is shelved for reuse**.  
- If the **ID Service** fails to send heartbeats **`MAX_HEARTBEAT_FAILURES(default 5)`** consecutively, it releases its machine ID and stops serving requests. This prevents ID duplication conflicts, as the **Coordinator Service** marks the instance as dead and reassigns the machine ID to a new instance.

## **Failure Handling**

1. **Coordinator Service Loses State or Restarts**
    
    - When the **Coordinator Service** restarts, it loses track of assigned machine IDs.
    - Normally, this isn’t a major issue—when existing **ID Service** instances (that already have assigned machine IDs) send their heartbeats, the coordinator detects the IDs as "unassigned" and requests the services to release and re-request a new ID.
    - **However**, a problem arises if a new or existing pod requests a machine ID **before** these heartbeats are processed. In this case, the coordinator might mistakenly assign the **same** machine ID to multiple pods, leading to conflicts.
    - **Possible Solution:** Persist the coordinator’s state in a durable store (e.g., Redis or disk-based storage) so it can restore assigned IDs after a restart.
2. **Network Partition Between Coordinator and an ID Service**
    
    - If an **ID Service** instance fails to send heartbeats due to a network partition, the coordinator assumes the service is dead and **shelves** the machine ID, preventing immediate reassignment.
    - Even if the **ID Service** is still running, it cannot communicate with the coordinator. If the partition persists, the service will eventually recognize the connectivity loss and, upon reconnecting, will either release or re-request a new machine ID.
3. **Network Partition Followed by Recovery**
    
    - If the coordinator has already **shelved** the machine ID due to missed heartbeats, and the **ID Service** later recovers and reconnects, it is treated as a new instance.
    - The coordinator will then assign it a fresh machine ID from the available pool, ensuring no conflict with the previously shelved ID.


**Important Note**
Under normal conditions, two different pods **cannot** receive the same machine ID. The only potential scenario for duplication occurs during network or service failures, but these are managed by the system as described above.

## **Duplicate Machine ID Detection**

Under normal operation, the **Coordinator Service** cannot assign duplicate machine IDs, as the values are thread locked. Even in cases of network failures, restarts, or shutdowns, the system is designed to prevent duplication. However, additional **deduplication mechanisms** are in place to ensure quick recovery in rare, extraordinary cases.

- If the **Coordinator Service** detects that a **previously assigned machine ID** is being used by a different `POD_UID`, it flags the ID as **unassigned usage**.
- In response, `id service` takes the following actions:
    1. **Releases its current machine ID**.
    2. **Resets its Snowflake generator** to prevent ID conflicts.
    3. **Requests a new machine ID** and enters **wait mode** until a new ID is assigned.




## **Constants Used**  

**Coordinator-Side Constants**  

| **Variable** | **Description** | **Default Value** |  
|-------------|----------------|------------------|  
| `ID_POOL` | Set of 1024 available machine IDs | `{0-1023}` |  
| `ASSIGNED_ID_POOL` | Machine IDs currently assigned | `set()` |  
| `ID_MAP` | Bidirectional map of `machine_id ↔ POD_UID` | `bidict({})` |  
| `HEARTBEAT_TRACKER` | Tracks last heartbeat time for each machine ID | `{}` |  
| `HEARTBEAT_DELAY` | Time before marking a pod as dead | `30s` |  
| `SHELVE_TIME` | Time before a shelved ID is reassigned | `120s` |  
| `EXPIRED_ID_CLEANUP_INTERVAL` | Interval between expired ID cleanups | `20s` |  
  
 **ID Service (`idgen`) Constants**  
 
| **Variable**                  | **Description**                                                   | **Default Value**           |     |
| ----------------------------- | ----------------------------------------------------------------- | --------------------------- | --- |
| `COORDINATOR_URL`             | URL of the Coordinator service                                    | `"http://localhost:5000"`   |     |
| `CURRENT_POD`                 | Pod name of the `idgen` instance                                  | `"id-generator-0"`          |     |
| `POD_UID`                     | Unique identifier for the pod                                     | `"0"`                       |     |
| `MACHINE_ID`                  | Assigned machine ID                                               | `None`                      |     |
| `EPOCH`                       | Epoch timestamp for Snowflake generator                           | `1739526270` (Feb 14, 2025) |     |
| `MACHINE_ID_REQUEST_INTERVAL` | Time between machine ID requests                                  | `30s`                       |     |
| `HEARTBEAT_INTERVAL`          | Time between heartbeats                                           | `10s`                       |     |
| `heartbeat_failures`          | Consecutive heartbeat failures                                    | `0`                         |     |
| `MAX_HEARTBEAT_FAILURES`      | Maximum consecutive heartbeat failures before re-requesting an ID | `5`                         |     |
  
---  
  

## **Conclusion**

This document provides a comprehensive overview of the **Coordinator Service** and **ID Generation Service**, detailing their interactions, startup behaviors, failure handling, and recovery mechanisms.

The **Coordinator Service** efficiently manages machine ID assignments, tracks active instances via heartbeats, and ensures proper ID reclamation when services go offline. The **ID Generation Service**, in turn, requests and maintains unique machine IDs, leveraging the **Snowflake algorithm** to generate unique integer IDs.

Robust failure-handling strategies are in place to mitigate issues arising from network failures, service restarts, and ID duplication risks. These include heartbeat-based monitoring, ID shelving, and deduplication mechanisms to ensure that no two instances receive the same machine ID under normal operation.

With these safeguards in place, the system maintains **high reliability**, **fault tolerance**, and **consistent ID generation**, even under exceptional circumstances.
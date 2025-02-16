### **Coordinator and ID Generation Service Documentation**

This documentation describes the **Coordinator Service** and **ID Generation Service**, their interactions, failure handling, and recovery mechanisms.

---

## **Coordinator Service**
The **Coordinator Service** is responsible for managing machine IDs, tracking heartbeats, and reclaiming IDs from inactive pods.  

### **Startup Behavior**
- Initializes a **pool of 1024 unique machine IDs** (`ID_POOL`).
- Maintains a **bidirectional mapping (`ID_MAP`)** between assigned IDs and pod unique identifiers (`POD_UID`).
- Tracks assigned IDs in **`ASSIGNED_ID_POOL`**.
- Monitors heartbeats via **`HEARTBEAT_TRACKER`**.

### **Machine ID Assignment**
When a pod requests a machine ID:
1. If a machine ID is already assigned to the requesting pod (`POD_UID`), return the existing assignment.
2. If a machine ID is available in the **`ID_POOL`**, assign it, track it in **`ASSIGNED_ID_POOL`**, and update the heartbeat tracker.
3. If no machine ID is available, **trigger wait mode** where the ID Generation Service (`idgen`) retries every `MACHINE_ID_REQUEST_INTERVAL` (default: 30s).

### **Heartbeat Monitoring**
- Each `idgen` pod sends a heartbeat **every `HEARTBEAT_INTERVAL` seconds** (default: 10s).
- If no heartbeat is received within **`HEARTBEAT_DELAY` seconds (30s default)**, the pod is considered **dead**.
- The associated **machine ID is shelved** for `SHELVE_TIME` (default: 120s) before it can be reassigned.

### **Handling Network Failures & Recovery**
- If the **network between Coordinator and ID service breaks**, the Coordinator will:
  1. Wait **30 seconds** for a heartbeat.
  2. If the pod does not recover, **shelve the machine ID for `SHELVE_TIME` (5 minutes)** before reuse.
- If the network restores before `idgen` detects the failure:
  - `idgen` will **detect the missing ID in the Coordinator** and **release the machine ID**, resetting itself.

### **Duplicate ID Detection**
- If the Coordinator detects a **previously assigned machine ID being used by a different `POD_UID`**, it marks the ID as **unassigned usage**.
- `idgen` will then:
  1. **Release its machine ID**.
  2. **Reset its Snowflake generator**.
  3. **Request a new machine ID** and enter wait mode until an ID is reassigned.

### **Coordinator Failure Handling**
- If the Coordinator crashes:
  - The **ID map (`ID_MAP`) is lost**.
  - **Existing `idgen` services continue to work** until they **fail to send `MAX_HEARTBEAT_FAILURES` (5) consecutive heartbeats**.
  - After `MAX_HEARTBEAT_FAILURES`, each `idgen` will **release its machine ID**, reset the Snowflake generator, and enter wait mode until the Coordinator recovers.

---

## **ID Generation Service (`idgen`)**
The **ID Generation Service** requests and maintains a unique machine ID from the Coordinator. It uses this ID to generate unique integer identifiers via the **Snowflake algorithm**.

### **Startup Behavior**
- Requests a **machine ID from the Coordinator** (`COORDINATOR_URL`).
- If an ID is assigned:
  1. **Caches the machine ID**.
  2. **Initializes the Snowflake ID generator (`integer_id_generator`)**.
  3. Begins serving requests.

### **Machine ID Request & Wait Mode**
- If no machine ID is available, `idgen` will:
  1. Wait **`MACHINE_ID_REQUEST_INTERVAL` (default: 30s)**.
  2. Retry the request **until an ID is assigned**.

### **ID Usage Rules**
- **Do not use an ID for more than 4 minutes**.
- **Do not remove the ID from the pool until 5 minutes after marking it as inactive**.

### **ID Generation**
- When requested, generate a new **UUID-based ID** (`/generate-id`).
- Generate a new **Snowflake integer ID** (`/generate-id-integer`).

### **Heartbeat Mechanism**
- Sends a **heartbeat every `HEARTBEAT_INTERVAL` (10s)**.
- If the Coordinator does not receive a heartbeat for `HEARTBEAT_DELAY` (30s), the **machine ID is shelved for reuse**.

### **Handling Network Failures**
If the network breaks:
1. The **Coordinator waits 30s before shelving the machine ID**.
2. Meanwhile, `idgen` will keep operating and serving requests.
3. If `idgen` fails to send **`MAX_HEARTBEAT_FAILURES` (default: 5) consecutive heartbeats**, it will:
   - **Release the machine ID**.
   - **Reset the Snowflake generator**.
   - **Enter wait mode until the network resolves and a new machine ID is assigned**.

### **Duplicate ID Handling**
- If `idgen` sends a heartbeat and the Coordinator **detects the ID is marked as unassigned**, `idgen` will:
  1. **Release its machine ID**.
  2. **Reset the Snowflake generator**.
  3. **Request a new machine ID and wait until it is reassigned**.

---

## **Constants Used**
### **Coordinator-Side Constants**
| **Variable** | **Description** | **Default Value** |
|-------------|----------------|------------------|
| `ID_POOL` | Set of 1024 available machine IDs | `{0-1023}` |
| `ASSIGNED_ID_POOL` | Machine IDs currently assigned | `set()` |
| `ID_MAP` | Bidirectional map of `machine_id ↔ POD_UID` | `bidict({})` |
| `HEARTBEAT_TRACKER` | Tracks last heartbeat time for each machine ID | `{}` |
| `HEARTBEAT_DELAY` | Time before marking a pod as dead | `30s` |
| `SHELVE_TIME` | Time before a shelved ID is reassigned | `120s` |
| `EXPIRED_ID_CLEANUP_INTERVAL` | Interval between expired ID cleanups | `20s` |

### **ID Service (`idgen`) Constants**
| **Variable** | **Description** | **Default Value** |
|-------------|----------------|------------------|
| `COORDINATOR_URL` | URL of the Coordinator service | `"http://localhost:5000"` |
| `CURRENT_POD` | Pod name of the `idgen` instance | `"id-generator-0"` |
| `POD_UID` | Unique identifier for the pod | `"0"` |
| `MACHINE_ID` | Assigned machine ID | `None` |
| `EPOCH` | Epoch timestamp for Snowflake generator | `1739526270` (Feb 14, 2025) |
| `MACHINE_ID_REQUEST_INTERVAL` | Time between machine ID requests | `30s` |
| `HEARTBEAT_INTERVAL` | Time between heartbeats | `10s` |
| `heartbeat_failures` | Consecutive heartbeat failures | `0` |
| `MAX_HEARTBEAT_FAILURES` | Maximum consecutive heartbeat failures before re-requesting an ID | `5` |

---

## **Summary of Key Behaviors**
| **Scenario** | **Coordinator Action** | **ID Generation Service Action** |
|-------------|------------------------|--------------------------------|
| **Pod does not send heartbeat for 30s** | Shelves ID for `SHELVE_TIME` (120s) | Continues working if network issue, resets ID if Coordinator marks unassigned |
| **Network failure occurs** | Waits 30s, then shelves ID | If `MAX_HEARTBEAT_FAILURES` reached, resets ID and waits for reassignment |
| **Duplicate ID detected** | Tags ID as unassigned | Releases ID, resets Snowflake generator, and requests new ID |
| **Coordinator crashes** | ID map is lost, existing pods work until heartbeat failures trigger resets | If `MAX_HEARTBEAT_FAILURES` reached, resets ID and waits for Coordinator to recover |

---

### **Final Thoughts**
This updated documentation ensures that:
✅ **Machine IDs are efficiently managed** and never reassigned too early.  
✅ **ID Generation Service handles network failures gracefully** by self-recovering.  
✅ **Duplicate ID usage is detected and corrected automatically.**  
✅ **Pods do not hold IDs indefinitely, ensuring fairness and stability in the system.**  

This **fault-tolerant design** ensures smooth operation even in **network failures, Coordinator crashes, or pod failures**. 🚀
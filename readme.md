
# Integer Id generation at scale using Kubernetes 


As you may know, **integer IDs** offer several advantages:

- **Smaller Storage** – `4-8 bytes` vs. `16 bytes` for UUIDs.
- **Faster Indexing & Lookups** – Improves database performance.
- **Better Readability** – Easier to read, debug, and reference.
- **Efficient Joins** – Speeds up foreign key relationships.
- **Auto-incrementing** – Maintains order and predictability.

#### **Scaling Challenge**

Generating integer IDs at scale can be tricky. Twitter solved this with **Snowflake**, a **64-bit time-sortable ID** system capable of **4 billion IDs/sec** using **32 workers across 32 data centers**. However, this setup is overkill for most cases, where **1–100 million IDs/sec** is more than enough.


#### **Approach**

In this project, we'll use **Go Service (optionally Python/Fastapi)  on Kubernetes**, replacing **data centers** with **nodes** and **workers** with **pods/replicas**. For example, in a **32-node cluster**, each node can run **32 pods(only 1 container per pod)**, totaling **1024 pods**—matching Twitter’s Snowflake throughput.

Estimated ID generation rates:

- **1024 replicas → 4B IDs/sec**
- **32 replicas → 128M IDs/sec**
- **4 replicas → 16M IDs/sec**

The concept is straightforward: **deploy an ID generation service on Kubernetes** and adjust replicas based on demand.




## Prerequisites

Before using this project, it's recommended to have knowledge of:

- **Docker**: Understanding containerization.
- **Kubernetes (k3s)**: For deployment and scaling.
- **Twitter Snowflake Algorithm**: How unique IDs are generated.



## Project Structure
```txt
./          
├── id-generator/     # id service implemented in python/fastapi
├── id-generator-go/  # id service implemented in go
├── kube/             # Dir containing all k8s config files
│   ├── headless-service.yaml
│   ├── ingress.yaml            
│   ├── namespace.yaml         
│   ├── service.yaml             
│   └── statefulset.yaml        
├── testing/           # Dir containing files for testing the service 
│   ├── database.py     # define sqllite db to temply store ids during load tests
│   ├── generated_ids.db  # sqllite db
│   ├── load_test.py      # load test the service
│   ├── service_test.py   # verify service health
│   └── snowflake_test.py   # Demonstrates how Snowflake ID generation logic
├── commands.md                         # All project related commands
└── readme.md                           # Project overview and setup instructions

```
## ID Generation Service - Quick Overview

#### Environment Variables
- **Node name, Pod UID, and Pod name** are injected by Kubernetes into the containers (configured in `statefulset.yaml`).
- **Node name** and **Pod UID** are optional and used only for debugging.
 
#### Machine ID Extraction
**Machine/instance ID** (range: 0-1023) is extracted from the **Pod name** to initialize the **Snowflake generator**.
```python
# Extract the machine ID from the pod name  
MACHINE_ID = int(re.search(r"\d+", POD_NAME).group())  
  
# Initialize snowflkae id generator  
integer_id_generator = SnowflakeGenerator(instance=MACHINE_ID, epoch=EPOCH)
```
#### Endpoints
When requested, the Snowflake generator produces unique IDs.
```python
@app.get("/generate-id")  
def generate_id_integer():  
    """Generate a Snowflake-based integer ID."""  
    return {"id": next(integer_id_generator)}
```
- **No Collisions:** Kubernetes guarantees unique pod names, ensuring collision-free ID generation across instances.

## Setup Process

### **1. Clone the Repository**

```bash
git clone <repo-url>
cd integer-id-generation-at-scale-using-kubernetes
```



### **2. Setup Environment**

The service is implemented in both **Python** and **Go**. You can choose which version to run based on your preference.

**Performance Note:**  
Local testing shows the **Go implementation is approximately 2x faster** than the Python version.


#### **Working with Python (FastAPI)**

If you choose the **Python/FastAPI** service:

1. **Navigate** to the Python service directory.
2. **Set up a virtual environment** for isolated dependencies.
3. **Install required packages** from `requirements.txt`.
4. **Run the service** locally.
5. **Test the service** via:
    - Swagger docs: [http://localhost:8000/docs](http://localhost:8000/docs)
    - Running the test script: `testing/service_test.py`

```bash
cd ./id-generator

# Create and activate a virtual environment
python3.11 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run the service locally
uvicorn id-generator.main:app --reload --host "0.0.0.0" --port 8000
```


#### **Working with Go**

If you choose the **Go** service:

1. **Ensure Go is installed** on your machine.
2. **Navigate** to the Go service directory.
3. **Install dependencies** using `go mod tidy`.
4. **Run the service** locally for quick testing.
5. **Build the binary** for production use and run it.
6. **Test the service** by running `testing/service_test.py`.

```bash
cd ./id-generator-go

# Install dependencies
go mod tidy

# Run the service locally
go run main.go

# Build and run the binary
go build -o id-generator
./id-generator
```



**Testing:**  
You can verify both versions by running:

```bash
python testing/service_test.py
```

Or by visiting the **Swagger documentation** for the Python service at:  
[http://localhost:8000/docs](http://localhost:8000/docs)

### **3. Build and Push Docker Images**

```bash
# Decide which service to use: Go or Python (this example uses Go)

# Build the Docker image using the Go service
docker build -t id-generator ./id-generator-go/

# Re-tag the image for the local registry
docker tag id-generator localhost:5001/id-generator

# Run a local Docker registry (if not already running)
docker run -d -p 5001:5000 --name local-registry registry:2

# Push the image to the local registry
docker push localhost:5001/id-generator
```

 **Notes:**

- Replace `./id-generator-go/` with `./id-generator/` if you are using the Python service.
- The local registry allows Kubernetes to pull images without external dependencies.

### **4. Install k3s**

```bash
curl -sfL https://get.k3s.io | sh -
```


**Why k3s?**

- Lightweight Kubernetes distribution for local and edge deployments.
- Simple to install with minimal resource requirements.

### **5. Verify k3s Installation**

```bash
sudo kubectl get nodes
```

**Expected Output:**  
You should see the node in a **"Ready"** state, indicating that k3s is successfully installed and running.

```bash
NAME        STATUS   ROLES                  AGE     VERSION
your-node   Ready    control-plane,master   5m      v1.xx.x+k3s
```
 
### **6. Configure k3s to Use Local Registry**

Edit `/etc/rancher/k3s/registries.yaml` and add:

```yaml
mirrors:
  "localhost:5001":
    endpoint:
      - "http://localhost:5001"
```

Restart k3s:

```bash
sudo systemctl restart k3s
```

### **7. Deploy Services to k3s**

```bash
cd ./kube
sudo kubectl apply -f namespace.yaml
sudo kubectl apply -f statefulset.yaml
sudo kubectl apply -f service.yaml
sudo kubectl apply -f ingress.yaml
```

### **8.  Monitoring & Scaling **

```bash
# View the pods in the cluster
sudo kubectl get pods -n id-system

# Scale the no of pods/replicas of our stateful set service in the cluster
sudo kubectl scale statefulset id-generator --replicas=2 -n id-system

# View the logs
sudo kubectl logs statefulset/id-generator -n id-system --all-containers
```

### **9. Access the Services**

You can access the **ID Generation Service** at:   `http://localhost:80` or `http://localhost/`

**For FastAPI (Python) Service:**  
If you deployed the FastAPI version, the interactive API documentation is available at: `http://localhost:80/docs` or `http://localhost/docs`

### **10. Cleanup** 

```bash
# remove k8s services  
cd ./kube  
sudo kubectl delete -f statefulset.yaml  
sudo kubectl delete -f service.yaml  
sudo kubectl delete -f ingress.yaml  
sudo kubectl delete -f namespace.yaml  
  
  
# Verify services are removed  
sudo kubectl get all -n id-system  
  
  
# Stop and remove local docker registry  
docker stop local-registry  
docker rm local-registry  
  
# Remove images from local registry  
docker image rm localhost:5001/id-generator  
docker image rm id-generator
```
**Note:** For a complete list of project-related commands, refer to the **`commands.md`** file.
## Rate Estimations

- The **theoretical ID generation rate** of the **Twitter Snowflake** algorithm is approximately **4.19 billion IDs per second**.
- With **1024 replicas** (maximum allowed machine IDs), we achieve a **similar rate of ~4 billion IDs per second**.
- A **32-replica deployment** yields **~128 million IDs per second**, which is sufficient for most use cases.
- The ID generator remains functional for **69 years** from the chosen epoch.

### ⚠️ **Practical Considerations:**

> While theoretical rates are impressive, **real-world performance may vary** due to several factors:

- **Network Latency & Routing Overhead:**  
    Communication delays between clients, load balancers, and service instances can reduce the effective generation rate.
    
- **Resource Contention:**  
    Deploying multiple pods on the **same node** leads to **CPU and memory sharing**, potentially reducing performance under heavy loads.
    
- **Scaling Across Nodes:**  
    Distributing pods across **multiple nodes** with **fewer but adequately resourced pods per node** improves stability and overall throughput.
    
**Recommendation:**  
To achieve higher throughput and stable performance:

- **Scale horizontally** across multiple nodes.
- **Avoid overcrowding** a single node with too many pods.
- Use **resource limits** in Kubernetes to prevent excessive resource contention.


## Conclusion

The **ID Generator** project efficiently generates **64-bit time-sortable integer IDs** using Kubernetes and a distributed architecture. With robust **failure handling**, **scalability**, and **high availability**, it ensures unique ID generation even in large-scale applications. By leveraging **Snowflake IDs** and a **heartbeat-based coordinator**, this system provides **fault tolerance**, **high throughput**, and **long-term reliability**.
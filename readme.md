
# Integer Id generation at scale using Kubernetes 


As you may know, **integer IDs** offer several advantages:

- **Smaller Storage** – `4-8 bytes` vs. `16 bytes` for UUIDs.
- **Faster Indexing & Lookups** – Improves database performance.
- **Better Readability** – Easier to read, debug, and reference.
- **Efficient Joins** – Speeds up foreign key relationships.
- **Auto-incrementing** – Maintains order and predictability.

#### **Scaling Challenge**
Generating integer IDs at scale can be tricky. Twitter solved this with **Snowflake**, a **64-bit time-sortable ID** system capable of **4 billion IDs/sec** using **32 workers across 32 data centers**. However, this setup is overkill for most cases, where **1–100 million IDs/sec** is more than enough.
#### Approach
In this project, we’ll run a **Go service (optionally Python/FastAPI)** on Kubernetes, where **data centers** are replaced by **nodes** and **workers** by **pods/replicas**. For example, a **32-node cluster** with **32 pods per node** can reach **1024 pods**—matching Twitter’s Snowflake scale.

**Estimated ID generation rates:**

- **1024 replicas → ~4B IDs/sec**
- **32 replicas → ~128M IDs/sec**
- **4 replicas → ~16M IDs/sec**

Just **deploy the service on Kubernetes** and scale replicas as needed.

**Note**
- **Never exceed 1024 replicas** because Snowflake uses 10 bits for worker IDs (0–1023).
- We use a **StatefulSet**—not a **Deployment**—because **StatefulSets** guarantee stable, ordinal pod names (e.g., `pod-0`, `pod-1`). These **ordinal numbers** act as each pod’s **unique worker ID** in the Snowflake algorithm, ensuring no ID collisions across pods.
- During the course of this project we will be using a **k3s** cluster for local testing, as it provides a lightweight Kubernetes environment to easily set up and validate the entire configuration.
## Prerequisites
Before using this project, it's recommended to have knowledge of:
- **Docker**: Understanding containerization.
- **Kubernetes (k3s)**: For deployment and scaling.
- **Twitter Snowflake Algorithm**: How unique IDs are generated.
## Project Structure
Below is the structure of the project, along with a description of what each file and folder represents.
```txt
./          
├── id-generator/     # id service implemented in python/fastapi
├── id-generator-go/  # id service implemented in go
├── kube/             # Dir containing all k8s config files
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

For Snowflake ID generation to work correctly, **each worker must have a unique ID**. In our setup, this is achieved through a **stateful Kubernetes cluster** with **ordinal pod naming** (e.g., `id-generation-0` to `id-generation-1023`).

Kubernetes guarantees **unique pod names**, allowing us to use the pod's ordinal number as the **instance/machine/worker ID**. This ID is then used to **initialize the Snowflake generator** and serve incoming requests reliably.
```python
# Extract the machine ID from the pod name  
MACHINE_ID = int(re.search(r"\d+", POD_NAME).group())  
  
# Initialize snowflake id generator  
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

#### ⚠️ Collisions
- **Cross-pod collisions are impossible** because each pod has a unique **worker ID** (derived from the pod’s ordinal name).
- **Same-pod collisions are possible** in the **Python** implementation because the `snowflake-id` package is **not thread-safe**. Under high concurrency, two threads within one pod could generate the same ID (though this is rare in Python due to the GIL).
In contrast, the **Go package** [`github.com/bwmarrin/snowflake`](https://github.com/bwmarrin/snowflake) is **thread-safe** and ideal for multithreaded environments.

👉 **Recommendation:**

- Use **Python** for testing and learning.
- Use **Go** for production or high-concurrency scenarios.
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

# You can test go service by running it directly or building the binary and then running it
# Run the service locally
go run main.go

# Build and run the binary
go build -o id-generator
./id-generator
```

**Testing:**  
You can verify both versions by running: `testing/service_test.py`
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

### **8.  Monitoring & Scaling**
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
  
# Remove images
docker image rm localhost:5001/id-generator  
docker image rm id-generator
```
**Note:** For a complete list of project-related commands, refer to the **`commands.md`** file.
## Rate Estimations
- The **theoretical ID generation rate** of the **Twitter Snowflake** algorithm is approximately **4.19 billion IDs per second**.
- With **1024 replicas** (maximum allowed machine IDs), we achieve a **similar rate of ~4 billion IDs per second**.
- A **32-replica deployment** yields **~128 million IDs per second**, which is sufficient for most use cases.
- The ID generator remains functional for **69 years** from the chosen epoch.

 In local tests on a 32 GB RAM Intel i7 machine with 4 pods , Python reached ~4,000 IDs/sec and Go ~9,000 IDs/sec. Actual performance may differ in production due to resource contention when both service and tests run on the same machine.
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

This project demonstrates how to deploy a Snowflake-based ID generation service at scale using Kubernetes (k3s) and a StatefulSet for stable, unique worker IDs. For most real-world production needs, the Go version is recommended due to its thread safety and better performance.
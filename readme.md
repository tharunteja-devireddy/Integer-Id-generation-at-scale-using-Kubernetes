
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

In this project, we'll use **Python/FastAPI on Kubernetes**, replacing **data centers** with **nodes** and **workers** with **pods/replicas**. For example, in a **32-node cluster**, each node can run **32 pods(only 1 container per pod)**, totaling **1024 pods**—matching Twitter’s Snowflake throughput.

Estimated ID generation rates:

- **1024 replicas → 4B IDs/sec**
- **32 replicas → 128M IDs/sec**
- **4 replicas → 16M IDs/sec**

The concept is straightforward: **deploy an ID generation service on Kubernetes** and adjust replicas based on demand.


## System Architecture


## Project Overview

### Directory Structure

- **coordinator-service/**: Manages machine ID assignments and tracks active instances.
- **id-service/**: Generates unique integer IDs based on the Snowflake algorithm.
- **kube/**: Kubernetes deployment configuration files.
- **venv/**: Python virtual environment.
- **commands.md**: List of commands for running and managing the system.
- **service.md**: Detailed documentation of Coordinator and ID services.
- **snowflake_test.py**: Demonstrates integer ID generation using Snowflake.
- **service_test.py**: Scripts to test Coordinator and ID services.

---

## Prerequisites

Before using this project, it's recommended to have knowledge of:

- **Docker**: Understanding containerization.
- **Kubernetes (k3s)**: For deployment and scaling.
- **Twitter Snowflake Algorithm**: How unique IDs are generated.

Refer to `service.md` for a detailed explanation of how each service operates.

---

## Walkthrough of Setup Process

### 1. Clone the Repository

```bash
git clone <repo-url>
cd ID-Generator
```

### 2. Setup Local Virtual Environment (Python 3.11)

```bash
python3.11 -m venv venv
source venv/bin/activate
pip install -r coordinator-service/requirements.txt
pip install -r id-service/requirements.txt
```

### 3. Start Services Locally

```bash
uvicorn coordinator-service.main:app --reload --host "0.0.0.0" --port 5000 --log-level debug
uvicorn id-service.main:app --reload --host "0.0.0.0" --port 8000 --log-level debug
```

### 4. Test the Services

Run `service_test.py` to ensure services are running correctly:

```bash
python service_test.py
```

### 5. Build and Push Docker Images

```bash
docker build -t id-service ./id-service/
docker build -t coordinator-service ./coordinator-service/

docker run -d -p 5001:5000 --name local-registry registry:2

docker tag id-service localhost:5001/id-service
docker tag coordinator-service localhost:5001/coordinator-service

docker push localhost:5001/id-service
docker push localhost:5001/coordinator-service
```

### 6. Install k3s

```bash
curl -sfL https://get.k3s.io | sh -
```

### 7. Verify k3s Installation

```bash
sudo kubectl get nodes
```

### 8. Configure k3s to Use Local Registry

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

### 9. Deploy Services to k3s

```bash
cd kube
sudo kubectl apply -f namespace.yaml
sudo kubectl apply -f coordinator-deployment.yaml
sudo kubectl apply -f id-generation-deployment.yaml
sudo kubectl apply -f ingress.yaml
```

### 10. Verify Running Services

```bash
sudo kubectl get pods -n id-system
```

### 11. Scale Services

```bash
sudo kubectl scale deployment id-service --replicas=2 -n id-system
sudo kubectl scale deployment coordinator-service --replicas=1 -n id-system
```

### 12. View Logs

```bash
sudo kubectl logs deployment/coordinator-service -n id-system --all-containers
sudo kubectl logs deployment/id-service -n id-system --all-containers
```

### 13. Access the Services

- **Coordinator Service**: `http://localhost:5000`
- **ID Generation Service**: `http://localhost:8000`

### 14. Cleanup (Refer to commands.md for more details)

```bash
sudo kubectl delete -f coordinator-deployment.yaml
sudo kubectl delete -f id-generation-deployment.yaml
sudo kubectl delete -f ingress.yaml
sudo kubectl delete -f namespace.yaml
```

---

## Rate Estimations

- The theoretical ID generation rate of **Twitter Snowflake** is **4.19 billion IDs per second**.
- Using **1024 replicas**, we achieve a **similar rate of ~4 billion IDs per second**.
- However, a **32-replica deployment** achieves **~128 million IDs per second**, which suffices for most use cases.
- The ID generator works for **69 years** from the chosen epoch before switching a flag bit for another **69 years**.

---

## Deploying to Production

If deploying this project in production, consider:

- **Increasing replicas** of `id-generation-deployment` to `1024` for high throughput.
- **Persisting ID allocation** (e.g., using Redis cache) with:

```python
ID_POOL = set(range(1024))
ASSIGNED_ID_POOL = set()
ID_MAP = bidict({})
HEARTBEAT_TRACKER = {}
```

- **Adding authentication** to both `Coordinator Service` and `ID Service`.

---

## Conclusion

The **ID Generator** project efficiently generates **64-bit time-sortable integer IDs** using Kubernetes and a distributed architecture. With robust **failure handling**, **scalability**, and **high availability**, it ensures unique ID generation even in large-scale applications. By leveraging **Snowflake IDs** and a **heartbeat-based coordinator**, this system provides **fault tolerance**, **high throughput**, and **long-term reliability**.
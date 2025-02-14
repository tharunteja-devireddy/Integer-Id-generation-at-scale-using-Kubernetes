### **🔥 Running Your Kubernetes-Based ID Generator Locally on Ubuntu (with Docker & K3s)**
Since you're on **Ubuntu** and have **Docker installed**, the easiest way to run Kubernetes locally is **K3s** (a lightweight Kubernetes distribution). 

---

## **✅ Step 1: Install K3s (Lightweight Kubernetes)**
Run the following commands to install K3s:

```sh
curl -sfL https://get.k3s.io | sh -
```

Once installed, verify that your cluster is running:
```sh
sudo kubectl get nodes

sudo systemctl start k3s
sudo systemctl stop k3s


kubectl apply -f statefulset.yaml
kubectl apply -f service.yaml

```
You should see something like:
```
NAME      STATUS   ROLES                  AGE   VERSION
ubuntu    Ready    control-plane,master    1m   v1.27.4+k3s1
```

If `kubectl` is not working, set up your environment:
```sh
export KUBECONFIG=/etc/rancher/k3s/k3s.yaml
```

---

## **✅ Step 2: Create the Kubernetes YAML Files**
Now, create the necessary Kubernetes config files.

### **1️⃣ `statefulset.yaml` (Creates 32 Pods)**
```yaml
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: id-generator
spec:
  replicas: 32  # Number of pods
  serviceName: "id-generator"
  selector:
    matchLabels:
      app: id-generator
  template:
    metadata:
      labels:
        app: id-generator
    spec:
      containers:
      - name: id-generator-container
        image: id-generator:latest  # Will build this locally
        env:
        - name: NODE_NAME
          valueFrom:
            fieldRef:
              fieldPath: spec.nodeName  # Auto-assign node name
        - name: POD_NAME
          valueFrom:
            fieldRef:
              fieldPath: metadata.name  # Auto-assign pod name
```

---

## **✅ Step 3: Create the Python Application**
Create a directory for your project and a `main.py` file.

```sh
mkdir id-generator
cd id-generator
nano main.py
```

### **2️⃣ `main.py` (Extracts IDs and Runs the Service)**
```python
import os
import re
import time

# Extract the node index from node name (e.g., node-3 → datacenter_id = 3)
node_name = os.getenv("NODE_NAME", "node-0")  # Default if not set
node_match = re.search(r'(\d+)$', node_name)
datacenter_id = int(node_match.group(1)) if node_match else 0  # Defaults to 0

# Extract pod index from pod name (e.g., id-generator-5 → worker_id = 5)
pod_name = os.getenv("POD_NAME", "id-generator-0")  # Default if not set
pod_match = re.search(r'(\d+)$', pod_name)
worker_id = int(pod_match.group(1)) if pod_match else 0  # Defaults to 0

print(f"✅ Running ID Generator with DATACENTER_ID={datacenter_id}, WORKER_ID={worker_id}")

# Simulate ID generation (loop for testing)
while True:
    timestamp = int(time.time() * 1000)  # Current timestamp in ms
    unique_id = (timestamp << 22) | (datacenter_id << 12) | worker_id
    print(f"Generated ID: {unique_id}")
    time.sleep(2)  # Simulate workload
```

---

## **✅ Step 4: Create the Dockerfile**
Inside the same `id-generator` directory, create a `Dockerfile`:

```sh
nano Dockerfile
```

### **3️⃣ `Dockerfile`**
```dockerfile
FROM python:3.9

WORKDIR /app

COPY main.py /app/main.py

CMD ["python", "main.py"]
```

---

## **✅ Step 5: Build the Docker Image**
Now, build the image locally:

```sh
docker build -t id-generator .
```

Verify the image:
```sh
docker images | grep id-generator
```

---

## **✅ Step 6: Load the Image into K3s**
Since K3s runs in a separate environment, we need to load the local Docker image into K3s:

```sh
k3s ctr images import id-generator:latest
```

---

## **✅ Step 7: Deploy to Kubernetes**
Apply the StatefulSet:

```sh
kubectl apply -f statefulset.yaml
```

Check if pods are running:
```sh
kubectl get pods
```
You should see something like:
```
NAME                READY   STATUS    RESTARTS   AGE
id-generator-0      1/1     Running   0          10s
id-generator-1      1/1     Running   0          10s
...
id-generator-31     1/1     Running   0          10s
```

---

## **✅ Step 8: Check the Logs**
To verify that each pod has a **unique datacenter ID and worker ID**, check the logs of a few pods:

```sh
kubectl logs id-generator-0
kubectl logs id-generator-1
```
You should see logs like:
```
✅ Running ID Generator with DATACENTER_ID=0, WORKER_ID=0
Generated ID: 16274817293947900
Generated ID: 16274817293947901
...
```

---

## **🔥 Success! Now your ID Generator is Running in Kubernetes**
This setup:
✅ **Ensures unique node and pod names**.  
✅ **Extracts IDs dynamically in Python**.  
✅ **Runs completely inside Kubernetes without manual node labeling**.  

### **💡 Bonus: Delete Everything**
If you want to clean up your cluster:

```sh
kubectl delete -f statefulset.yaml
```

Or completely remove K3s:

```sh
/usr/local/bin/k3s-uninstall.sh
```

---

🔥 **Now your ID generator is fully functional locally! 🚀**  
Would you like any modifications or enhancements? 😊
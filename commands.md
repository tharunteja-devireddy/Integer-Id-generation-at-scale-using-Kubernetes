
## Commands


#### Start services locally, coordinator-service and id-service
```bash
uvicorn coordinator-service.main:app --reload --host "0.0.0.0" --port 5000 --log-level debug
uvicorn id-service.main:app --reload --host "0.0.0.0" --port 8000 --log-level debug
```

#### Install k3s on linux/ubuntu
```bash
curl -sfL https://get.k3s.io | sh -
```

#### Verify k3s working or not
```bash
sudo kubectl get nodes

# Commands to manage k3s
sudo systemctl start k3s
sudo systemctl stop k3s
sudo systemctl restart k3s
```


####  Build images
```bash
docker build -t id-service ./id-service/
docker build -t coordinator-service ./coordinator-service/

# Creating a local registry
docker run -d -p 5001:5000 --name local-registry registry:2

# Re-tag images
docker tag id-service localhost:5001/id-service
docker tag coordinator-service localhost:5001/coordinator-service

# Push images to local registry
docker push localhost:5001/id-service
docker push localhost:5001/coordinator-service
```

#### Whitelist the local registry in k3s
`/etc/rancher/k3s/registries.yaml`
```yaml
mirrors:
  "localhost:5001":
    endpoint:
      - "http://localhost:5001"

````
# restart k3s to apply the changes
`sudo systemctl restart k3s`


# list down objects in default name space
sudo kubectl get all -n default

# remove old applied files
sudo kubectl delete -f ./kube/headless-service.yaml
sudo kubectl delete -f ./kube/statefulset.yaml
sudo kubectl delete -f ./kube/service.yaml
sudo kubectl delete -f ./kube/ingress.yaml

# Apply new files
cd ./kube
sudo kubectl apply -f namespace.yaml
sudo kubectl apply -f coordinator-deployment.yaml
sudo kubectl apply -f id-generation-deployment.yaml
sudo kubectl apply -f ingress.yaml


# View services(use id-system as this the namespace we created)
sudo kubectl get pods -n id-system

# Scale services
sudo kubectl scale deployment id-service --replicas=2 -n id-system
sudo kubectl scale deployment coordinator-service --replicas=1 -n id-system

# View service logs
sudo kubectl logs deployment/coordinator-service -n id-system --all-containers
sudo kubectl logs deployment/id-service -n id-system --all-containers
# -f for stream


# Remove services
cd ./kube
sudo kubectl delete -f coordinator-deployment.yaml
sudo kubectl delete -f id-generation-deployment.yaml
sudo kubectl delete -f ingress.yaml
sudo kubectl delete -f namespace.yaml

# Uninstall k3s
# /usr/local/bin/k3s-uninstall.sh
```

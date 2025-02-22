
### Commands

List of all the commands used in the project

#### Start services locally, coordinator-service and id-service
```bash
uvicorn coordinator-service.main:app --reload --host "0.0.0.0" --port 5000 --log-level debug
uvicorn id-service.main:app --reload --host "0.0.0.0" --port 8000 --log-level debug

```


####  Build images and push them into local registry
```bash
docker build -t id-service ./id-service/
docker build -t coordinator-service ./coordinator-service/

# Creating a local registry
docker run -d -p 5001:5000 --name local-registry registry:2

# Re-tag images
docker tag id-service localhost:5001/id-service
docker tag coordinator-service localhost:5001/coordinator-service

# Run local registry
docker run -d -p 5001:5000 --name local-registry registry:2

# Push images to local registry
docker push localhost:5001/id-service
docker push localhost:5001/coordinator-service
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


#### Whitelist the local registry in k3s
`/etc/rancher/k3s/registries.yaml`
```yaml
mirrors:
  "localhost:5001":
    endpoint:
      - "http://localhost:5001"

````
- restart k3s to apply the changes
  `sudo systemctl restart k3s`


  
#### Deploy services in k3s
```bash
cd ./kube
sudo kubectl apply -f namespace.yaml
sudo kubectl apply -f coordinator-deployment-active.yaml
sudo kubectl apply -f coordinator-deployment-standby.yaml
sudo kubectl apply -f coordinator-service.yaml
sudo kubectl apply -f priority-classes.yaml
sudo kubectl apply -f pod-disruption-budget.yaml
sudo kubectl apply -f id-generation-deployment.yaml
sudo kubectl apply -f ingress.yaml


# View services(use id-system as this the namespace we created)
sudo kubectl get pods -n id-system

# Scale services
sudo kubectl scale deployment id-service --replicas=2 -n id-system

# View service logs
sudo kubectl logs deployment/coordinator-service-active -n id-system --all-containers
sudo kubectl logs deployment/coordinator-service-standby -n id-system --all-containers
sudo kubectl logs deployment/id-service -n id-system --all-containers
# -f for stream
````


#### Clean up services
```bash
# remove k8s services
cd ./kube
sudo kubectl delete -f coordinator-deployment-active.yaml
sudo kubectl delete -f coordinator-deployment-standby.yaml  
sudo kubectl delete -f coordinator-service.yaml
sudo kubectl delete -f priority-classes.yaml
sudo kubectl delete -f pod-disruption-budget.yaml
sudo kubectl delete -f id-generation-deployment.yaml
sudo kubectl delete -f ingress.yaml
sudo kubectl delete -f namespace.yaml


# Verify services are removed
sudo kubectl get all -n id-system


# Stop and remove local docker registry
docker stop local-registry
docker rm local-registry

# Remove images
docker image rm localhost:5001/id-service
docker image rm id-service
docker image rm localhost:5001/coordinator-service
docker image rm coordinator-service


  
```


#### Uninstall k3s
```bash
/usr/local/bin/k3s-uninstall.sh
```

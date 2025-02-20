
### Commands

List of all the commands used in the project

#### Start service locally
```bash
# Setup up python env with requirements
uvicorn id-generator.main:app --reload --host "0.0.0.0" --port 8000 --log-level debug

# Setup go, install dependencies and run
go run id-generator-go.main.go
```


####  Build images and push them into local registry
```bash
# Use Fastapi service
# docker build -t id-generator ./id-generator/

# Use Go service
docker build -t id-generator ./id-generator-go/

# Re-tag images
docker tag id-generator localhost:5001/id-generator

# Run local registry
docker run -d -p 5001:5000 --name local-registry registry:2

# Push images to local registry
docker push localhost:5001/id-generator
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
sudo kubectl apply -f statefulset.yaml
sudo kubectl apply -f service.yaml
sudo kubectl apply -f ingress.yaml


# View services(use id-system as this the namespace we created)
sudo kubectl get pods -n id-system

# Scale services
sudo kubectl scale statefulset id-generator --replicas=2 -n id-system

# View service logs
sudo kubectl logs statefulset/id-generator -n id-system --all-containers
# -f for stream
````


#### Clean up services
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

# Command to remove all images
# docker rmi $(docker images -q)

```


#### Uninstall k3s
```bash
/usr/local/bin/k3s-uninstall.sh
```

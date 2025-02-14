

```bash


curl -sfL https://get.k3s.io | sh -
curl -sfL https://get.k3s.io | \
  INSTALL_K3S_EXEC="--node-name=node-0" sh -

sudo kubectl get nodes

sudo systemctl start k3s
sudo systemctl stop k3s

# Save image as a tar file
docker save -o id-generator.tar id-generator:latest

sudo k3s ctr images import id-generator.tar
sudo k3s ctr images list

sudo k3s ctr images tag \
    docker.io/library/id-generator:latest \
    id-generator:latest


# Scale down to zero
sudo kubectl scale statefulset id-generator --replicas=0

# Wait a moment, then scale back up
sudo kubectl scale statefulset id-generator --replicas=4


sudo kubectl apply -f headless-service.yaml
sudo kubectl apply -f statefulset.yaml
sudo kubectl apply -f service.yaml
sudo kubectl apply -f ingress.yaml


sudo kubectl get nodes
sudo kubectl get pods


sudo kubectl get pods -l app=id-generator
sudo kubectl get svc
sudo kubectl get ingress

sudo kubectl logs id-generator-0
kubectl logs id-generator-1


kubectl delete -f statefulset.yaml


# /usr/local/bin/k3s-uninstall.sh
```

```bash

docker build -t id-generator ./

docker container run -p 8080:8080 -d --name id-generator id-generator

docker container stop id-generator
docker container rm id-generator
docker build -t id-generator ./
docker container run -p 8000:8000 -d --name id-generator id-generator

```
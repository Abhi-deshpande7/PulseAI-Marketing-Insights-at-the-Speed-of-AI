# 🐳 PulseAI — Docker & Kubernetes Guide

---

## 🐳 Docker

### Local Development

**1. Create your `.env` file** (never commit this):
```bash
ANTHROPIC_API_KEY=sk-ant-your-key-here
```

**2. Build the image:**
```bash
docker build -t pulseai:latest .
```

**3. Run the container:**
```bash
docker run -p 8501:8501 --env-file .env pulseai:latest
```
Open: http://localhost:8501 ✅

**4. With Docker Compose (easier):**
```bash
docker compose up
```
Stop with: `docker compose down`

---

### Push to Docker Hub

```bash
# Login
docker login

# Tag
docker tag pulseai:latest YOUR_USERNAME/pulseai:latest

# Push
docker push YOUR_USERNAME/pulseai:latest
```

---

## ☸️ Kubernetes

### Option A — Local with Minikube (free, your laptop)

**1. Install Minikube:**
```bash
# Windows (PowerShell as Admin)
winget install Kubernetes.minikube
winget install Kubernetes.kubectl
```

**2. Start cluster:**
```bash
minikube start --memory=4096 --cpus=2
```

**3. Deploy PulseAI:**
```bash
# Create namespace
kubectl apply -f k8s/namespace.yaml

# Create secret with your real API key
kubectl create secret generic pulseai-secrets \
  --from-literal=ANTHROPIC_API_KEY=sk-ant-your-key-here \
  --namespace=pulseai

# Deploy everything
kubectl apply -f k8s/deployment.yaml
kubectl apply -f k8s/service.yaml
kubectl apply -f k8s/hpa.yaml
```

**4. Access the app:**
```bash
minikube service pulseai-service --namespace=pulseai
```
This opens the app in your browser automatically ✅

**5. Useful commands:**
```bash
# Check pods
kubectl get pods -n pulseai

# Check logs
kubectl logs -l app=pulseai -n pulseai

# Scale manually
kubectl scale deployment pulseai --replicas=3 -n pulseai

# Watch autoscaling
kubectl get hpa -n pulseai -w

# Rolling update (zero downtime)
kubectl set image deployment/pulseai pulseai=YOUR_USERNAME/pulseai:v2 -n pulseai
kubectl rollout status deployment/pulseai -n pulseai

# Rollback if something breaks
kubectl rollout undo deployment/pulseai -n pulseai
```

---

### Option B — Cloud Kubernetes (production)

#### AWS EKS
```bash
# Install eksctl
# Create cluster
eksctl create cluster --name pulseai --region ap-south-1 --nodes 2

# Deploy
kubectl apply -f k8s/
```

#### Google GKE (easiest cloud K8s)
```bash
# Create cluster
gcloud container clusters create pulseai \
  --num-nodes=2 --region=asia-south1

# Get credentials
gcloud container clusters get-credentials pulseai --region=asia-south1

# Deploy
kubectl apply -f k8s/
```

#### Azure AKS
```bash
az aks create --resource-group pulseai-rg \
  --name pulseai-cluster --node-count 2
az aks get-credentials --resource-group pulseai-rg --name pulseai-cluster
kubectl apply -f k8s/
```

---

## 🔄 CI/CD with GitHub Actions

### Setup (one-time):

1. Go to your GitHub repo → **Settings → Secrets → Actions**
2. Add these secrets:
   - `DOCKERHUB_USERNAME` — your Docker Hub username
   - `DOCKERHUB_TOKEN` — Docker Hub access token (hub.docker.com → Account → Security)
   - `KUBECONFIG` — base64 of your kubeconfig:
     ```bash
     cat ~/.kube/config | base64
     ```

### How it works:
```
git push → GitHub Actions triggers →
  1. Runs tests (pipeline, data generator)
  2. Builds Docker image
  3. Pushes to Docker Hub with git SHA tag
  4. Deploys to Kubernetes with zero downtime
  5. Verifies rollout succeeded
```

Every push to `main` = automatic deployment. ✅

---

## 🏗️ Architecture Diagram

```
                    ┌─────────────────────────────────────┐
                    │         Kubernetes Cluster           │
                    │  ┌─────────────────────────────┐    │
  Internet ──────── │  │      Ingress (nginx)         │    │
                    │  └────────────┬────────────────┘    │
                    │               │                      │
                    │  ┌────────────▼────────────────┐    │
                    │  │    Service (LoadBalancer)    │    │
                    │  └────────────┬────────────────┘    │
                    │               │                      │
                    │  ┌────────────▼────────────────┐    │
                    │  │   Deployment (2-10 replicas) │    │
                    │  │  ┌─────────┐  ┌─────────┐   │    │
                    │  │  │ Pod 1   │  │ Pod 2   │   │    │
                    │  │  │PulseAI  │  │PulseAI  │   │    │
                    │  │  │:8501    │  │:8501    │   │    │
                    │  │  └─────────┘  └─────────┘   │    │
                    │  └─────────────────────────────┘    │
                    │               ▲                      │
                    │  ┌────────────┴────────────────┐    │
                    │  │  HPA (auto-scales 2-10)      │    │
                    │  └─────────────────────────────┘    │
                    │               ▲                      │
                    │  ┌────────────┴────────────────┐    │
                    │  │  Secret (ANTHROPIC_API_KEY)  │    │
                    │  └─────────────────────────────┘    │
                    └─────────────────────────────────────┘
                                    │
                    ┌───────────────▼──────────────────────┐
                    │        External Services              │
                    │  Anthropic API (Claude)               │
                    └──────────────────────────────────────┘
```

---

## 📋 What to say in your college presentation

> "PulseAI is containerised with Docker using a multi-stage build that separates the compilation environment from the runtime image, keeping the final image lean and secure. It runs as a non-root user inside the container. On Kubernetes, we deploy 2 replicas with a rolling update strategy for zero-downtime deployments, a Horizontal Pod Autoscaler that scales from 2 to 10 pods based on CPU and memory, liveness and readiness probes for self-healing, and secrets management to keep the API key out of the image. The entire pipeline — test, build, push, deploy — is automated with GitHub Actions."

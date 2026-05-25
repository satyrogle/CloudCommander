# Staging Deployment Runbook

## Environment Preparation

Ensure your local `.env.staging` file is populated. This file is git-ignored and must never be committed.

## Standard Deployment

Execute the PowerShell scripts to inject secrets, build the current commit, push to the registry, and apply the manifests.

```powershell
.\scripts\apply-secrets.ps1
.\scripts\deploy-staging.ps1
```

## Rollback Procedure

If a deployment fails, revert to a known-good state by pointing the deployments to an older, stable Git SHA.

Identify the stable short SHA, for example `8bc7fc4`.

Update the manifest files locally:

```powershell
(Get-Content k8s/staging/api-deployment.yaml) -replace 'image: jakeyy8/cloudcommander-api:.*', 'image: jakeyy8/cloudcommander-api:<OLD_SHA>' | Set-Content k8s/staging/api-deployment.yaml

(Get-Content k8s/staging/worker-deployment.yaml) -replace 'image: jakeyy8/cloudcommander-worker:.*', 'image: jakeyy8/cloudcommander-worker:<OLD_SHA>' | Set-Content k8s/staging/worker-deployment.yaml
```

Apply the reverted manifests:

```powershell
kubectl apply -f k8s/staging/api-deployment.yaml
kubectl apply -f k8s/staging/worker-deployment.yaml
```

## Complete Teardown

To spin down the compute resources while preserving the namespace and persistent data, if applicable:

```powershell
kubectl delete -f k8s/staging/service-ingress.yaml
kubectl delete -f k8s/staging/worker-deployment.yaml
kubectl delete -f k8s/staging/api-deployment.yaml
```

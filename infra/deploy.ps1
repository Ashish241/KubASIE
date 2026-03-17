# =============================================================================
# deploy.ps1 - Deploy the K8s Auto-Scaling Intelligence Engine to Minikube
# =============================================================================
# Usage (from the project root):
#   .\infra\deploy.ps1          # full deploy
#   .\infra\deploy.ps1 -Clean   # delete namespace, then full deploy
#   .\infra\deploy.ps1 -Memory 2048  # override RAM (MB) for low-memory machines
#
# Prerequisites: minikube, kubectl, docker (all on PATH)
# =============================================================================
param(
    [switch]$Clean,
    [int]$Memory = 3500   # MB - safe default that fits inside Docker Desktop's 3806 MB cap
)

$NAMESPACE    = "autoscaler"
$SCRIPT_DIR   = $PSScriptRoot
$PROJECT_ROOT = Split-Path $SCRIPT_DIR -Parent

function Info { param($msg) Write-Host "[INFO]  $msg" -ForegroundColor Cyan }
function Warn { param($msg) Write-Host "[WARN]  $msg" -ForegroundColor Yellow }
function Ok   { param($msg) Write-Host "[ OK ]  $msg" -ForegroundColor Green }

# Helper: run an external command and stop the script if it fails
function Invoke-Ext {
    param([string]$Description, [scriptblock]$Cmd)
    Info $Description
    & $Cmd
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[ERROR] '$Description' failed (exit $LASTEXITCODE). Stopping." -ForegroundColor Red
        exit $LASTEXITCODE
    }
}

# -- 0. Optional clean ---------------------------------------------------------
if ($Clean) {
    Warn "Deleting namespace '$NAMESPACE' for a clean re-deploy ..."
    kubectl delete namespace $NAMESPACE --ignore-not-found
    $deadline = (Get-Date).AddSeconds(60)
    while ((kubectl get namespace $NAMESPACE 2>$null) -and ((Get-Date) -lt $deadline)) {
        Start-Sleep -Seconds 3
        Info "  Waiting for namespace to disappear ..."
    }
}

# -- 1. Ensure Minikube is running ---------------------------------------------
Info "Checking Minikube status ..."
$mkStatus = minikube status --format="{{.Host}}" 2>$null
if ($mkStatus -notmatch "Running") {
    Info "Starting Minikube (4 CPUs, ${Memory}MB RAM, docker driver) ..."
    minikube start --cpus=4 --memory=$Memory --driver=docker
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[ERROR] minikube start failed. Try a lower -Memory value, e.g.:" -ForegroundColor Red
        Write-Host "        .\infra\deploy.ps1 -Memory 2048" -ForegroundColor Yellow
        exit 1
    }
}
Ok "Minikube is running."

# -- 2. Enable addons ----------------------------------------------------------
Info "Enabling metrics-server addon ..."
minikube addons enable metrics-server
if ($LASTEXITCODE -ne 0) { Warn "metrics-server addon failed - continuing anyway." }

Info "Enabling ingress addon ..."
minikube addons enable ingress 2>$null
# ingress is optional - don't fail if it doesn't exist on this driver

# -- 3. Point Docker at Minikube's daemon --------------------------------------
Info "Configuring Docker to use Minikube's daemon ..."
$envLines = minikube docker-env --shell powershell 2>$null
if ($LASTEXITCODE -ne 0 -or -not $envLines) {
    Write-Host "[ERROR] 'minikube docker-env' failed. Is Minikube running?" -ForegroundColor Red
    exit 1
}
# Filter to only lines that look like environment variable assignments
$validLines = $envLines | Where-Object { $_ -match '^\$Env:' }
if ($validLines) {
    Invoke-Expression ($validLines -join "`n")
    Ok "Docker daemon configured."
} else {
    Warn "No environment variables returned by minikube docker-env. Skipping."
}

# -- 4. Build target-app image -------------------------------------------------
Info "Building target-app Docker image ..."
docker build -t target-app:latest "$PROJECT_ROOT\target-app"
if ($LASTEXITCODE -ne 0) {
    Write-Host "[ERROR] docker build failed." -ForegroundColor Red
    exit 1
}

Info "Building metrics-collector Docker image ..."
docker build -t metrics-collector:latest "$PROJECT_ROOT\metrics-collector"
if ($LASTEXITCODE -ne 0) {
    Write-Host "[ERROR] metrics-collector docker build failed." -ForegroundColor Red
    exit 1
}

Info "Building ml-predictor Docker image ..."
docker build -t ml-predictor:latest "$PROJECT_ROOT\ml-predictor"
if ($LASTEXITCODE -ne 0) {
    Write-Host "[ERROR] ml-predictor docker build failed." -ForegroundColor Red
    exit 1
}

Info "Building api-server Docker image ..."
docker build -t api-server:latest "$PROJECT_ROOT\api-server"
if ($LASTEXITCODE -ne 0) {
    Write-Host "[ERROR] api-server docker build failed." -ForegroundColor Red
    exit 1
}

Ok "Images built: target-app:latest, metrics-collector:latest, ml-predictor:latest, api-server:latest"

# -- 5. Install kube-state-metrics ---------------------------------------------
Info "Installing kube-state-metrics v2.12.0 ..."
$KSM_URL = "https://github.com/kubernetes/kube-state-metrics/releases/download/v2.12.0/kube-state-metrics-v2.12.0.yaml"
kubectl apply -f $KSM_URL
if ($LASTEXITCODE -ne 0) { Warn "kube-state-metrics apply failed - it may already be installed. Continuing." }
else { Ok "kube-state-metrics applied." }

# -- 6. Apply namespace --------------------------------------------------------
Info "Applying namespace ..."
kubectl apply -f "$SCRIPT_DIR\namespace.yaml"
if ($LASTEXITCODE -ne 0) { Write-Host "[ERROR] namespace apply failed." -ForegroundColor Red; exit 1 }

# -- 7. Apply Prometheus -------------------------------------------------------
Info "Applying Prometheus ConfigMap ..."
kubectl apply -f "$SCRIPT_DIR\prometheus\prometheus-config.yaml"
if ($LASTEXITCODE -ne 0) { exit 1 }

Info "Applying Prometheus Deployment ..."
kubectl apply -f "$SCRIPT_DIR\prometheus\deployment.yaml"
if ($LASTEXITCODE -ne 0) { exit 1 }

# -- 8. Apply InfluxDB ---------------------------------------------------------
Info "Applying InfluxDB ..."
kubectl apply -f "$SCRIPT_DIR\influxdb\deployment.yaml"
if ($LASTEXITCODE -ne 0) { exit 1 }

# -- 9. Apply Grafana ----------------------------------------------------------
Info "Applying Grafana ..."
kubectl apply -f "$SCRIPT_DIR\grafana\deployment.yaml"
if ($LASTEXITCODE -ne 0) { exit 1 }

# -- 10. Apply metrics-collector -----------------------------------------------
Info "Applying metrics-collector ..."
kubectl apply -f "$SCRIPT_DIR\metrics-collector\deployment.yaml"
if ($LASTEXITCODE -ne 0) { exit 1 }

# -- 11. Apply ml-predictor ----------------------------------------------------
Info "Applying ml-predictor ..."
kubectl apply -f "$SCRIPT_DIR\ml-predictor\deployment.yaml"
if ($LASTEXITCODE -ne 0) { exit 1 }

# -- 12. Apply api-server --------------------------------------------------------
Info "Applying api-server ..."
kubectl apply -f "$SCRIPT_DIR\api-server\deployment.yaml"
if ($LASTEXITCODE -ne 0) { exit 1 }

# -- 13. Apply target-app ------------------------------------------------------
Info "Applying target-app ..."
kubectl apply -f "$PROJECT_ROOT\target-app\k8s\deployment.yaml"
kubectl apply -f "$PROJECT_ROOT\target-app\k8s\service.yaml"
kubectl apply -f "$PROJECT_ROOT\target-app\k8s\hpa.yaml"

Info "Creating grafana-dashboards ConfigMap from JSON ..."
$dashboardJson = "$SCRIPT_DIR\grafana\dashboards\autoscaler-overview.json"
$configmapYaml = kubectl create configmap grafana-dashboards `
    "--from-file=autoscaler-overview.json=$dashboardJson" `
    -n $NAMESPACE --dry-run=client -o yaml
if ($LASTEXITCODE -ne 0) { exit 1 }
$configmapYaml | kubectl apply -f -
if ($LASTEXITCODE -ne 0) {
    # Validation can fail against a local-only API - retry without validation
    Warn "Retrying ConfigMap apply with --validate=false ..."
    $configmapYaml | kubectl apply -f - --validate=false
}

# -- 14. Wait for Deployments to be ready --------------------------------------
Info "Waiting for Deployments to be ready (timeout: 3 min each) ..."
foreach ($deploy in @("prometheus", "influxdb", "grafana", "metrics-collector", "ml-predictor", "api-server", "target-app")) {
    Info "  Waiting for $deploy ..."
    kubectl rollout status "deployment/$deploy" -n $NAMESPACE --timeout=180s
    if ($LASTEXITCODE -ne 0) {
        Warn "$deploy not ready in time. Check: kubectl describe deployment $deploy -n $NAMESPACE"
    } else {
        Ok "  $deploy is ready."
    }
}

# -- 12. Print access URLs -----------------------------------------------------
$MINIKUBE_IP = minikube ip

Write-Host ""
Write-Host "================================================" -ForegroundColor Green
Write-Host "  Deployment complete!" -ForegroundColor Green
Write-Host "================================================" -ForegroundColor Green
Write-Host ""
Write-Host "  Target App   http://$($MINIKUBE_IP):30007" -ForegroundColor Cyan
Write-Host "  Prometheus   http://$($MINIKUBE_IP):30090" -ForegroundColor Cyan
Write-Host "  Grafana      http://$($MINIKUBE_IP):30030  (admin / autoscaler-admin)" -ForegroundColor Cyan
Write-Host "  API Server   http://$($MINIKUBE_IP):30080" -ForegroundColor Cyan
Write-Host "  InfluxDB     kubectl port-forward -n $NAMESPACE svc/influxdb-service 8086:8086" -ForegroundColor Cyan
Write-Host ""
Write-Host "  Quick smoke tests:" -ForegroundColor Yellow
Write-Host "    kubectl get pods -n $NAMESPACE" -ForegroundColor Yellow
Write-Host "    kubectl top pods  -n $NAMESPACE" -ForegroundColor Yellow
Write-Host "    kubectl get hpa   -n $NAMESPACE" -ForegroundColor Yellow
Write-Host ""

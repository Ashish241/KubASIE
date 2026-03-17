#!/usr/bin/env bash
# =============================================================================
# deploy.sh — Deploy the K8s Auto-Scaling Intelligence Engine to Minikube
# =============================================================================
# Usage:
#   bash infra/deploy.sh          # full deploy
#   bash infra/deploy.sh --clean  # delete namespace first, then full deploy
#
# Prerequisites: minikube, kubectl, docker (all on PATH)
# =============================================================================
set -euo pipefail

NAMESPACE="autoscaler"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

GREEN='\033[0;32m'; YELLOW='\033[1;33m'; CYAN='\033[0;36m'; NC='\033[0m'
info()  { echo -e "${CYAN}[INFO]${NC}  $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC}  $*"; }
ok()    { echo -e "${GREEN}[ OK ]${NC}  $*"; }

# ── 0. Optional clean ────────────────────────────────────────────────────────
if [[ "${1:-}" == "--clean" ]]; then
  warn "Deleting namespace ${NAMESPACE} for a clean re-deploy …"
  kubectl delete namespace "${NAMESPACE}" --ignore-not-found
  kubectl wait --for=delete namespace/"${NAMESPACE}" --timeout=60s 2>/dev/null || true
fi

# ── 1. Ensure Minikube is running ─────────────────────────────────────────────
info "Checking Minikube status …"
if ! minikube status --format='{{.Host}}' 2>/dev/null | grep -q "Running"; then
  info "Starting Minikube …"
  minikube start --cpus=4 --memory=6g --driver=docker
fi
ok "Minikube is running."

# ── 2. Enable required addons ─────────────────────────────────────────────────
info "Enabling Minikube addons …"
minikube addons enable metrics-server
minikube addons enable ingress 2>/dev/null || true   # nice-to-have
ok "Addons enabled."

# ── 3. Point Docker at Minikube's daemon ─────────────────────────────────────
info "Configuring Docker to use Minikube's daemon …"
eval "$(minikube docker-env)"

# ── 4. Build target-app image ────────────────────────────────────────────────
info "Building target-app Docker image …"
docker build -t target-app:latest "${PROJECT_ROOT}/target-app/"
ok "Image built: target-app:latest"

# ── 5. Install kube-state-metrics (in kube-system) ───────────────────────────
info "Installing kube-state-metrics …"
KSM_VERSION="v2.12.0"
KSM_URL="https://github.com/kubernetes/kube-state-metrics/releases/download/${KSM_VERSION}/kube-state-metrics-${KSM_VERSION}.yaml"
kubectl apply -f "${KSM_URL}" || warn "kube-state-metrics apply failed — it may already be installed."

# ── 6. Apply namespace ───────────────────────────────────────────────────────
info "Applying namespace …"
kubectl apply -f "${SCRIPT_DIR}/namespace.yaml"

# ── 7. Apply Prometheus ──────────────────────────────────────────────────────
info "Applying Prometheus config + deployment …"
kubectl apply -f "${SCRIPT_DIR}/prometheus/prometheus-config.yaml"
kubectl apply -f "${SCRIPT_DIR}/prometheus/deployment.yaml"

# ── 8. Apply InfluxDB ────────────────────────────────────────────────────────
info "Applying InfluxDB …"
kubectl apply -f "${SCRIPT_DIR}/influxdb/deployment.yaml"

# ── 9. Apply Grafana ─────────────────────────────────────────────────────────
info "Applying Grafana (deployment + datasource + dashboard provider) …"
kubectl apply -f "${SCRIPT_DIR}/grafana/deployment.yaml"

# Create/update the dashboard ConfigMap from the JSON file
info "Creating grafana-dashboards ConfigMap from JSON …"
kubectl create configmap grafana-dashboards \
  --from-file=autoscaler-overview.json="${SCRIPT_DIR}/grafana/dashboards/autoscaler-overview.json" \
  -n "${NAMESPACE}" \
  --dry-run=client -o yaml | kubectl apply -f -

# ── 10. Apply target-app ─────────────────────────────────────────────────────
info "Applying target-app (deployment + service + HPA) …"
kubectl apply -f "${PROJECT_ROOT}/target-app/k8s/deployment.yaml"
kubectl apply -f "${PROJECT_ROOT}/target-app/k8s/service.yaml"
kubectl apply -f "${PROJECT_ROOT}/target-app/k8s/hpa.yaml"

# ── 11. Wait for all Deployments to be ready ─────────────────────────────────
info "Waiting for all Deployments in namespace '${NAMESPACE}' to be ready (timeout: 3 min) …"
for deploy in prometheus influxdb grafana target-app; do
  info "  → waiting for ${deploy} …"
  kubectl rollout status deployment/"${deploy}" -n "${NAMESPACE}" --timeout=180s
  ok "    ${deploy} is ready."
done

# ── 12. Print access URLs ─────────────────────────────────────────────────────
MINIKUBE_IP=$(minikube ip)
echo ""
echo -e "${GREEN}════════════════════════════════════════════════${NC}"
echo -e "${GREEN} ✅  Deployment complete!${NC}"
echo -e "${GREEN}════════════════════════════════════════════════${NC}"
echo ""
echo -e "  ${CYAN}Target App${NC}     http://${MINIKUBE_IP}:30007"
echo -e "  ${CYAN}Prometheus${NC}     http://${MINIKUBE_IP}:30090"
echo -e "  ${CYAN}Grafana${NC}        http://${MINIKUBE_IP}:30030   (admin / autoscaler-admin)"
echo -e "  ${CYAN}InfluxDB${NC}       kubectl port-forward -n ${NAMESPACE} svc/influxdb-service 8086:8086"
echo ""
echo -e "  Run a quick smoke test:"
echo -e "    ${YELLOW}kubectl get pods -n ${NAMESPACE}${NC}"
echo -e "    ${YELLOW}kubectl top pods -n ${NAMESPACE}${NC}"
echo -e "    ${YELLOW}kubectl get hpa -n ${NAMESPACE}${NC}"
echo ""

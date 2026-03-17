/**
 * Centralized API helper — connects to the K8s Auto-Scaling API server.
 */

const API_BASE = import.meta.env.VITE_API_URL || '';

async function fetchJSON(endpoint, options = {}) {
  const res = await fetch(`${API_BASE}${endpoint}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`API ${res.status}: ${text}`);
  }
  return res.json();
}

export const api = {
  // Predictions
  getPredictions: (horizon = 15, model = 'prophet') =>
    fetchJSON(`/api/predictions?horizon=${horizon}&model=${model}`),

  // Metrics
  getCurrentMetrics: () => fetchJSON('/api/metrics/current'),
  getMetricsHistory: (field = 'request_rate', start = '-1h') =>
    fetchJSON(`/api/metrics/history?field=${field}&start=${start}`),

  // Scaling
  getScalingStatus: () => fetchJSON('/api/scaling/status'),
  getScalingHistory: () => fetchJSON('/api/scaling/history'),
  scalingOverride: (replicas, reason) =>
    fetchJSON('/api/scaling/override', {
      method: 'POST',
      body: JSON.stringify({ replicas, reason }),
    }),

  // Cost
  getCostSummary: () => fetchJSON('/api/cost/summary'),
  getCostHourly: () => fetchJSON('/api/cost/hourly'),

  // SLA
  getSlaStatus: () => fetchJSON('/api/sla/status'),
  getSlaTrend: () => fetchJSON('/api/sla/trend'),

  // Settings
  getSettings: () => fetchJSON('/api/settings'),
  updateSettings: (settings) =>
    fetchJSON('/api/settings', {
      method: 'PUT',
      body: JSON.stringify(settings),
    }),

  // Health
  getHealth: () => fetchJSON('/health'),
};

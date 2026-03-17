import { useState, useEffect } from 'react';
import { api } from '../api';
import StatCard from '../components/StatCard';
import PredictionChart from '../components/PredictionChart';
import CostChart from '../components/CostChart';
import SlaGauge from '../components/SlaGauge';
import MemoryIcon from '@mui/icons-material/Memory';
import StorageIcon from '@mui/icons-material/Storage';
import TrendingUpIcon from '@mui/icons-material/TrendingUp';
import AutorenewIcon from '@mui/icons-material/Autorenew';

export default function Overview() {
  const [metrics, setMetrics] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetch = () => {
      api.getCurrentMetrics().then(setMetrics).catch((e) => setError(e.message));
    };

    fetch();
    const interval = setInterval(fetch, 10000);
    return () => clearInterval(interval);
  }, []);

  return (
    <>
      <div className="page-header">
        <h2>Dashboard Overview</h2>
        <p>Real-time monitoring of the Kubernetes Auto-Scaling Intelligence Engine</p>
      </div>

      {error && (
        <div className="error-message" style={{ marginBottom: '1rem', color: 'var(--accent-danger)' }}>
          Failed to load metrics: {error}. Ensure the API server is running and accessible.
        </div>
      )}
      <div className="stat-grid">
        <StatCard label="CPU Utilization" value={metrics?.cpu_utilization ?? '—'} unit="%" icon={<MemoryIcon />} />
        <StatCard label="Memory" value={metrics?.memory_utilization ?? '—'} unit="%" icon={<StorageIcon />} />
        <StatCard label="Request Rate" value={metrics?.request_rate ?? '—'} unit="rps" icon={<TrendingUpIcon />} />
        <StatCard label="Replicas" value={metrics?.replica_count ?? '—'} icon={<AutorenewIcon />} />
      </div>

      <div className="grid-3">
        <PredictionChart compact />
        <SlaGauge compact />
      </div>

      <CostChart compact />
    </>
  );
}

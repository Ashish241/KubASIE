import { useState, useEffect } from 'react';
import { api } from '../api';
import SecurityIcon from '@mui/icons-material/Security';

export default function SlaGauge({ compact = false }) {
  const [status, setStatus] = useState(null);
  const [trend, setTrend] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    setError(null);
    api.getSlaStatus().then(setStatus).catch((e) => setError(e.message));
    if (!compact) api.getSlaTrend().then(setTrend).catch((e) => setError(e.message));
  }, [compact]);

  if (error) return <div className="loading" style={{ color: 'var(--accent-danger)' }}>Failed to load SLA data: {error}</div>;
  if (!status) return <div className="loading">Loading SLA…</div>;

  const pct = status.compliance_percent;
  const statusColor = pct >= 99.5 ? 'success' : pct >= 98 ? 'warning' : 'danger';
  const badgeClass = pct >= 99.5 ? 'badge-success' : pct >= 98 ? 'badge-warning' : 'badge-danger';

  return (
    <div className="chart-card">
      <div className="chart-header">
        <h3><SecurityIcon fontSize="small" style={{ verticalAlign: 'middle', marginRight: 6 }} /> SLA Compliance</h3>
        <span className={`badge ${badgeClass}`}>
          {status.status}
        </span>
      </div>

      <div className="gauge-container">
        <div className={`gauge-value ${statusColor}`}>{pct}%</div>
        <div className="gauge-label">Compliance Rate</div>
      </div>

      {!compact && (
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '1rem', marginTop: '0.5rem' }}>
          <div style={{ textAlign: 'center' }}>
            <div style={{ fontSize: '1.25rem', fontWeight: 700, color: 'var(--text-primary)' }}>
              {status.total_checks}
            </div>
            <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Total Checks</div>
          </div>
          <div style={{ textAlign: 'center' }}>
            <div style={{ fontSize: '1.25rem', fontWeight: 700, color: 'var(--accent-danger)' }}>
              {status.total_violations}
            </div>
            <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Violations</div>
          </div>
          <div style={{ textAlign: 'center' }}>
            <div style={{ fontSize: '1.25rem', fontWeight: 700, color: 'var(--accent-success)' }}>
              {status.recent_compliance_percent}%
            </div>
            <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Recent</div>
          </div>
        </div>
      )}

      {!compact && trend && (
        <div style={{
          marginTop: '1.5rem',
          padding: '1rem',
          background: 'var(--bg-tertiary)',
          borderRadius: 'var(--radius-md)',
        }}>
          <div style={{ fontSize: '0.8rem', fontWeight: 600, color: 'var(--text-muted)', marginBottom: '0.75rem', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
            Latency Trend
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '1rem' }}>
            <div>
              <div style={{ fontSize: '1.1rem', fontWeight: 700, color: 'var(--text-primary)' }}>{trend.avg_latency_ms}ms</div>
              <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>Avg Latency</div>
            </div>
            <div>
              <div style={{ fontSize: '1.1rem', fontWeight: 700, color: 'var(--text-primary)' }}>{trend.p99_latency_ms}ms</div>
              <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>P99 Latency</div>
            </div>
            <div>
              <div style={{ fontSize: '1.1rem', fontWeight: 700, color: 'var(--text-primary)' }}>{(trend.avg_error_rate * 100).toFixed(2)}%</div>
              <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>Error Rate</div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

import { useState, useEffect } from 'react';
import { api } from '../api';
import BoltIcon from '@mui/icons-material/Bolt';
import AdsClickIcon from '@mui/icons-material/AdsClick';
import HistoryIcon from '@mui/icons-material/History';

export default function ScalingPanel() {
  const [status, setStatus] = useState(null);
  const [history, setHistory] = useState([]);
  const [replicas, setReplicas] = useState(3);
  const [reason, setReason] = useState('');
  const [submitting, setSubmitting] = useState(false);

  const [error, setError] = useState(null);

  useEffect(() => {
    setError(null);
    api.getScalingStatus().then(setStatus).catch((e) => setError(e.message));
    api.getScalingHistory().then(r => setHistory(r.events || [])).catch((e) => setError(e.message));
  }, []);

  const handleOverride = async (e) => {
    e.preventDefault();
    setSubmitting(true);
    try {
      await api.scalingOverride(replicas, reason || 'Manual override');
      const updated = await api.getScalingHistory();
      setHistory(updated.events || []);
      setReason('');
    } catch (err) {
      alert('Override failed: ' + err.message);
    }
    setSubmitting(false);
  };

  return (
    <>
      {error && (
        <div style={{ marginBottom: '1rem', color: 'var(--accent-danger)' }}>
          ⚠ Failed to load scaling data: {error}
        </div>
      )}
      {/* HPA Status */}
      <div className="chart-card">
        <div className="chart-header">
          <h3><BoltIcon fontSize="small" style={{ verticalAlign: 'middle', marginRight: 6 }} /> HPA Status</h3>
          {status && (
            <span className="badge badge-success">Active</span>
          )}
        </div>

        {status ? (
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '1rem' }}>
            <div style={{ textAlign: 'center' }}>
              <div style={{ fontSize: '1.5rem', fontWeight: 700, color: 'var(--accent-primary)' }}>
                {status.hpa.current_replicas}
              </div>
              <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Current</div>
            </div>
            <div style={{ textAlign: 'center' }}>
              <div style={{ fontSize: '1.5rem', fontWeight: 700, color: 'var(--text-primary)' }}>
                {status.hpa.min_replicas}
              </div>
              <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Min</div>
            </div>
            <div style={{ textAlign: 'center' }}>
              <div style={{ fontSize: '1.5rem', fontWeight: 700, color: 'var(--text-primary)' }}>
                {status.hpa.max_replicas}
              </div>
              <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Max</div>
            </div>
            <div style={{ textAlign: 'center' }}>
              <div style={{ fontSize: '1.5rem', fontWeight: 700, color: 'var(--text-primary)' }}>
                {status.hpa.target_cpu_percent}%
              </div>
              <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Target CPU</div>
            </div>
          </div>
        ) : (
          <div className="loading">Loading…</div>
        )}
      </div>

      {/* Manual Override */}
      <div className="chart-card">
        <div className="chart-header">
          <h3><AdsClickIcon fontSize="small" style={{ verticalAlign: 'middle', marginRight: 6 }} /> Manual Override</h3>
        </div>
        <form onSubmit={handleOverride} style={{ display: 'flex', gap: '1rem', alignItems: 'flex-end', flexWrap: 'wrap' }}>
          <div className="form-group" style={{ marginBottom: 0, flex: '0 0 100px' }}>
            <label>Replicas</label>
            <input type="number" min={1} max={20} value={replicas}
              onChange={e => setReplicas(parseInt(e.target.value) || 1)} />
          </div>
          <div className="form-group" style={{ marginBottom: 0, flex: 1 }}>
            <label>Reason</label>
            <input type="text" value={reason} onChange={e => setReason(e.target.value)}
              placeholder="e.g., Pre-scale for launch event" />
          </div>
          <button type="submit" className="btn btn-primary" disabled={submitting}>
            {submitting ? 'Applying…' : 'Apply Override'}
          </button>
        </form>
      </div>

      {/* History */}
      <div className="chart-card">
        <div className="chart-header">
          <h3><HistoryIcon fontSize="small" style={{ verticalAlign: 'middle', marginRight: 6 }} /> Scaling History</h3>
        </div>
        {history.length === 0 ? (
          <div style={{ color: 'var(--text-muted)', fontSize: '0.85rem', padding: '1rem 0' }}>
            No scaling events recorded yet.
          </div>
        ) : (
          <table className="data-table">
            <thead>
              <tr>
                <th>Timestamp</th>
                <th>Action</th>
                <th>Replicas</th>
                <th>Reason</th>
              </tr>
            </thead>
            <tbody>
              {history.slice().reverse().map((evt, i) => (
                <tr key={i}>
                  <td>{new Date(evt.timestamp).toLocaleString()}</td>
                  <td><span className="badge badge-warning">{evt.action}</span></td>
                  <td style={{ fontWeight: 600 }}>{evt.target_replicas}</td>
                  <td>{evt.reason}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </>
  );
}

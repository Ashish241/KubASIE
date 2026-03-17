import { useState } from 'react';
import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, Legend
} from 'recharts';
import { api } from '../api';
import InsightsIcon from '@mui/icons-material/Insights';

export default function PredictionChart({ compact = false }) {
  const [horizon, setHorizon] = useState(15);
  const [data, setData] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const fetchPredictions = async (h) => {
    setLoading(true);
    setError(null);
    try {
      const res = await api.getPredictions(h);
      setData(
        (res.predictions || []).map((p, i) => ({
          time: p.timestamp ? new Date(p.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : `+${i + 1}m`,
          predicted: p.predicted_request_rate,
          lower: p.lower_bound,
          upper: p.upper_bound,
        }))
      );
    } catch (e) {
      setError(e.message);
      setData([]);
    }
    setLoading(false);
  };

  useState(() => { fetchPredictions(horizon); }, []);

  const handleHorizon = (h) => {
    setHorizon(h);
    fetchPredictions(h);
  };

  const height = compact ? 250 : 350;

  return (
    <div className="chart-card">
      <div className="chart-header">
        <h3><InsightsIcon fontSize="small" style={{ verticalAlign: 'middle', marginRight: 6 }} /> Traffic Predictions</h3>
        {!compact && (
          <div className="chart-controls">
            {[15, 30, 60].map((h) => (
              <button
                key={h}
                className={horizon === h ? 'active' : ''}
                onClick={() => handleHorizon(h)}
              >
                {h}m
              </button>
            ))}
          </div>
        )}
      </div>

      {loading && <div className="loading">Loading predictions…</div>}
      {error && <div className="loading" style={{ color: 'var(--accent-danger)' }}>⚠ {error}</div>}

      {!loading && !error && data.length > 0 && (
        <ResponsiveContainer width="100%" height={height}>
          <AreaChart data={data} margin={{ top: 5, right: 20, left: 0, bottom: 5 }}>
            <defs>
              <linearGradient id="predGrad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="var(--chart-line-1)" stopOpacity={0.3} />
                <stop offset="100%" stopColor="var(--chart-line-1)" stopOpacity={0.02} />
              </linearGradient>
              <linearGradient id="bandGrad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="var(--chart-line-1)" stopOpacity={0.08} />
                <stop offset="100%" stopColor="var(--chart-line-1)" stopOpacity={0.02} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="var(--chart-grid)" />
            <XAxis dataKey="time" tick={{ fill: 'var(--text-muted)', fontSize: 11 }} />
            <YAxis tick={{ fill: 'var(--text-muted)', fontSize: 11 }} />
            <Tooltip
              contentStyle={{
                background: 'var(--bg-secondary)',
                border: '1px solid var(--border-color)',
                borderRadius: '8px',
                color: 'var(--text-primary)',
                fontSize: '0.8rem',
              }}
            />
            {!compact && <Legend />}
            <Area type="monotone" dataKey="upper" stroke="none" fill="url(#bandGrad)" name="Upper Bound" />
            <Area type="monotone" dataKey="lower" stroke="none" fill="url(#bandGrad)" name="Lower Bound" />
            <Area type="monotone" dataKey="predicted" stroke="var(--chart-line-1)" strokeWidth={2} fill="url(#predGrad)" name="Predicted RPS" />
          </AreaChart>
        </ResponsiveContainer>
      )}
    </div>
  );
}

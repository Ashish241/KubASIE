import { useState, useEffect } from 'react';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, PieChart, Pie, Cell
} from 'recharts';
import { api } from '../api';
import AttachMoneyIcon from '@mui/icons-material/AttachMoney';

export default function CostChart({ compact = false }) {
  const [summary, setSummary] = useState(null);
  const [hourly, setHourly] = useState([]);
  const [error, setError] = useState(null);

  useEffect(() => {
    setError(null);
    api.getCostSummary().then(setSummary).catch((e) => setError(e.message));
    if (!compact) api.getCostHourly().then(r => setHourly(r.hours || [])).catch((e) => setError(e.message));
  }, [compact]);

  if (error) return <div className="loading" style={{ color: 'var(--accent-danger)' }}>Failed to load cost data: {error}</div>;
  if (!summary) return <div className="loading">Loading cost data…</div>;

  const donutData = [
    { name: 'Efficient', value: summary.efficiency_percent },
    { name: 'Overhead', value: 100 - summary.efficiency_percent },
  ];
  const COLORS = ['var(--accent-success)', 'var(--border-color)'];

  return (
    <div className="chart-card">
      <div className="chart-header">
        <h3><AttachMoneyIcon fontSize="small" style={{ verticalAlign: 'middle', marginRight: 6 }} /> Cost Efficiency</h3>
      </div>

      <div style={{ display: 'flex', alignItems: 'center', gap: '2rem', flexWrap: 'wrap' }}>
        <div style={{ width: compact ? 140 : 180, height: compact ? 140 : 180 }}>
          <ResponsiveContainer>
            <PieChart>
              <Pie
                data={donutData}
                cx="50%"
                cy="50%"
                innerRadius="65%"
                outerRadius="90%"
                paddingAngle={3}
                dataKey="value"
                strokeWidth={0}
              >
                {donutData.map((_, i) => (
                  <Cell key={i} fill={COLORS[i]} />
                ))}
              </Pie>
            </PieChart>
          </ResponsiveContainer>
        </div>

        <div>
          <div style={{ fontSize: '2rem', fontWeight: 800, color: 'var(--accent-success)' }}>
            {summary.efficiency_percent}%
          </div>
          <div style={{ color: 'var(--text-muted)', fontSize: '0.8rem', marginBottom: '0.75rem' }}>
            Resource Efficiency
          </div>
          <div style={{ color: 'var(--text-secondary)', fontSize: '0.85rem' }}>
            Saved <strong style={{ color: 'var(--accent-primary)' }}>${summary.total_savings_usd}</strong> ({summary.period})
          </div>
          <div style={{ color: 'var(--text-muted)', fontSize: '0.8rem', marginTop: '0.25rem' }}>
            Avg {summary.avg_replicas} / {summary.avg_max_replicas} max replicas
          </div>
        </div>
      </div>

      {!compact && hourly.length > 0 && (
        <div style={{ marginTop: '1.5rem' }}>
          <h4 style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', marginBottom: '1rem' }}>
            Hourly Savings Breakdown
          </h4>
          <ResponsiveContainer width="100%" height={200}>
            <BarChart data={hourly}>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--chart-grid)" />
              <XAxis dataKey="hour" tick={{ fill: 'var(--text-muted)', fontSize: 10 }}
                tickFormatter={(v) => v.split('T')[1] || v} />
              <YAxis tick={{ fill: 'var(--text-muted)', fontSize: 10 }} />
              <Tooltip
                contentStyle={{
                  background: 'var(--bg-secondary)',
                  border: '1px solid var(--border-color)',
                  borderRadius: '8px',
                  color: 'var(--text-primary)',
                  fontSize: '0.8rem',
                }}
              />
              <Bar dataKey="savings_usd" fill="var(--chart-line-1)" radius={[4, 4, 0, 0]} name="Savings ($)" />
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  );
}

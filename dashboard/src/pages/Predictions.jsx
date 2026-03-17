import PredictionChart from '../components/PredictionChart';
import { useState, useEffect } from 'react';
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer
} from 'recharts';
import { api } from '../api';
import TrendingUpIcon from '@mui/icons-material/TrendingUp';

export default function Predictions() {
  const [history, setHistory] = useState([]);

  useEffect(() => {
    api.getMetricsHistory('request_rate', '-1h').then((res) => {
      setHistory(
        (res.data || []).map((d) => ({
          time: d.time.split('T')[1]?.replace('Z', '') || d.time,
          value: d.value,
        }))
      );
    }).catch(() => {});
  }, []);

  return (
    <>
      <div className="page-header">
        <h2>Traffic Predictions</h2>
        <p>ML-powered traffic forecast using Prophet model</p>
      </div>

      <PredictionChart />

      <div className="chart-card">
        <div className="chart-header">
          <h3><TrendingUpIcon fontSize="small" style={{ verticalAlign: 'middle', marginRight: 6 }} /> Historical Request Rate (Last Hour)</h3>
        </div>
        {history.length > 0 ? (
          <ResponsiveContainer width="100%" height={280}>
            <LineChart data={history} margin={{ top: 5, right: 20, left: 0, bottom: 5 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--chart-grid)" />
              <XAxis dataKey="time" tick={{ fill: 'var(--text-muted)', fontSize: 10 }} />
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
              <Line type="monotone" dataKey="value" stroke="var(--chart-line-2)" strokeWidth={2} dot={false} name="Actual RPS" />
            </LineChart>
          </ResponsiveContainer>
        ) : (
          <div className="loading">Loading historical data…</div>
        )}
      </div>
    </>
  );
}

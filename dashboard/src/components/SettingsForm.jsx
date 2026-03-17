import { useState, useEffect } from 'react';
import { api } from '../api';
import SettingsIcon from '@mui/icons-material/Settings';

export default function SettingsForm() {
  const [settings, setSettings] = useState(null);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    api.getSettings().then(setSettings).catch(() => {});
  }, []);

  const handleChange = (key, value) => {
    setSettings(prev => ({ ...prev, [key]: value }));
    setSaved(false);
  };

  const handleSave = async (e) => {
    e.preventDefault();
    setSaving(true);
    try {
      const res = await api.updateSettings(settings);
      setSettings(res.settings);
      setSaved(true);
      setTimeout(() => setSaved(false), 2500);
    } catch (err) {
      alert('Save failed: ' + err.message);
    }
    setSaving(false);
  };

  if (!settings) return <div className="loading">Loading settings…</div>;

  return (
    <div className="chart-card">
      <div className="chart-header">
        <h3><SettingsIcon fontSize="small" style={{ verticalAlign: 'middle', marginRight: 6 }} /> Engine Configuration</h3>
        {saved && <span className="badge badge-success">✓ Saved</span>}
      </div>

      <form onSubmit={handleSave}>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0 2rem' }}>
          <div className="form-group">
            <label>SLA Latency Threshold (ms)</label>
            <input type="number" value={settings.sla_latency_threshold_ms}
              onChange={e => handleChange('sla_latency_threshold_ms', parseFloat(e.target.value))} />
          </div>
          <div className="form-group">
            <label>SLA Error Rate Threshold</label>
            <input type="number" step="0.001" value={settings.sla_error_rate_threshold}
              onChange={e => handleChange('sla_error_rate_threshold', parseFloat(e.target.value))} />
          </div>
          <div className="form-group">
            <label>Reactive Weight (0-1)</label>
            <input type="number" step="0.1" min="0" max="1" value={settings.reactive_weight}
              onChange={e => handleChange('reactive_weight', parseFloat(e.target.value))} />
          </div>
          <div className="form-group">
            <label>Predictive Weight (0-1)</label>
            <input type="number" step="0.1" min="0" max="1" value={settings.predictive_weight}
              onChange={e => handleChange('predictive_weight', parseFloat(e.target.value))} />
          </div>
          <div className="form-group">
            <label>Cooldown (seconds)</label>
            <input type="number" min="0" value={settings.cooldown_seconds}
              onChange={e => handleChange('cooldown_seconds', parseInt(e.target.value))} />
          </div>
        </div>

        <div style={{ display: 'flex', gap: '0.75rem', marginTop: '0.5rem' }}>
          <button type="submit" className="btn btn-primary" disabled={saving}>
            {saving ? 'Saving…' : 'Save Settings'}
          </button>
          <button type="button" className="btn btn-secondary" onClick={() => {
            api.getSettings().then(setSettings);
            setSaved(false);
          }}>
            Reset
          </button>
        </div>
      </form>
    </div>
  );
}

export default function StatCard({ label, value, unit, icon }) {
  return (
    <div className="stat-card">
      <div className="stat-label">{label}</div>
      <div className="stat-value">
        {value}
        {unit && <span className="stat-unit">{unit}</span>}
      </div>
      {icon && <span className="stat-icon">{icon}</span>}
    </div>
  );
}

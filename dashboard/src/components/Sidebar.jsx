import { NavLink } from 'react-router-dom';
import BarChartIcon from '@mui/icons-material/BarChart';
import InsightsIcon from '@mui/icons-material/Insights';
import BoltIcon from '@mui/icons-material/Bolt';
import AttachMoneyIcon from '@mui/icons-material/AttachMoney';
import SecurityIcon from '@mui/icons-material/Security';
import SettingsIcon from '@mui/icons-material/Settings';

const navItems = [
  { to: '/', icon: <BarChartIcon fontSize="small" />, label: 'Overview' },
  { to: '/predictions', icon: <InsightsIcon fontSize="small" />, label: 'Predictions' },
  { to: '/scaling', icon: <BoltIcon fontSize="small" />, label: 'Scaling' },
  { to: '/cost', icon: <AttachMoneyIcon fontSize="small" />, label: 'Cost' },
  { to: '/sla', icon: <SecurityIcon fontSize="small" />, label: 'SLA' },
  { to: '/settings', icon: <SettingsIcon fontSize="small" />, label: 'Settings' },
];

export default function Sidebar({ theme, onToggleTheme, isCollapsed, onToggleCollapse }) {
  return (
    <aside className="sidebar">
      <div className="sidebar-brand">
        <div className="brand-logo-container">
          <img src="/logo.svg" alt="KubASIE Logo" className="brand-logo" />
        </div>
        {!isCollapsed && (
          <div className="brand-text">
            <h1>KubASIE</h1>
            <span>Kubernetes Auto-Scaling Intelligence Engine</span>
          </div>
        )}
        <button
          className="collapse-btn"
          onClick={onToggleCollapse}
          title={isCollapsed ? "Expand Sidebar" : "Collapse Sidebar"}
        >
          {isCollapsed ? '»' : '«'}
        </button>
      </div>

      <ul className="sidebar-nav">
        {navItems.map((item) => (
          <li key={item.to}>
            <NavLink
              to={item.to}
              end={item.to === '/'}
              className={({ isActive }) => isActive ? 'active' : ''}
              title={isCollapsed ? item.label : undefined}
            >
              <span className="nav-icon">{item.icon}</span>
              {!isCollapsed && <span className="nav-label">{item.label}</span>}
            </NavLink>
          </li>
        ))}
      </ul>

      <div className="sidebar-footer">
        <button className="theme-toggle" onClick={onToggleTheme} title="Toggle Theme">
          <div className="theme-toggle-track" />
          {!isCollapsed && (
            <span className="theme-toggle-label">
              {theme === 'dark' ? ' Dark Mode' : ' Light Mode'}
            </span>
          )}
        </button>
      </div>
    </aside>
  );
}

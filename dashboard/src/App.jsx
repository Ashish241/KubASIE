import { useState, useEffect } from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import Sidebar from './components/Sidebar';
import Overview from './pages/Overview';
import Predictions from './pages/Predictions';
import Scaling from './pages/Scaling';
import Cost from './pages/Cost';
import Sla from './pages/Sla';
import Settings from './pages/Settings';

export default function App() {
  const [theme, setTheme] = useState(() => {
    return localStorage.getItem('autoscale-theme') || 'dark';
  });

  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(() => {
    return localStorage.getItem('autoscale-sidebar') === 'true';
  });

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('autoscale-theme', theme);
  }, [theme]);

  useEffect(() => {
    localStorage.setItem('autoscale-sidebar', isSidebarCollapsed);
  }, [isSidebarCollapsed]);

  const toggleTheme = () => {
    setTheme((prev) => (prev === 'dark' ? 'light' : 'dark'));
  };

  const toggleSidebar = () => {
    setIsSidebarCollapsed((prev) => !prev);
  }

  return (
    <BrowserRouter>
      <div className={`app-layout ${isSidebarCollapsed ? 'sidebar-collapsed' : ''}`}>
        <Sidebar 
          theme={theme} 
          onToggleTheme={toggleTheme} 
          isCollapsed={isSidebarCollapsed}
          onToggleCollapse={toggleSidebar}
        />
        <main className="main-content">
          <Routes>
            <Route path="/" element={<Overview />} />
            <Route path="/predictions" element={<Predictions />} />
            <Route path="/scaling" element={<Scaling />} />
            <Route path="/cost" element={<Cost />} />
            <Route path="/sla" element={<Sla />} />
            <Route path="/settings" element={<Settings />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  );
}

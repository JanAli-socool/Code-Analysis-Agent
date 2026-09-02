import React, { useState, useEffect } from 'react';
import { Routes, Route, Link, useNavigate, useLocation } from 'react-router-dom';
import {
  LayoutDashboard, GitBranch, FileCode, Shield, 
  BarChart2, Settings, ChevronLeft, ChevronRight,
  Menu, X, Bell, User, LogOut, Search,
  RefreshCw, Download, Filter, Plus
} from 'lucide-react';
import axios from 'axios';
import Dashboard from './pages/Dashboard';
import Repositories from './pages/Repositories';
import RepositoryDetail from './pages/RepositoryDetail';
import Policies from './pages/Policies';
import Reports from './pages/Reports';
import SettingsPage from './pages/Settings';

const API_BASE = process.env.REACT_APP_API_URL || 'http://localhost:8000';

const api = axios.create({
  baseURL: API_BASE,
  timeout: 30000,
});

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('auth_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

const navItems = [
  { path: '/', icon: LayoutDashboard, label: 'Dashboard' },
  { path: '/repositories', icon: GitBranch, label: 'Repositories' },
  { path: '/policies', icon: Shield, label: 'Policies' },
  { path: '/reports', icon: BarChart2, label: 'Reports' },
  { path: '/settings', icon: Settings, label: 'Settings' },
];

function Sidebar({ isOpen, onToggle }) {
  const location = useLocation();
  
  return (
    <aside className={`sidebar ${isOpen ? 'open' : ''}`}>
      <div className="sidebar-header">
        <Link to="/" className="sidebar-logo">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M9 18l6-6-6-6"/>
            <path d="M6 9l6 6 6-6"/>
          </svg>
          <span>Code Analysis</span>
        </Link>
      </div>
      <nav className="sidebar-nav" role="navigation" aria-label="Main navigation">
        {navItems.map((item) => {
          const isActive = location.pathname === item.path || 
            (item.path !== '/' && location.pathname.startsWith(item.path));
          return (
            <Link
              key={item.path}
              to={item.path}
              className={`nav-item ${isActive ? 'active' : ''}`}
              onClick={onToggle}
            >
              <item.icon size={20} />
              <span>{item.label}</span>
            </Link>
          );
        })}
      </nav>
      <div className="sidebar-footer">
        <div style={{fontSize: '0.75rem', color: 'var(--text-muted)'}}>
          v1.0.0
        </div>
      </div>
    </aside>
  );
}

function Header({ onMenuClick, title }) {
  return (
    <header className="header">
      <div className="header-left">
        <button className="header-btn" onClick={onMenuClick} aria-label="Toggle menu">
          <Menu size={24} />
        </button>
        <div>
          <h1 className="page-title">{title}</h1>
        </div>
      </div>
      <div className="header-right">
        <button className="header-btn" aria-label="Search">
          <Search size={20} />
        </button>
        <button className="header-btn" aria-label="Notifications">
          <Bell size={20} />
        </button>
        <button className="header-btn" aria-label="Refresh">
          <RefreshCw size={20} />
        </button>
        <div className="user-menu">
          <div className="user-avatar">JD</div>
          <span className="user-name">John Doe</span>
          <ChevronRight size={16} />
        </div>
      </div>
    </header>
  );
}

function Layout({ children }) {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const location = useLocation();
  const navigate = useNavigate();
  
  const pageTitles = {
    '/': 'Dashboard',
    '/repositories': 'Repositories',
    '/repositories/new': 'New Analysis',
    '/policies': 'Policies',
    '/reports': 'Reports',
    '/settings': 'Settings',
  };
  
  const title = pageTitles[location.pathname] || 'Dashboard';
  
  return (
    <div className="dashboard">
      <Sidebar isOpen={sidebarOpen} onToggle={() => setSidebarOpen(false)} />
      <div className="main-content">
        <Header onMenuClick={() => setSidebarOpen(true)} title={title} />
        <main className="content">
          {children}
        </main>
      </div>
    </div>
  );
}

function App() {
  return (
    <Layout>
      <Routes>
        <Route path="/" element={<Dashboard />} />
        <Route path="/repositories" element={<Repositories />} />
        <Route path="/repositories/:id" element={<RepositoryDetail />} />
        <Route path="/policies" element={<Policies />} />
        <Route path="/reports" element={<Reports />} />
        <Route path="/settings" element={<SettingsPage />} />
      </Routes>
    </Layout>
  );
}

export default App;// Trigger Vercel deploy

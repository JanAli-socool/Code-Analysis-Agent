import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { Search, Filter, Plus, Code, Database, TrendingUp, AlertTriangle, CheckCircle, MoreVertical, Download, RefreshCw } from 'lucide-react';
import axios from 'axios';

const API_BASE = process.env.REACT_APP_API_URL || 'http://localhost:8000';

function Repositories() {
  const [repos, setRepos] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [riskFilter, setRiskFilter] = useState('all');
  const [sortBy, setSortBy] = useState('name');
  const [sortOrder, setSortOrder] = useState('asc');

  useEffect(() => {
    fetchRepositories();
  }, []);

  const fetchRepositories = async () => {
    try {
      setLoading(true);
      await new Promise(resolve => setTimeout(resolve, 500));
      
      // Mock data
      setRepos([
        { id: 1, name: 'payment-service', language: 'Python', lastAnalyzed: '2024-03-15', score: 85, risk: 'low', status: 'completed', findings: { critical: 0, high: 1, medium: 3, low: 5 } },
        { id: 2, name: 'user-api', language: 'JavaScript', lastAnalyzed: '2024-03-14', score: 72, risk: 'medium', status: 'completed', findings: { critical: 0, high: 3, medium: 8, low: 12 } },
        { id: 3, name: 'auth-service', language: 'Go', lastAnalyzed: '2024-03-13', score: 58, risk: 'high', status: 'completed', findings: { critical: 2, high: 5, medium: 10, low: 8 } },
        { id: 4, name: 'notification-service', language: 'TypeScript', lastAnalyzed: '2024-03-12', score: 91, risk: 'low', status: 'completed', findings: { critical: 0, high: 0, medium: 1, low: 2 } },
        { id: 5, name: 'order-service', language: 'Java', lastAnalyzed: '2024-03-11', score: 63, risk: 'high', status: 'completed', findings: { critical: 1, high: 4, medium: 7, low: 9 } },
        { id: 6, name: 'inventory-api', language: 'Python', lastAnalyzed: '2024-03-10', score: 79, risk: 'medium', status: 'completed', findings: { critical: 0, high: 2, medium: 4, low: 6 } },
        { id: 7, name: 'analytics-engine', language: 'Rust', lastAnalyzed: '2024-03-09', score: 88, risk: 'low', status: 'completed', findings: { critical: 0, high: 1, medium: 2, low: 3 } },
        { id: 8, name: 'gateway-service', language: 'Go', lastAnalyzed: '2024-03-08', score: 74, risk: 'medium', status: 'completed', findings: { critical: 0, high: 3, medium: 6, low: 8 } },
      ]);
      setLoading(false);
    } catch (err) {
      console.error('Failed to fetch repositories:', err);
      setLoading(false);
    }
  };

  const filteredRepos = repos
    .filter(r => {
      if (search && !r.name.toLowerCase().includes(search.toLowerCase())) return false;
      if (riskFilter !== 'all' && r.risk !== riskFilter) return false;
      return true;
    })
    .sort((a, b) => {
      const aVal = a[sortBy];
      const bVal = b[sortBy];
      if (aVal < bVal) return sortOrder === 'asc' ? -1 : 1;
      if (aVal > bVal) return sortOrder === 'asc' ? 1 : -1;
      return 0;
    });

  const riskColors = {
    low: 'badge-success',
    medium: 'badge-warning',
    high: 'badge-danger',
    critical: 'badge-danger',
  };

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px' }}>
        <div>
          <h2 style={{ fontSize: '1.5rem', fontWeight: 600, marginBottom: '4px' }}>Repositories</h2>
          <p style={{ color: 'var(--text-muted)' }}>Manage and analyze your code repositories</p>
        </div>
        <Link to="/repositories/new" className="btn btn-primary">
          <Plus size={18} />
          New Analysis
        </Link>
      </div>

      <div className="card" style={{ marginBottom: '24px' }}>
        <div className="card-content" style={{ padding: '20px' }}>
          <div style={{ display: 'flex', gap: '16px', flexWrap: 'wrap', alignItems: 'center' }}>
            <div style={{ flex: 1, minWidth: '250px', position: 'relative' }}>
              <Search size={18} style={{ position: 'absolute', left: '12px', top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)' }} />
              <input
                type="text"
                placeholder="Search repositories..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="form-input"
                style={{ paddingLeft: '40px' }}
              />
            </div>
            <div style={{ display: 'flex', gap: '12px' }}>
              <select
                value={riskFilter}
                onChange={(e) => setRiskFilter(e.target.value)}
                className="form-input form-select"
                style={{ minWidth: '150px' }}
              >
                <option value="all">All Risk Levels</option>
                <option value="low">Low</option>
                <option value="medium">Medium</option>
                <option value="high">High</option>
                <option value="critical">Critical</option>
              </select>
              <select
                value={sortBy}
                onChange={(e) => setSortBy(e.target.value)}
                className="form-input form-select"
                style={{ minWidth: '150px' }}
              >
                <option value="name">Name</option>
                <option value="score">Score</option>
                <option value="risk">Risk Level</option>
                <option value="lastAnalyzed">Last Analyzed</option>
              </select>
              <button
                onClick={() => setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc')}
                className="btn btn-secondary btn-sm"
                aria-label="Toggle sort order"
              >
                {sortOrder === 'asc' ? <TrendingUp size={16} /> : <TrendingDown size={16} />}
              </button>
            </div>
          </div>
        </div>
      </div>

      <div className="card">
        <div className="table-container">
          <table className="table">
            <thead>
              <tr>
                <th>Repository</th>
                <th>Language</th>
                <th>Last Analyzed</th>
                <th>Score</th>
                <th>Risk Level</th>
                <th>Findings</th>
                <th>Status</th>
                <th style={{width: '60px'}}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr>
                  <td colSpan={8} style={{textAlign: 'center', padding: '48px'}}>
                    <div className="loading"><div className="spinner"></div></div>
                  </td>
                </tr>
              ) : filteredRepos.length === 0 ? (
                <tr>
                  <td colSpan={8} style={{textAlign: 'center', padding: '48px'}}>
                    <div className="empty-state">
                      <Database size={48} />
                      <h3>No repositories found</h3>
                      <p>Try adjusting your filters or add a new repository</p>
                    </div>
                  </td>
                </tr>
              ) : (
                filteredRepos.map((repo) => (
                  <tr key={repo.id}>
                    <td>
                      <Link to={`/repositories/${repo.id}`} style={{color: 'inherit', textDecoration: 'none', fontWeight: 500}}>
                        <Code size={16} style={{marginRight: '8px', verticalAlign: 'middle'}} />
                        {repo.name}
                      </Link>
                    </td>
                    <td>
                      <span style={{background: 'var(--surface-hover)', padding: '4px 10px', borderRadius: '20px', fontSize: '0.75rem', fontWeight: 500}}>
                        {repo.language}
                      </span>
                    </td>
                    <td style={{color: 'var(--text-secondary)', fontSize: '0.85rem', whiteSpace: 'nowrap'}}>
                      {repo.lastAnalyzed}
                    </td>
                    <td>
                      <span style={{fontWeight: 600, fontSize: '1rem', color: repo.score >= 80 ? 'var(--success)' : repo.score >= 60 ? 'var(--warning)' : 'var(--danger)'}}>
                        {repo.score}
                      </span>
                    </td>
                    <td>
                      <span className={`badge ${riskColors[repo.risk]}`}>
                        {repo.risk.charAt(0).toUpperCase() + repo.risk.slice(1)}
                      </span>
                    </td>
                    <td style={{fontSize: '0.85rem', color: 'var(--text-secondary)'}}>
                      <span style={{color: 'var(--danger)'}}>{repo.findings.critical}</span> /
                      <span style={{color: 'var(--warning)'}}>{repo.findings.high}</span> /
                      <span style={{color: 'var(--info)'}}>{repo.findings.medium}</span> /
                      <span style={{color: 'var(--text-muted)'}}>{repo.findings.low}</span>
                    </td>
                    <td>
                      <span className={`badge badge-${repo.status === 'completed' ? 'success' : 'info'}`}>
                        {repo.status}
                      </span>
                    </td>
                    <td>
                      <div style={{display: 'flex', gap: '4px'}}>
                        <Link to={`/repositories/${repo.id}`} className="btn btn-icon btn-secondary" aria-label="View details">
                          <Code size={16} />
                        </Link>
                        <button className="btn btn-icon btn-secondary" aria-label="Download report">
                          <Download size={16} />
                        </button>
                        <button className="btn btn-icon btn-secondary" aria-label="Re-analyze">
                          <RefreshCw size={16} />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

export default Repositories;
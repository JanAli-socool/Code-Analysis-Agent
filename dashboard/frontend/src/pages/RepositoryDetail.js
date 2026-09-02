import React, { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { ArrowLeft, AlertTriangle, CheckCircle, Shield, Code, FileText, Clock, TrendingUp, Download, RefreshCw, ChevronRight, Filter, Search } from 'lucide-react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, PieChart, Pie, Cell } from 'recharts';

function RepositoryDetail() {
  const { id } = useParams();
  const [repo, setRepo] = useState(null);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState('overview');
  const [findingsFilter, setFindingsFilter] = useState('all');

  useEffect(() => {
    fetchRepoData();
  }, [id]);

  const fetchRepoData = async () => {
    await new Promise(resolve => setTimeout(resolve, 300));
    setRepo({
      id: parseInt(id),
      name: 'payment-service',
      language: 'Python',
      description: 'Core payment processing microservice',
      lastAnalyzed: '2024-03-15',
      score: 85,
      risk: 'low',
      status: 'completed',
      linesOfCode: 12543,
      filesCount: 142,
      commitHash: 'a1b2c3d4e5f6',
      branch: 'main',
      findings: [
        { id: 1, category: 'security', severity: 'high', title: 'Hardcoded API Key', message: 'API key found in config.py', file: 'config.py', line: 42, recommendation: 'Use environment variables' },
        { id: 2, category: 'complexity', severity: 'medium', title: 'High Cyclomatic Complexity', message: 'Function process_payment has CC of 18', file: 'payment.py', line: 120, recommendation: 'Refactor into smaller functions' },
        { id: 3, category: 'testing', severity: 'medium', title: 'Low Test Coverage', message: 'Module payment has 45% coverage', file: 'payment.py', recommendation: 'Add unit tests for edge cases' },
        { id: 4, category: 'dependencies', severity: 'low', title: 'Outdated Dependency', message: 'requests 2.25.1 is outdated', file: 'requirements.txt', line: 3, recommendation: 'Update to 2.31.0' },
        { id: 5, category: 'architecture', severity: 'low', title: 'Circular Dependency', message: 'Circular import between models and services', file: 'models/__init__.py', recommendation: 'Restructure imports' },
      ],
      categoryScores: [
        { category: 'Security', score: 78, weight: 3.0 },
        { category: 'Complexity', score: 82, weight: 2.0 },
        { category: 'Testing', score: 72, weight: 2.0 },
        { category: 'Architecture', score: 88, weight: 2.0 },
        { category: 'Maintainability', score: 85, weight: 1.5 },
        { category: 'Dependencies', score: 90, weight: 1.0 },
        { category: 'Documentation', score: 80, weight: 0.5 },
        { category: 'Git History', score: 92, weight: 0.5 },
      ],
      metrics: {
        totalFindings: 45,
        critical: 0,
        high: 2,
        medium: 12,
        low: 31,
      }
    });
    setLoading(false);
  };

  if (loading) {
    return <div className="loading"><div className="spinner"></div></div>;
  }

  if (!repo) {
    return <div className="empty-state"><h3>Repository not found</h3></div>;
  }

  const riskColors = { low: 'badge-success', medium: 'badge-warning', high: 'badge-danger', critical: 'badge-danger' };
  const severityColors = { critical: 'badge-danger', high: 'badge-danger', medium: 'badge-warning', low: 'badge-success', info: 'badge-info' };

  const filteredFindings = repo.findings.filter(f => 
    findingsFilter === 'all' || f.severity === findingsFilter || f.category === findingsFilter
  );

  const tabs = [
    { id: 'overview', label: 'Overview', icon: <Code size={16} /> },
    { id: 'findings', label: 'Findings', icon: <AlertTriangle size={16} /> },
    { id: 'metrics', label: 'Metrics', icon: <TrendingUp size={16} /> },
    { id: 'sbom', label: 'SBOM', icon: <Shield size={16} /> },
  ];

  return (
    <div>
      <div style={{ display: 'flex', alignItems: 'center', gap: '16px', marginBottom: '24px' }}>
        <Link to="/repositories" className="btn btn-secondary btn-sm">
          <ArrowLeft size={16} />
          Back
        </Link>
        <div style={{ flex: 1 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '8px' }}>
            <h1 style={{ fontSize: '1.75rem', fontWeight: 700 }}>{repo.name}</h1>
            <span style={{background: 'var(--surface-hover)', padding: '4px 10px', borderRadius: '20px', fontSize: '0.75rem', fontWeight: 500}}>
              {repo.language}
            </span>
            <span className={`badge ${riskColors[repo.risk]}`}>
              {repo.risk.charAt(0).toUpperCase() + repo.risk.slice(1)} Risk
            </span>
          </div>
          <p style={{color: 'var(--text-muted)', marginTop: '4px'}}>{repo.description}</p>
        </div>
        <div style={{display: 'flex', gap: '8px'}}>
          <Link to={`/repositories/${repo.id}?tab=overview`} className="btn btn-secondary btn-sm">Overview</Link>
          <Link to={`/repositories/${repo.id}?tab=findings`} className="btn btn-secondary btn-sm">Findings</Link>
          <Link to={`/repositories/${repo.id}?tab=metrics`} className="btn btn-secondary btn-sm">Metrics</Link>
          <button className="btn btn-primary">
            <RefreshCw size={16} />
            Re-analyze
          </button>
        </div>
      </div>

      <div style={{ display: 'flex', gap: '12px', marginBottom: '20px', flexWrap: 'wrap' }}>
        <Link to="/repositories" className="tab-btn" style={{ padding: '10px 16px', borderRadius: '8px', textDecoration: 'none', background: activeTab === 'overview' ? 'var(--primary)' : 'var(--surface)', color: activeTab === 'overview' ? 'white' : 'var(--text-primary)', border: '1px solid var(--border)' }}>
          <Code size={16} style={{marginRight: '6px'}} /> Overview
        </Link>
        <Link to="/repositories" className="tab-btn" style={{ padding: '10px 16px', borderRadius: '8px', textDecoration: 'none', background: activeTab === 'findings' ? 'var(--primary)' : 'var(--surface)', color: activeTab === 'findings' ? 'white' : 'var(--text-primary)', border: '1px solid var(--border)' }}>
          <AlertTriangle size={16} style={{marginRight: '6px'}} /> Findings ({repo.metrics?.totalFindings || 0})
        </Link>
        <Link to="/repositories" className="tab-btn" style={{ padding: '10px 16px', borderRadius: '8px', textDecoration: 'none', background: activeTab === 'metrics' ? 'var(--primary)' : 'var(--surface)', color: activeTab === 'metrics' ? 'white' : 'var(--text-primary)', border: '1px solid var(--border)' }}>
          <TrendingUp size={16} style={{marginRight: '6px'}} /> Metrics
        </Link>
        <Link to="/repositories" className="tab-btn" style={{ padding: '10px 16px', borderRadius: '8px', textDecoration: 'none', background: activeTab === 'sbom' ? 'var(--primary)' : 'var(--surface)', color: activeTab === 'sbom' ? 'white' : 'var(--text-primary)', border: '1px solid var(--border)' }}>
          <Shield size={16} style={{marginRight: '6px'}} /> SBOM
        </Link>
      </div>

      {activeTab === 'overview' && (
        <div>
          <div style={{display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '16px', marginBottom: '24px'}}>
            <div className="stat-card">
              <div className="stat-header">
                <div className="stat-icon success"><CheckCircle size={20}/></div>
              </div>
              <div className="stat-value" style={{fontSize: '2.5rem'}}>{repo.score}</div>
              <div className="stat-label">Overall Score</div>
            </div>
            <div className="stat-card">
              <div className="stat-header">
                <div className="stat-icon info"><Shield size={20}/></div>
              </div>
              <div className="stat-value" style={{fontSize: '2.5rem'}}>{repo.metrics?.critical || 0}</div>
              <div className="stat-label">Critical Findings</div>
            </div>
            <div className="stat-card">
              <div className="stat-header">
                <div className="stat-icon warning"><AlertTriangle size={20}/></div>
              </div>
              <div className="stat-value" style={{fontSize: '2.5rem'}}>{repo.metrics?.high || 0}</div>
              <div className="stat-label">High Severity</div>
            </div>
            <div className="stat-card">
              <div className="stat-header">
                <div className="stat-icon info"><Code size={20}/></div>
              </div>
              <div className="stat-value" style={{fontSize: '2.5rem'}}>{repo.linesOfCode?.toLocaleString() || 0}</div>
              <div className="stat-label">Lines of Code</div>
            </div>
          </div>

          <div style={{display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(500px, 1fr))', gap: '20px'}}>
            <div className="card">
              <div className="card-header">
                <div className="card-title">Category Scores</div>
              </div>
              <div className="card-content">
                <div className="chart-container" style={{height: '300px'}}>
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={repo.categoryScores} layout="vertical" margin={{top: 10, right: 30, left: 100, bottom: 0}}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#e9ecef" horizontal={false} />
                      <XAxis type="number" tick={{fontSize: 11, fill: '#868e96'}} tickLine={false} axisLine={false} domain={[0, 100]} />
                      <YAxis type="category" dataKey="category" tick={{fontSize: 11, fill: '#868e96'}} tickLine={false} axisLine={false} width={100} />
                      <Tooltip contentStyle={{background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: '8px'}} formatter={(value) => [`${value}/100`, 'Score']} />
                      <Bar dataKey="score" fill="#0f3460" radius={[0, 4, 4, 0]} maxBarWidth={40} />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </div>
            </div>

            <div className="card">
              <div className="card-header">
                <div className="card-title">Risk Distribution</div>
              </div>
              <div className="card-content">
                <div className="chart-container" style={{height: '250px'}}>
                  <ResponsiveContainer width="100%" height="100%">
                    <PieChart>
                      <Pie data={[
                        { name: 'Critical', value: repo.metrics?.critical || 0, color: '#c92a2a' },
                        { name: 'High', value: repo.metrics?.high || 0, color: '#e67700' },
                        { name: 'Medium', value: repo.metrics?.medium || 0, color: '#e67700' },
                        { name: 'Low', value: repo.metrics?.low || 0, color: '#2b8a3e' },
                      ]} cx="50%" cy="50%" innerRadius={50} outerRadius={90} paddingAngle={3} dataKey="value" nameKey="name" label={({name, value, percent}) => `${name}: ${value} (${(percent*100).toFixed(0)}%)`} labelLine={false}>
                        <Cell fill="#c92a2a" />
                        <Cell fill="#e67700" />
                        <Cell fill="#e67700" />
                        <Cell fill="#2b8a3e" />
                      </Pie>
                      <Tooltip contentStyle={{background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: '8px'}} />
                    </PieChart>
                  </ResponsiveContainer>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {activeTab === 'findings' && (
        <div>
          <div className="card" style={{marginBottom: '20px'}}>
            <div className="card-content" style={{padding: '20px'}}>
              <div style={{display: 'flex', gap: '16px', flexWrap: 'wrap', alignItems: 'center'}}>
                <div style={{position: 'relative', minWidth: '250px'}}>
                  <Search size={18} style={{position: 'absolute', left: '12px', top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)'}} />
                  <input type="text" placeholder="Search findings..." className="form-input" style={{paddingLeft: '40px'}} />
                </div>
                <select className="form-input form-select" style={{minWidth: '150px'}} defaultValue="all" onChange={(e) => setFindingsFilter(e.target.value)}>
                  <option value="all">All Severities</option>
                  <option value="critical">Critical</option>
                  <option value="high">High</option>
                  <option value="medium">Medium</option>
                  <option value="low">Low</option>
                  <option value="security">Security</option>
                  <option value="complexity">Complexity</option>
                  <option value="testing">Testing</option>
                </select>
              </div>
            </div>
          </div>

          <div className="card">
            <div className="table-container">
              <table className="table">
                <thead>
                  <tr>
                    <th>Severity</th>
                    <th>Category</th>
                    <th>Title</th>
                    <th>Location</th>
                    <th>Recommendation</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredFindings.map((finding) => (
                    <tr key={finding.id}>
                      <td>
                        <span className={`badge ${severityColors[finding.severity]}`}>
                          {finding.severity.charAt(0).toUpperCase() + finding.severity.slice(1)}
                        </span>
                      </td>
                      <td>
                        <span style={{textTransform: 'capitalize'}}>{finding.category}</span>
                      </td>
                      <td style={{fontWeight: 500}}>{finding.title}</td>
                      <td>
                        <Code size={14} style={{marginRight: '6px', verticalAlign: 'middle'}} />
                        <span style={{fontFamily: 'monospace', fontSize: '0.85rem'}}>{finding.file}:{finding.line}</span>
                      </td>
                      <td style={{color: 'var(--text-secondary)', maxWidth: '300px'}}>{finding.recommendation}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {activeTab === 'metrics' && (
        <div className="card">
          <div className="card-content">
            <div className="chart-container" style={{height: '350px'}}>
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={repo.categoryScores} layout="vertical" margin={{top: 10, right: 30, left: 100, bottom: 0}}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#e9ecef" horizontal={false} />
                  <XAxis type="number" tick={{fontSize: 11, fill: '#868e96'}} tickLine={false} axisLine={false} domain={[0, 100]} />
                  <YAxis type="category" dataKey="category" tick={{fontSize: 11, fill: '#868e96'}} tickLine={false} axisLine={false} width={120} />
                  <Tooltip contentStyle={{background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: '8px'}} formatter={(value) => [`${value}/100`, 'Score']} />
                  <Bar dataKey="score" fill="#0f3460" radius={[0, 4, 4, 0]} maxBarWidth={40} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>
      )}

      {activeTab === 'sbom' && (
        <div className="card">
          <div className="card-header">
            <div className="card-title">Software Bill of Materials</div>
          </div>
          <div className="card-content">
            <div className="empty-state">
              <Shield size={64} />
              <h3>SBOM Generation</h3>
              <p>Generate and view the Software Bill of Materials for this repository</p>
              <button className="btn btn-primary" style={{marginTop: '16px'}}>
                <Shield size={16} style={{marginRight: '8px'}} />
                Generate SBOM
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default RepositoryDetail;
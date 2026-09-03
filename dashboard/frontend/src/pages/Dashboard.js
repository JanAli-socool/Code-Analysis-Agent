import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { TrendingUp, TrendingDown, AlertTriangle, CheckCircle, Clock, Database, Code, FileText, RefreshCw, Shield, AlertTriangle } from 'lucide-react';
import { AreaChart, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, PieChart, Pie, Cell, BarChart, Bar, Area } from 'recharts';

const API_BASE = process.env.REACT_APP_API_URL || 'http://localhost:8000';

const COLORS = ['#0f3460', '#00d9a5', '#e94560', '#e67700', '#1971c2', '#2b8a3e'];

function Dashboard() {
  const [stats, setStats] = useState({
    totalRepos: 0,
    analysesRun: 0,
    avgScore: 0,
    criticalFindings: 0,
  });
  const [scoreTrend, setScoreTrend] = useState([]);
  const [riskDistribution, setRiskDistribution] = useState([]);
  const [categoryScores, setCategoryScores] = useState([]);
  const [recentAnalyses, setRecentAnalyses] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetchDashboardData();
  }, []);

  const fetchDashboardData = async () => {
    try {
      setLoading(true);
      
      // In a real app, these would be API calls
      // For demo, we'll simulate data
      await new Promise(resolve => setTimeout(resolve, 500));
      
      // Mock data
      setStats({
        totalRepos: 24,
        analysesRun: 156,
        avgScore: 78.5,
        criticalFindings: 12,
      });

      setScoreTrend([
        { date: '2024-01-01', score: 72 },
        { date: '2024-01-08', score: 74 },
        { date: '2024-01-15', score: 76 },
        { date: '2024-01-22', score: 75 },
        { date: '2024-01-29', score: 77 },
        { date: '2024-02-05', score: 78 },
        { date: '2024-02-12', score: 79 },
        { date: '2024-02-19', score: 78 },
        { date: '2024-02-26', score: 80 },
        { date: '2024-03-04', score: 79 },
        { date: '2024-03-11', score: 81 },
        { date: '2024-03-18', score: 78 },
      ]);

      setRiskDistribution([
        { name: 'Low', value: 45, color: '#2b8a3e' },
        { name: 'Medium', value: 30, color: '#e67700' },
        { name: 'High', value: 18, color: '#e67700' },
        { name: 'Critical', value: 7, color: '#c92a2a' },
      ]);

      setCategoryScores([
        { category: 'Security', score: 82, weight: 3.0 },
        { category: 'Complexity', score: 75, weight: 2.0 },
        { category: 'Testing', score: 68, weight: 2.0 },
        { category: 'Architecture', score: 88, weight: 2.0 },
        { category: 'Maintainability', score: 74, weight: 1.5 },
        { category: 'Dependencies', score: 90, weight: 1.0 },
        { category: 'Documentation', score: 65, weight: 0.5 },
        { category: 'Git History', score: 72, weight: 0.5 },
      ]);

      setRecentAnalyses([
        { id: 1, repo: 'payment-service', score: 85, risk: 'low', date: '2024-03-15', status: 'completed' },
        { id: 2, repo: 'user-api', score: 72, risk: 'medium', date: '2024-03-14', status: 'completed' },
        { id: 3, repo: 'auth-service', score: 58, risk: 'high', date: '2024-03-13', status: 'completed' },
        { id: 4, repo: 'notification-service', score: 91, risk: 'low', date: '2024-03-12', status: 'completed' },
        { id: 5, repo: 'order-service', score: 63, risk: 'high', date: '2024-03-11', status: 'completed' },
      ]);

      setLoading(false);
    } catch (err) {
      console.error('Failed to fetch dashboard data:', err);
      setError('Failed to load dashboard data');
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="loading">
        <div className="spinner"></div>
      </div>
    );
  }

  const scoreChange = stats.avgScore - 75.2; // vs last period
  const analysesChange = 12; // vs last period
  const reposChange = 3;
  const criticalChange = -2;

  return (
    <div>
      <div className="stats-grid">
        <div className="stat-card">
          <div className="stat-header">
            <div className="stat-icon primary">
              <Database size={20} />
            </div>
            <span className={`stat-trend ${reposChange >= 0 ? 'positive' : 'negative'}`}>
              {reposChange >= 0 ? '+' : ''}{reposChange} this month
            </span>
          </div>
          <div className="stat-value">{stats.totalRepos}</div>
          <div className="stat-label">Total Repositories</div>
        </div>

        <div className="stat-card">
          <div className="stat-header">
            <div className="stat-icon success">
              <CheckCircle size={20} />
            </div>
            <span className="stat-trend positive">
              +{analysesChange} vs last month
            </span>
          </div>
          <div className="stat-value">{stats.analysesRun}</div>
          <div className="stat-label">Analyses Completed</div>
        </div>

        <div className="stat-card">
          <div className="stat-header">
            <div className="stat-icon info">
              <Code size={20} />
            </div>
            <span className={`stat-trend ${scoreChange >= 0 ? 'positive' : 'negative'}`}>
              {scoreChange >= 0 ? '+' : ''}{scoreChange.toFixed(1)} pts
            </span>
          </div>
          <div className="stat-value">{stats.avgScore.toFixed(1)}</div>
          <div className="stat-label">Average Score</div>
        </div>

        <div className="stat-card">
          <div className="stat-header">
            <div className="stat-icon danger">
              <AlertTriangle size={20} />
            </div>
            <span className={`stat-trend ${criticalChange <= 0 ? 'positive' : 'negative'}`}>
              {criticalChange >= 0 ? '+' : ''}{criticalChange} vs last month
            </span>
          </div>
          <div className="stat-value">{stats.criticalFindings}</div>
          <div className="stat-label">Critical Findings</div>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(500px, 1fr))', gap: '20px', marginBottom: '24px' }}>
        {/* Score Trend Chart */}
        <div className="card">
          <div className="card-header">
            <div className="card-title">
              <div style={{display: 'flex', alignItems: 'center', gap: '8px'}}>
                <TrendingUp size={18} style={{color: 'var(--primary)'}} />
                Score Trend (30 days)
              </div>
            </div>
          </div>
          <div className="card-content">
            <div className="chart-container">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={scoreTrend} margin={{ top: 10, right: 30, left: 0, bottom: 0 }}>
                  <defs>
                    <linearGradient id="colorScore" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#0f3460" stopOpacity={0.3}/>
                      <stop offset="95%" stopColor="#0f3460" stopOpacity={0}/>
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="#e9ecef" vertical={false} />
                  <XAxis dataKey="date" tick={{ fontSize: 11, fill: '#868e96' }} tickLine={false} axisLine={false} interval="preserveStartEnd" />
                  <YAxis tick={{ fontSize: 11, fill: '#868e96' }} tickLine={false} axisLine={false} domain={[60, 100]} />
                  <Tooltip 
                    contentStyle={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: '8px' }}
                    labelStyle={{ color: 'var(--text-primary)' }}
                  />
                  <Area 
                    type="monotone" 
                    dataKey="score" 
                    stroke="#0f3460" 
                    strokeWidth={2}
                    fillOpacity={1}
                    fill="url(#colorScore)"
                  />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>

        {/* Risk Distribution */}
        <div className="card">
          <div className="card-header">
            <div className="card-title">
              <div style={{display: 'flex', alignItems: 'center', gap: '8px'}}>
                <FileText size={18} style={{color: 'var(--primary)'}} />
                Risk Distribution
              </div>
            </div>
          </div>
          <div className="card-content">
            <div className="chart-container" style={{height: '280px'}}>
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={riskDistribution}
                    cx="50%"
                    cy="50%"
                    innerRadius={60}
                    outerRadius={100}
                    paddingAngle={2}
                    dataKey="value"
                    nameKey="name"
                    label={({ name, value, percent }) => `${name}: ${value} (${(percent * 100).toFixed(0)}%)`}
                    labelLine={false}
                  >
                    {riskDistribution.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={entry.color} />
                    ))}
                  </Pie>
                  <Tooltip 
                    contentStyle={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: '8px' }}
                  />
                </PieChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(500px, 1fr))', gap: '20px', marginBottom: '24px' }}>
        {/* Category Scores */}
        <div className="card">
          <div className="card-header">
            <div className="card-title">
              <div style={{display: 'flex', alignItems: 'center', gap: '8px'}}>
                <Shield size={18} style={{color: 'var(--primary)'}} />
                Category Scores
              </div>
            </div>
          </div>
          <div className="card-content">
            <div className="chart-container" style={{height: '300px'}}>
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={categoryScores} layout="vertical" margin={{ top: 10, right: 30, left: 80, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#e9ecef" horizontal={false} />
                  <XAxis type="number" tick={{ fontSize: 11, fill: '#868e96' }} tickLine={false} axisLine={false} domain={[0, 100]} />
                  <YAxis type="category" dataKey="category" tick={{ fontSize: 11, fill: '#868e96' }} tickLine={false} axisLine={false} width={100} />
                  <Tooltip 
                    contentStyle={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: '8px' }}
                    formatter={(value) => [`${value}/100`, 'Score']}
                  />
                  <Bar dataKey="score" fill="#0f3460" radius={[0, 4, 4, 0]} maxBarWidth={40} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>

        {/* Recent Analyses */}
        <div className="card">
          <div className="card-header">
            <div className="card-title">
              <div style={{display: 'flex', alignItems: 'center', justifyContent: 'space-between', width: '100%'}}>
                <div style={{display: 'flex', alignItems: 'center', gap: '8px'}}>
                  <Clock size={18} style={{color: 'var(--primary)'}} />
                  Recent Analyses
                </div>
                <Link to="/repositories" className="btn btn-sm btn-secondary">
                  View All
                </Link>
              </div>
            </div>
          </div>
          <div className="card-content">
            <div className="table-container">
              <table className="table">
                <thead>
                  <tr>
                    <th>Repository</th>
                    <th>Score</th>
                    <th>Risk</th>
                    <th>Date</th>
                    <th>Status</th>
                  </tr>
                </thead>
                <tbody>
                  {recentAnalyses.map((analysis) => (
                    <tr key={analysis.id}>
                      <td>
                        <Link to={`/repositories/${analysis.id}`} style={{color: 'inherit', textDecoration: 'none'}}>
                          <Code size={14} style={{marginRight: '8px', verticalAlign: 'middle'}} />
                          {analysis.repo}
                        </Link>
                      </td>
                      <td>
                        <span style={{fontWeight: 600, fontSize: '0.9rem'}}>{analysis.score}</span>
                      </td>
                      <td>
                        <span className={`badge badge-${analysis.risk === 'low' ? 'success' : analysis.risk === 'medium' ? 'warning' : 'danger'}`}>
                          {analysis.risk}
                        </span>
                      </td>
                      <td style={{color: 'var(--text-secondary)', fontSize: '0.85rem'}}>{analysis.date}</td>
                      <td>
                        <span className={`badge badge-${analysis.status === 'completed' ? 'success' : 'info'}`}>
                          {analysis.status}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default Dashboard;
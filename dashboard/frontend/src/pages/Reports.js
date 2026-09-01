import React, { useState, useEffect } from 'react';
import { Download, FileText, BarChart2, Calendar, Filter, ChevronLeft, ChevronRight } from 'lucide-react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, BarChart, Bar, PieChart, Pie, Cell } from 'recharts';

function Reports() {
  const [reports, setReports] = useState([]);
  const [loading, setLoading] = useState(true);
  const [dateRange, setDateRange] = useState({ start: '2024-01-01', end: '2024-03-20' });
  const [reportType, setReportType] = useState('summary');
  const [selectedRepo, setSelectedRepo] = useState('all');

  useEffect(() => {
    fetchReports();
  }, [dateRange, reportType, selectedRepo]);

  const fetchReports = async () => {
    await new Promise(resolve => setTimeout(resolve, 400));
    setReports([
      { id: 1, repo: 'payment-service', date: '2024-03-15', type: 'full', score: 85, risk: 'low', findings: 12, format: 'pdf', size: '2.4 MB' },
      { id: 2, repo: 'user-api', date: '2024-03-14', type: 'full', score: 72, risk: 'medium', findings: 23, format: 'pdf', size: '3.1 MB' },
      { id: 3, repo: 'auth-service', date: '2024-03-13', type: 'incremental', score: 58, risk: 'high', findings: 19, format: 'json', size: '456 KB' },
      { id: 4, repo: 'notification-service', date: '2024-03-12', type: 'full', score: 91, risk: 'low', findings: 3, format: 'pdf', size: '1.8 MB' },
      { id: 5, repo: 'order-service', date: '2024-03-11', type: 'full', score: 63, risk: 'high', findings: 21, format: 'pdf', size: '2.9 MB' },
    ]);
    setLoading(false);
  };

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px' }}>
        <div>
          <h2 style={{ fontSize: '1.5rem', fontWeight: 600, marginBottom: '4px' }}>Reports</h2>
          <p style={{ color: 'var(--text-muted)' }}>View and download analysis reports</p>
        </div>
        <div style={{ display: 'flex', gap: '12px' }}>
          <button className="btn btn-secondary">
            <Download size={18} />
            Export All
          </button>
        </div>
      </div>

      <div className="card" style={{ marginBottom: '24px' }}>
        <div className="card-content" style={{ padding: '20px' }}>
          <div style={{ display: 'flex', gap: '16px', flexWrap: 'wrap', alignItems: 'center' }}>
            <div style={{ display: 'flex', gap: '8px' }}>
              <label style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', marginRight: '8px' }}>From</label>
              <input type="date" className="form-input" style={{ width: '160px' }} value={dateRange.start} onChange={(e) => setDateRange({...dateRange, start: e.target.value})} />
            </div>
            <div style={{ display: 'flex', gap: '8px' }}>
              <label style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', marginRight: '8px' }}>To</label>
              <input type="date" className="form-input" style={{ width: '160px' }} value={dateRange.end} onChange={(e) => setDateRange({...dateRange, end: e.target.value})} />
            </div>
            <select value={reportType} onChange={(e) => setReportType(e.target.value)} className="form-input form-select" style={{ minWidth: '180px' }}>
              <option value="summary">Summary Reports</option>
              <option value="detailed">Detailed Reports</option>
              <option value="sbom">SBOM Reports</option>
              <option value="compliance">Compliance Reports</option>
            </select>
            <select value={selectedRepo} onChange={(e) => setSelectedRepo(e.target.value)} className="form-input form-select" style={{ minWidth: '180px' }}>
              <option value="all">All Repositories</option>
              <option value="payment-service">payment-service</option>
              <option value="user-api">user-api</option>
              <option value="auth-service">auth-service</option>
            </select>
          </div>
        </div>
      </div>

      <div className="card">
        <div className="card-header">
          <div className="card-title">Generated Reports</div>
        </div>
        <div className="table-container">
          <table className="table">
            <thead>
              <tr>
                <th>Repository</th>
                <th>Date</th>
                <th>Type</th>
                <th>Score</th>
                <th>Risk</th>
                <th>Findings</th>
                <th>Format</th>
                <th>Size</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr><td colSpan={9} style={{textAlign: 'center', padding: '48px'}}><div className="loading"><div className="spinner"></div></div></td></tr>
              ) : reports.map((report) => (
                <tr key={report.id}>
                  <td><strong>{report.repo}</strong></td>
                  <td style={{whiteSpace: 'nowrap'}}>{report.date}</td>
                  <td>
                    <span style={{background: 'var(--surface-hover)', padding: '4px 10px', borderRadius: '20px', fontSize: '0.7rem', fontWeight: 500'}}>
                      {report.type}
                    </span>
                  </td>
                  <td style={{fontWeight: 600}}>{report.score}</td>
                  <td>
                    <span className={`badge ${report.risk === 'low' ? 'badge-success' : report.risk === 'medium' ? 'badge-warning' : 'badge-danger'}`}>
                      {report.risk}
                    </span>
                  </td>
                  <td>{report.findings}</td>
                  <td>
                    <span style={{background: 'var(--surface-hover)', padding: '4px 10px', borderRadius: '20px', fontSize: '0.7rem', fontWeight: 500'}}>
                      {report.format}
                    </span>
                  </td>
                  <td style={{color: 'var(--text-secondary)'}}>{report.size}</td>
                  <td>
                    <button className="btn btn-icon btn-secondary" aria-label="Download"><FileText size={16} /></button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      <div style={{marginTop: '24px'}}>
        <h3 style={{fontSize: '1.25rem', fontWeight: 600, marginBottom: '16px'}}>Report Templates</h3>
        <div style={{display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: '16px'}}>
          <div className="card">
            <div className="card-content" style={{padding: '24px', textAlign: 'center'}}>
              <FileText size={48} style={{color: 'var(--primary)', marginBottom: '16px'}} />
              <h4 style={{marginBottom: '8px'}}>Executive Summary</h4>
              <p style={{color: 'var(--text-secondary)', marginBottom: '16px', fontSize: '0.9rem'}}>High-level overview for leadership</p>
              <button className="btn btn-secondary">Generate</button>
            </div>
          </div>
          <div className="card">
            <div className="card-content" style={{padding: '24px', textAlign: 'center'}}>
              <Shield size={48} style={{color: 'var(--success)', marginBottom: '16px'}} />
              <h4 style={{marginBottom: '8px'}}>Compliance Report</h4>
              <p style={{color: 'var(--text-secondary)', marginBottom: '16px', fontSize: '0.9rem'}}>License and security compliance</p>
              <button className="btn btn-secondary">Generate</button>
            </div>
          </div>
          <div className="card">
            <div className="card-content" style={{padding: '24px', textAlign: 'center'}}>
              <BarChart2 size={48} style={{color: 'var(--warning)', marginBottom: '16px'}} />
              <h4 style={{marginBottom: '8px'}}>Trend Analysis</h4>
              <p style={{color: 'var(--text-secondary)', marginBottom: '16px', fontSize: '0.9rem'}}>Historical score trends</p>
              <button className="btn btn-secondary">Generate</button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default Reports;
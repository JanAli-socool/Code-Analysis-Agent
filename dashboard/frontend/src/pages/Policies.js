import React, { useState, useEffect } from 'react';
import { Shield, Plus, Edit, Trash2, Search, X } from 'lucide-react';

function Policies() {
  const [policies, setPolicies] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [editingPolicy, setEditingPolicy] = useState(null);
  const [search, setSearch] = useState('');
  const [categoryFilter, setCategoryFilter] = useState('all');
  const [formData, setFormData] = useState({ id: '', name: '', category: 'security', rego: '' });

  const categories = ['security', 'complexity', 'testing', 'architecture', 'dependencies', 'licensing', 'custom'];

  useEffect(() => {
    fetchPolicies();
  }, []);

  const fetchPolicies = async () => {
    await new Promise(resolve => setTimeout(resolve, 300));
    setPolicies([
      { id: 'critical-vulnerabilities', name: 'Critical Vulnerabilities', category: 'security', description: 'Deny if critical vulnerabilities found', builtin: true, rego: 'package codeanalysis\n\nresult := {\n  "decision": "deny",\n  "message": "Critical vulnerabilities found"\n}' },
      { id: 'high-vulnerabilities', name: 'High Vulnerabilities Threshold', category: 'security', description: 'Warn if high vulnerabilities exceed 5', builtin: true, rego: 'package codeanalysis\n\nresult := {\n  "decision": "warn",\n  "message": "High vulnerabilities threshold exceeded"\n}' },
      { id: 'license-compliance', name: 'License Compliance', category: 'licensing', description: 'Block GPL-3.0, AGPL-3.0, LGPL-3.0', builtin: true, rego: 'package codeanalysis\n\nresult := {\n  "decision": "deny",\n  "message": "Blocked license detected"\n}' },
      { id: 'min-test-coverage', name: 'Minimum Test Coverage', category: 'testing', description: 'Warn if test coverage below 80%', builtin: true, rego: 'package codeanalysis\n\nresult := {\n  "decision": "warn",\n  "message": "Test coverage below threshold"\n}' },
      { id: 'custom-secret-detection', name: 'Custom Secret Detection', category: 'custom', description: 'Detect custom secret patterns', builtin: false, rego: 'package codeanalysis\n\nresult := {\n  "decision": "deny",\n  "message": "Custom secret pattern detected"\n}' },
    ]);
    setLoading(false);
  };

  const filteredPolicies = policies.filter(p => {
    if (search && !p.name.toLowerCase().includes(search.toLowerCase()) && !p.id.toLowerCase().includes(search.toLowerCase())) return false;
    if (categoryFilter !== 'all' && p.category !== categoryFilter) return false;
    return true;
  });

  const handleAdd = () => {
    setEditingPolicy(null);
    setFormData({ id: '', name: '', category: 'security', rego: 'package codeanalysis\n\nresult := {\n  "decision": "allow",\n  "message": "Custom policy passed"\n}' });
    setShowModal(true);
  };

  const handleEdit = (policy) => {
    setEditingPolicy(policy);
    setFormData({ id: policy.id, name: policy.name, category: policy.category, rego: policy.rego });
    setShowModal(true);
  };

  const handleSave = async (e) => {
    e.preventDefault();
    if (editingPolicy) {
      setPolicies(policies.map(p => p.id === editingPolicy.id ? { ...p, ...formData } : p));
    } else {
      setPolicies([...policies, { ...formData, builtin: false }]);
    }
    setShowModal(false);
    resetForm();
  };

  const handleDelete = (id) => {
    if (window.confirm('Delete this policy?')) {
      setPolicies(policies.filter(p => p.id !== id));
    }
  };

  const resetForm = () => {
    setFormData({ id: '', name: '', category: 'security', rego: 'package codeanalysis\n\nresult := {\n  "decision": "allow",\n  "message": "Custom policy passed"\n}' });
    setEditingPolicy(null);
  };

  const handleClose = () => {
    setShowModal(false);
    resetForm();
  };

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px' }}>
        <div>
          <h2 style={{ fontSize: '1.5rem', fontWeight: 600, marginBottom: '4px' }}>Policies</h2>
          <p style={{ color: 'var(--text-muted)' }}>Manage OPA/Rego policies for code analysis</p>
        </div>
        <button className="btn btn-primary" onClick={handleAdd}>
          <Plus size={18} />
          Add Policy
        </button>
      </div>

      <div className="card" style={{ marginBottom: '24px' }}>
        <div className="card-content" style={{ padding: '20px' }}>
          <div style={{ display: 'flex', gap: '16px', flexWrap: 'wrap', alignItems: 'center' }}>
            <div style={{ flex: 1, minWidth: '250px', position: 'relative' }}>
              <Search size={18} style={{ position: 'absolute', left: '12px', top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)' }} />
              <input type="text" placeholder="Search policies..." value={search} onChange={(e) => setSearch(e.target.value)} className="form-input" style={{ paddingLeft: '40px' }} />
            </div>
            <select value={categoryFilter} onChange={(e) => setCategoryFilter(e.target.value)} className="form-input form-select" style={{ minWidth: '180px' }}>
              <option value="all">All Categories</option>
              <option value="security">Security</option>
              <option value="complexity">Complexity</option>
              <option value="testing">Testing</option>
              <option value="architecture">Architecture</option>
              <option value="dependencies">Dependencies</option>
              <option value="licensing">Licensing</option>
              <option value="custom">Custom</option>
            </select>
          </div>
        </div>
      </div>

      <div className="card">
        <div className="table-container">
          <table className="table">
            <thead>
              <tr>
                <th>Policy ID</th>
                <th>Name</th>
                <th>Category</th>
                <th>Description</th>
                <th>Type</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {policies.filter(p => {
                if (search && !p.name.toLowerCase().includes(search.toLowerCase()) && !p.id.toLowerCase().includes(search.toLowerCase())) return false;
                if (categoryFilter !== 'all' && p.category !== categoryFilter) return false;
                return true;
              }).map((policy) => (
                <tr key={policy.id}>
                  <td style={{fontFamily: 'monospace', fontSize: '0.85rem'}}>{policy.id}</td>
                  <td style={{fontWeight: 500}}>{policy.name}</td>
                  <td>
                    <span style={{background: 'var(--surface-hover)', padding: '4px 10px', borderRadius: '20px', fontSize: '0.7rem', fontWeight: 500, textTransform: 'capitalize'}}>
                      {policy.category}
                    </span>
                  </td>
                  <td style={{color: 'var(--text-secondary)', maxWidth: '300px'}}>{policy.description}</td>
                  <td>
                    <span className={`badge ${policy.builtin ? 'badge-info' : 'badge-success'}`}>
                      {policy.builtin ? 'Built-in' : 'Custom'}
                    </span>
                  </td>
                  <td>
                    <div style={{display: 'flex', gap: '4px'}}>
                      <button className="btn btn-icon btn-secondary" onClick={() => handleEdit(policy)} aria-label="Edit">
                        <Edit size={16} />
                      </button>
                      {!policy.builtin && (
                        <button className="btn btn-icon btn-secondary" onClick={() => handleDelete(policy.id)} aria-label="Delete">
                          <Trash2 size={16} />
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Modal */}
      {showModal && (
        <div className="modal-overlay" onClick={handleClose}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h3>{editingPolicy ? 'Edit Policy' : 'Add Policy'}</h3>
              <button className="btn btn-icon btn-secondary" onClick={handleClose}><X size={20} /></button>
            </div>
            <form onSubmit={handleSave}>
              <div className="modal-body">
                <div className="form-group">
                  <label className="form-label">Policy ID</label>
                  <input type="text" className="form-input" value={formData.id} onChange={(e) => setFormData({...formData, id: e.target.value})} placeholder="unique-policy-id" required disabled={!!editingPolicy} />
                </div>
                <div className="form-group">
                  <label className="form-label">Name</label>
                  <input type="text" className="form-input" value={formData.name} onChange={(e) => setFormData({...formData, name: e.target.value})} placeholder="Policy Name" required />
                </div>
                <div className="form-group">
                  <label className="form-label">Category</label>
                  <select className="form-input form-select" value={formData.category} onChange={(e) => setFormData({...formData, category: e.target.value})}>
                    {['security', 'complexity', 'testing', 'architecture', 'dependencies', 'licensing', 'custom'].map(c => <option key={c} value={c}>{c.charAt(0).toUpperCase() + c.slice(1)}</option>)}
                  </select>
                </div>
                <div className="form-group">
                  <label className="form-label">Rego Policy</label>
                  <textarea className="form-input" style={{fontFamily: 'monospace', fontSize: '0.8rem', minHeight: '200px', resize: 'vertical'}} value={formData.rego} onChange={(e) => setFormData({...formData, rego: e.target.value})} placeholder={`package codeanalysis

result := {
  "decision": "allow",
  "message": "Policy passed"
}`} required />
                </div>
              </div>
              <div className="modal-footer">
                <button type="button" className="btn btn-secondary" onClick={handleClose}>Cancel</button>
                <button type="submit" className="btn btn-primary">{editingPolicy ? 'Update' : 'Create'} Policy</button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}

export default Policies;
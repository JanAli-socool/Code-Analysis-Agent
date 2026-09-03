import React, { useState, useEffect, useContext } from 'react';
import { User, Shield, Bell, Key, Database, Globe, Moon, Save, TestTube, Terminal, Download, Upload, Trash2, Code, LogOut, Github } from 'lucide-react';
import { AuthContext } from '../contexts/AuthContext';

function Settings() {
  const { user, logout, loginWithGoogle, loginWithGithub } = useContext(AuthContext);
  const [activeTab, setActiveTab] = useState('profile');
  const [settings, setSettings] = useState({
    profile: { name: user?.name || 'User', email: user?.email || '', avatar: user?.avatar || 'U' },
    notifications: { email: true, slack: false, webhook: false, critical: true, high: true, medium: false, low: false },
    security: { twoFactor: false, sessionTimeout: 30, apiKeys: [{ name: 'CI/CD Token', created: '2024-01-15', lastUsed: '2024-03-10' }] },
    integrations: { github: true, gitlab: false, jira: false, slack: false, teams: false },
    appearance: { theme: 'light', density: 'comfortable', sidebarCollapsed: false },
    advanced: { dataRetention: 90, autoAnalyze: true, parallelJobs: 4, logLevel: 'info' },
  });

  const tabs = [
    { id: 'profile', label: 'Profile', icon: <User size={16} /> },
    { id: 'notifications', label: 'Notifications', icon: <Bell size={16} /> },
    { id: 'security', label: 'Security', icon: <Shield size={16} /> },
    { id: 'integrations', label: 'Integrations', icon: <Database size={16} /> },
    { id: 'appearance', label: 'Appearance', icon: <Moon size={16} /> },
    { id: 'advanced', label: 'Advanced', icon: <Settings size={16} /> },
  ];

  const handleSave = (tab) => {
    console.log(`Saving ${tab} settings:`, settings[tab]);
    alert(`${tab.charAt(0).toUpperCase() + tab.slice(1)} settings saved!`);
  };

  const handleLogin = (provider) => {
    if (provider === 'google') {
      window.location.href = `${process.env.REACT_APP_API_URL || 'http://localhost:8000'}/auth/google`;
    } else if (provider === 'github') {
      window.location.href = `${process.env.REACT_APP_API_URL || 'http://localhost:8000'}/auth/github`;
    }
  };

  const handleLogout = () => {
    logout();
  };

  const avatarInitial = user?.name?.charAt(0)?.toUpperCase() || 'U';

  return (
    <div>
      <div style={{ marginBottom: '24px' }}>
        <h2 style={{ fontSize: '1.5rem', fontWeight: 600, marginBottom: '4px' }}>Settings</h2>
        <p style={{ color: 'var(--text-muted)' }}>Manage your account and application preferences</p>
      </div>

      <div className="card">
        <div className="card-content" style={{ padding: 0 }}>
          <div style={{ display: 'flex' }}>
            <nav style={{ width: '220px', borderRight: '1px solid var(--border)', padding: '16px 0' }}>
              {tabs.map((tab) => (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  style={{
                    width: '100%',
                    padding: '12px 20px',
                    border: 'none',
                    background: activeTab === tab.id ? 'var(--primary-light)' : 'transparent',
                    color: activeTab === tab.id ? 'var(--primary)' : 'var(--text-secondary)',
                    fontSize: '0.9rem',
                    fontWeight: activeTab === tab.id ? 600 : 500,
                    textAlign: 'left',
                    cursor: 'pointer',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '12px',
                    borderLeft: activeTab === tab.id ? '3px solid var(--primary)' : '3px solid transparent',
                    transition: 'all 0.15s',
                  }}
                >
                  {tab.icon}
                  {tab.label}
                </button>
              ))}
            </nav>

            <div style={{ flex: 1, padding: '24px', overflowY: 'auto', maxHeight: 'calc(100vh - 140px)' }}>
              {activeTab === 'profile' && (
                <div style={{ maxWidth: '600px' }}>
                  <h3 style={{ marginBottom: '24px', fontSize: '1.1rem' }}>Profile Information</h3>
                  
                  {!user ? (
                    <div style={{ textAlign: 'center', padding: '48px', background: 'var(--surface-hover)', borderRadius: '12px' }}>
                      <h3 style={{ marginBottom: '16px' }}>Sign in to manage your profile</h3>
                      <p style={{ color: 'var(--text-secondary)', marginBottom: '24px' }}>
                        Sign in with GitHub or Google to access your profile and settings.
                      </p>
                      <div style={{ display: 'flex', gap: '12px', justifyContent: 'center' }}>
                        <button className="btn btn-secondary" onClick={() => handleLogin('github')}>
                          <Github size={18} style={{ marginRight: '8px' }} />
                          Continue with GitHub
                        </button>
                        <button className="btn btn-secondary" onClick={() => handleLogin('google')}>
                          <svg width="18" height="18" viewBox="0 0 24 24" style={{ marginRight: '8px' }}>
                            <path fill="currentColor" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
                            <path fill="currentColor" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.09 1.06-3.42 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23c4.42 0 8.16-2.5 9.7-6h-1.4c-.79.58-1.8.89-3.1.89z"/>
                          </svg>
                          Continue with Google
                        </button>
                      </div>
                    </div>
                  ) : (
                    <div style={{ maxWidth: '600px' }}>
                      <h3 style={{ marginBottom: '24px', fontSize: '1.1rem' }}>Profile Information</h3>
                      <div className="form-group">
                        <label className="form-label">Display Name</label>
                        <input type="text" className="form-input" defaultValue={settings.profile.name} />
                      </div>
                      <div className="form-group">
                        <label className="form-label">Email Address</label>
                        <input type="email" className="form-input" defaultValue={settings.profile.email} />
                      </div>
                      <div className="form-group">
                        <label className="form-label">Avatar</label>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
                          <div style={{ width: '80px', height: '80px', borderRadius: '50%', background: 'var(--primary)', color: 'white', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '2rem', fontWeight: 600 }}>
                            {avatarInitial}
                          </div>
                          <button className="btn btn-secondary">Change Avatar</button>
                        </div>
                      </div>
                      <div style={{ marginTop: '24px', display: 'flex', gap: '12px' }}>
                        <button className="btn btn-primary" onClick={() => handleSave('profile')}>
                          <Save size={18} />
                          Save Changes
                        </button>
                        <button className="btn btn-danger" onClick={handleLogout}>
                          <LogOut size={18} />
                          Sign Out
                        </button>
                      </div>
                </div>
              )}

              {activeTab === 'notifications' && (
                <div style={{ maxWidth: '700px' }}>
                  <h3 style={{ marginBottom: '24px', fontSize: '1.1rem' }}>Notification Preferences</h3>
                  
                  <div style={{ marginBottom: '32px' }}>
                    <h4 style={{ marginBottom: '16px', fontSize: '0.9rem', fontWeight: 600 }}>Delivery Channels</h4>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                      {['email', 'slack', 'webhook'].map(channel => (
                        <label key={channel} style={{ display: 'flex', alignItems: 'center', gap: '12px', padding: '16px', background: 'var(--surface-hover)', borderRadius: '8px' }}>
                          <input type="checkbox" defaultChecked={settings.notifications[channel]} style={{ width: '20px', height: '20px', accentColor: 'var(--primary)' }} />
                          <span style={{ fontWeight: 500, textTransform: 'capitalize' }}>{channel}</span>
                        </label>
                      ))}
                    </div>
                  </div>

                  <div style={{ marginBottom: '32px' }}>
                    <h4 style={{ marginBottom: '16px', fontSize: '0.9rem', fontWeight: 600 }}>Severity Alerts</h4>
                    <p style={{ color: 'var(--text-secondary)', marginBottom: '16px', fontSize: '0.85rem' }}>Receive notifications for findings of these severity levels</p>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                      {['critical', 'high', 'medium', 'low'].map(severity => (
                        <label key={severity} style={{ display: 'flex', alignItems: 'center', gap: '12px', padding: '16px', background: 'var(--surface-hover)', borderRadius: '8px' }}>
                          <input type="checkbox" defaultChecked={settings.notifications[severity]} style={{ width: '20px', height: '20px', accentColor: 'var(--primary)' }} />
                          <span style={{ fontWeight: 500, textTransform: 'capitalize' }}>{severity}</span>
                        </label>
                      ))}
                    </div>
                  </div>

                  <button className="btn btn-primary" onClick={() => handleSave('notifications')}>
                    <Save size={18} />
                    Save Notification Settings
                  </button>
                </div>
              )}

              {activeTab === 'security' && (
                <div style={{ maxWidth: '700px' }}>
                  <h3 style={{ marginBottom: '24px', fontSize: '1.1rem' }}>Security Settings</h3>
                  
                  <div style={{ marginBottom: '32px', padding: '24px', background: 'var(--surface-hover)', borderRadius: '12px' }}>
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '16px' }}>
                      <div>
                        <h4 style={{ marginBottom: '4px' }}>Two-Factor Authentication</h4>
                        <p style={{ color: 'var(--text-secondary)', fontSize: '0.85rem' }}>Add an extra layer of security to your account</p>
                      </div>
                      <label style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                        <input type="checkbox" defaultChecked={settings.security.twoFactor} style={{ width: '24px', height: '24px', accentColor: 'var(--primary)' }} />
                      </label>
                    </div>
                    <button className="btn btn-primary" style={{ width: '100%' }}>Enable 2FA</button>
                  </div>

                  <div style={{ marginBottom: '32px' }}>
                    <h4 style={{ marginBottom: '16px' }}>Session Management</h4>
                    <div className="form-group">
                      <label className="form-label">Session Timeout (minutes)</label>
                      <input type="number" className="form-input" style={{ maxWidth: '120px' }} defaultValue={settings.security.sessionTimeout} min="5" max="480" />
                    </div>
                  </div>

                  <div style={{ marginBottom: '32px' }}>
                    <h4 style={{ marginBottom: '16px', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                      <span>API Keys</span>
                      <button className="btn btn-secondary btn-sm">
                        <Key size={16} />
                        Generate New Key
                      </button>
                    </h4>
                    <div className="table-container">
                      <table className="table">
                        <thead>
                          <tr>
                            <th>Name</th>
                            <th>Created</th>
                            <th>Last Used</th>
                            <th>Actions</th>
                          </tr>
                        </thead>
                        <tbody>
                          {settings.security.apiKeys.map((key, i) => (
                            <tr key={i}>
                              <td><code>{key.name}</code></td>
                              <td style={{color: 'var(--text-secondary)'}}>{key.created}</td>
                              <td style={{color: 'var(--text-secondary)'}}>{key.lastUsed}</td>
                              <td>
                                <button className="btn btn-icon btn-secondary" aria-label="Revoke"><Trash2 size={16} /></button>
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>

                  <button className="btn btn-primary" onClick={() => handleSave('security')}>
                    <Save size={18} />
                    Save Security Settings
                  </button>
                </div>
              )}

              {activeTab === 'integrations' && (
                <div style={{ maxWidth: '700px' }}>
                  <h3 style={{ marginBottom: '24px', fontSize: '1.1rem' }}>Third-Party Integrations</h3>
                  
                  {['github', 'gitlab', 'jira', 'slack', 'teams'].map(integration => (
                    <div key={integration} style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '20px', background: 'var(--surface-hover)', borderRadius: '8px', marginBottom: '12px' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
                        <div style={{ width: '48px', height: '48px', borderRadius: '12px', background: 'var(--primary)', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'white' }}>
                          {integration === 'github' && <Code size={24} />}
                          {integration === 'gitlab' && <Database size={24} />}
                          {integration === 'jira' && <TestTube size={24} />}
                          {integration === 'slack' && <Globe size={24} />}
                          {integration === 'teams' && <Terminal size={24} />}
                        </div>
                        <div>
                          <h4 style={{ marginBottom: '4px', textTransform: 'capitalize' }}>{integration}</h4>
                          <p style={{ color: 'var(--text-secondary)', fontSize: '0.85rem' }}>Connected to your {integration} account</p>
                        </div>
                      </div>
                      <label style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                        <input type="checkbox" defaultChecked={settings.integrations[integration]} style={{ width: '24px', height: '24px', accentColor: 'var(--primary)' }} />
                      </label>
                    </div>
                  ))}
                </div>
              )}

              {activeTab === 'appearance' && (
                <div style={{ maxWidth: '600px' }}>
                  <h3 style={{ marginBottom: '24px', fontSize: '1.1rem' }}>Appearance</h3>
                  
                  <div style={{ marginBottom: '32px' }}>
                    <h4 style={{ marginBottom: '16px' }}>Theme</h4>
                    <div style={{ display: 'flex', gap: '16px' }}>
                      {['light', 'dark', 'system'].map(theme => (
                        <label key={theme} style={{ flex: 1, padding: '20px', borderRadius: '12px', border: `2px solid ${settings.appearance.theme === theme ? 'var(--primary)' : 'var(--border)'}`, cursor: 'pointer', textAlign: 'center', transition: 'all 0.2s' }}>
                          <input type="radio" name="theme" value={theme} defaultChecked={settings.appearance.theme === theme} style={{ display: 'none' }} />
                          <div style={{ fontWeight: 600, textTransform: 'capitalize', marginBottom: '8px' }}>{theme}</div>
                          <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                            {theme === 'light' && 'Light mode'}
                            {theme === 'dark' && 'Dark mode'}
                            {theme === 'system' && 'Follow system'}
                          </p>
                        </label>
                      ))}
                    </div>
                  </div>

                  <div style={{ marginBottom: '32px' }}>
                    <h4 style={{ marginBottom: '16px' }}>Density</h4>
                    <div style={{ display: 'flex', gap: '16px' }}>
                      {['compact', 'comfortable', 'spacious'].map(density => (
                        <label key={density} style={{ flex: 1, padding: '20px', borderRadius: '12px', border: `2px solid ${settings.appearance.density === density ? 'var(--primary)' : 'var(--border)'}`, cursor: 'pointer', textAlign: 'center' }}>
                          <input type="radio" name="density" value={density} defaultChecked={settings.appearance.density === density} style={{ display: 'none' }} />
                          <div style={{ fontWeight: 600, textTransform: 'capitalize' }}>{density}</div>
                        </label>
                      ))}
                    </div>
                  </div>

                  <div style={{ marginBottom: '32px' }}>
                    <h4 style={{ marginBottom: '16px' }}>Sidebar</h4>
                    <label style={{ display: 'flex', alignItems: 'center', gap: '12px', padding: '16px', background: 'var(--surface-hover)', borderRadius: '8px' }}>
                      <input type="checkbox" defaultChecked={settings.appearance.sidebarCollapsed} style={{ width: '24px', height: '24px', accentColor: 'var(--primary)' }} />
                      <span>Collapse sidebar by default</span>
                    </label>
                  </div>

                  <button className="btn btn-primary" onClick={() => handleSave('appearance')}>
                    <Save size={18} />
                    Save Appearance Settings
                  </button>
                </div>
              )}

              {activeTab === 'advanced' && (
                <div style={{ maxWidth: '700px' }}>
                  <h3 style={{ marginBottom: '24px', fontSize: '1.1rem' }}>Advanced Settings</h3>
                  
                  <div style={{ marginBottom: '32px' }}>
                    <h4 style={{ marginBottom: '16px' }}>Data Management</h4>
                    <div className="form-group">
                      <label className="form-label">Data Retention (days)</label>
                      <input type="number" className="form-input" style={{ maxWidth: '120px' }} defaultValue={settings.advanced.dataRetention} min="1" max="365" />
                      <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginTop: '4px' }}>How long to keep analysis results and reports</p>
                    </div>
                  </div>

                  <div style={{ marginBottom: '32px' }}>
                    <h4 style={{ marginBottom: '16px' }}>Analysis Settings</h4>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                      <label style={{ display: 'flex', alignItems: 'center', gap: '12px', padding: '16px', background: 'var(--surface-hover)', borderRadius: '8px' }}>
                        <input type="checkbox" defaultChecked={settings.advanced.autoAnalyze} style={{ width: '24px', height: '24px', accentColor: 'var(--primary)' }} />
                        <div>
                          <strong>Auto-analyze on push</strong>
                          <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginTop: '2px' }}>Automatically run analysis when code is pushed</p>
                        </div>
                      </label>
                      <div className="form-group" style={{ maxWidth: '200px' }}>
                        <label className="form-label">Parallel Jobs</label>
                        <input type="number" className="form-input" defaultValue={settings.advanced.parallelJobs} min="1" max="16" />
                      </div>
                    </div>
                  </div>

                  <div style={{ marginBottom: '32px' }}>
                    <h4 style={{ marginBottom: '16px' }}>Logging</h4>
                    <div className="form-group" style={{ maxWidth: '200px' }}>
                      <label className="form-label">Log Level</label>
                      <select className="form-input form-select" defaultValue={settings.advanced.logLevel}>
                        <option value="debug">Debug</option>
                        <option value="info">Info</option>
                        <option value="warn">Warning</option>
                        <option value="error">Error</option>
                      </select>
                    </div>
                  </div>

                  <div style={{ marginBottom: '32px', padding: '24px', background: 'var(--surface-hover)', borderRadius: '12px' }}>
                    <h4 style={{ marginBottom: '16px' }}>Danger Zone</h4>
                    <p style={{ color: 'var(--text-secondary)', marginBottom: '16px' }}>These actions are irreversible</p>
                    <div style={{ display: 'flex', gap: '12px', flexWrap: 'wrap' }}>
                      <button className="btn btn-secondary">
                        <Download size={18} />
                        Export All Data
                      </button>
                      <button className="btn btn-secondary">
                        <Upload size={18} />
                        Import Data
                      </button>
                      <button className="btn btn-danger">
                        <Trash2 size={18} />
                        Delete All Data
                      </button>
                    </div>
                  </div>

                  <button className="btn btn-primary" onClick={() => handleSave('advanced')}>
                    <Save size={18} />
                    Save Advanced Settings
                  </button>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default Settings;
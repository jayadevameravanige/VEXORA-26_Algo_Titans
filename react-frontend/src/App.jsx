import { useState, useEffect } from 'react'
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip, Legend, BarChart, Bar, XAxis, YAxis, CartesianGrid } from 'recharts'
import { Upload, FileText, AlertTriangle, CheckCircle, Shield, History, Activity, Map as MapIcon, LogOut } from 'lucide-react'
import logo from './assets/logo.png'
import './App.css'

const API_BASE = '/api'

function App() {
  const [isLoggedIn, setIsLoggedIn] = useState(false)
  const [currentUser, setCurrentUser] = useState({ name: '', role: '' })
  const [loginData, setLoginData] = useState({ username: '', password: '' })

  const [stats, setStats] = useState({
    total_records: 0,
    ghost_voters: 0,
    duplicate_voters: 0,
    flagged_as_both: 0,
    analysis_status: 'pending'
  })
  const [complianceData, setComplianceData] = useState(null)
  const [file, setFile] = useState(null)
  const [loading, setLoading] = useState(false)
  const [message, setMessage] = useState('')
  const [currentView, setCurrentView] = useState('dashboard') // 'dashboard' or 'records'
  const [ghostRecords, setGhostRecords] = useState([])
  const [duplicateRecords, setDuplicateRecords] = useState([])
  const [selectedRecords, setSelectedRecords] = useState(new Set())
  const [selectedReviewedIds, setSelectedReviewedIds] = useState(new Set())
  const [historyRecords, setHistoryRecords] = useState([])
  const [visibleGhostCount, setVisibleGhostCount] = useState(50)
  const [visibleDuplicateCount, setVisibleDuplicateCount] = useState(50)
  const [privacyMode, setPrivacyMode] = useState(false)

  const maskText = (text, type = 'name') => {
    if (!privacyMode || !text) return text
    if (type === 'name') {
      const parts = text.split(' ')
      return parts.map(p => p[0] + '*'.repeat(Math.max(0, p.length - 1))).join(' ')
    }
    if (type === 'address') {
      // Keep city/state if at end, mask the street
      const parts = text.split(',')
      if (parts.length > 2) {
        return `${parts[0].substring(0, 3)}... ${parts.slice(-2).join(',')}`
      }
      return text.substring(0, 5) + '...'
    }
    return '****'
  }

  useEffect(() => {
    // Check for saved session
    const savedUser = localStorage.getItem('voteGuardUser')
    if (savedUser) {
      setCurrentUser(JSON.parse(savedUser))
      setIsLoggedIn(true)
    }
  }, [])

  useEffect(() => {
    if (isLoggedIn) {
      // Don't auto-fetch anything on refresh to keep a 100% clean slate
      // Data will load when analysis starts or when viewing history
    }
  }, [isLoggedIn])

  useEffect(() => {
    if (isLoggedIn && (currentView === 'records' || currentView === 'history' || currentView === 'reviewed_ids')) {
      if (currentView === 'history' || currentView === 'reviewed_ids') {
        fetchHistory()
      }
      // Only fetch flagged if we actually have stats/analysis run in this session
      if (stats.total_records > 0 && currentView === 'records') {
        fetchAllFlagged()
      }
    }
  }, [currentView, isLoggedIn, stats.total_records])

  const handleLogin = async (e) => {
    e.preventDefault()
    setLoading(true)
    setMessage('')

    try {
      const res = await fetch(`${API_BASE}/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(loginData)
      })

      const data = await res.json()

      if (res.ok && data.status === 'success') {
        const user = data.user
        setCurrentUser(user)
        setIsLoggedIn(true)
        localStorage.setItem('voteGuardUser', JSON.stringify(user))
        localStorage.setItem('voteGuardToken', data.token) // Session Token
      } else {
        setMessage(data.message || 'Access Denied: Highly Secure Endpoint')
      }
    } catch (err) {
      setMessage('Security Server Connection Failed')
    } finally {
      setLoading(false)
    }
  }

  const handleLogout = () => {
    setIsLoggedIn(false)
    setCurrentUser({ name: '', role: '' })
    localStorage.removeItem('voteGuardUser')
  }

  const fetchStats = async () => {
    try {
      const res = await fetch(`${API_BASE}/stats`)
      if (!res.ok) return
      const data = await res.json()
      if (data.status === 'success') {
        setStats({
          total_records: data.total_records || 0,
          ghost_voters: data.ghost_voters_flagged || 0,
          duplicate_voters: data.duplicate_voters_flagged || 0,
          flagged_as_both: data.summary?.summary?.flagged_as_both || 0,
          analysis_status: 'completed'
        })
        setComplianceData(data.security_report || null)
      }
    } catch (err) {
      console.error('Failed to fetch stats:', err)
    }
  }

  const fetchAllFlagged = async (force = false) => {
    // Only fetch if we don't have data, to prevent lagging on view switch
    const tasks = []
    if (force || ghostRecords.length === 0) tasks.push(fetchFlaggedByType('ghost', setGhostRecords))
    if (force || duplicateRecords.length === 0) tasks.push(fetchFlaggedByType('duplicate', setDuplicateRecords))

    if (tasks.length > 0) {
      await Promise.all(tasks)
    }
  }

  const fetchFlaggedByType = async (type, setter) => {
    try {
      // Increased limit to 5000 to capture complete datasets
      const res = await fetch(`${API_BASE}/flagged?type=${type}&limit=5000`)
      if (!res.ok) {
        setMessage(`⚠️ Failed to fetch ${type} records from security server.`)
        return
      }
      const data = await res.json()
      if (data.status === 'success') {
        setter(data.records || [])
      }
    } catch (err) {
      console.error(`Failed to fetch ${type} records:`, err)
      setMessage(`⚠️ Connection error while fetching ${type} records.`)
    }
  }

  const fetchHistory = async () => {
    try {
      const res = await fetch(`${API_BASE}/history`)
      if (!res.ok) return
      const data = await res.json()
      if (data.status === 'success') {
        setHistoryRecords(data.records || [])
      }
    } catch (err) {
      console.error('Failed to fetch history:', err)
    }
  }

  const handleExportCSV = async (scope = 'audit') => {
    setMessage(`📥 Preparing your ${scope === 'history' ? 'history' : 'audit'} report...`)
    try {
      const response = await fetch(`${API_BASE}/export/csv?scope=${scope}`)
      if (!response.ok) {
        const errorData = await response.json()
        setMessage(`❌ Export failed: ${errorData.error || 'Check server state'}`)
        return
      }

      // If OK, trigger download
      const blob = await response.blob()
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = 'voteguard_audit_report.csv'
      document.body.appendChild(a)
      a.click()
      window.URL.revokeObjectURL(url)
      setMessage('✅ Audit report downloaded successfully!')
    } catch (err) {
      console.error('Export error:', err)
      setMessage('⚠️ Error connecting to export server.')
    }
  }

  const handleFileUpload = async (event) => {
    const selectedFile = event.target.files[0]
    if (!selectedFile) return

    setFile(selectedFile)
    setMessage(`Selected: ${selectedFile.name}`)

    // Automatically start analysis
    await handleUpload(selectedFile)
  }

  const handleUpload = async (fileToUpload = null) => {
    const targetFile = fileToUpload || file

    if (!targetFile) {
      setMessage('Please select a CSV file first')
      return
    }

    setLoading(true)
    setMessage('Uploading...')
    const formData = new FormData()
    formData.append('file', targetFile)

    try {
      const res = await fetch(`${API_BASE}/upload`, {
        method: 'POST',
        body: formData
      })
      let data;
      try {
        data = await res.json();
      } catch (jsonErr) {
        throw new Error(`Invalid response from server (Status: ${res.status})`);
      }

      if (res.ok && data.status === 'success') {
        setMessage('File uploaded! Starting immediate analysis...')
        await runAnalysis(data.filepath)
      } else {
        setMessage('Upload failed: ' + (data.message || data.error || `Server error ${res.status}`))
      }
    } catch (err) {
      setMessage('Security Server Connection Error: ' + err.message)
    } finally {
      setLoading(false)
    }
  }

  const runAnalysis = async (filePath = null) => {
    setLoading(true)
    setMessage('🛡️ Audit in progress...')
    try {
      const options = {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' }
      }
      if (filePath) options.body = JSON.stringify({ data_path: filePath })

      const res = await fetch(`${API_BASE}/analyze`, options)

      let data;
      try {
        data = await res.json();
      } catch (jsonErr) {
        if (!res.ok) {
          throw new Error(`Server returned error ${res.status}: ${res.statusText}`);
        }
        throw new Error("Analysis completed but server returned an invalid response.");
      }

      if (res.ok && data.status === 'success') {
        setMessage('✅ Audit completed successfully!')
        await fetchStats()
        await fetchAllFlagged(true) // Force fresh fetch after update
      } else {
        setMessage('Audit failed: ' + (data.message || data.error || `Server error ${res.status}`))
      }
    } catch (err) {
      setMessage('Analysis error: ' + err.message)
    } finally {
      setLoading(false)
    }
  }

  if (!isLoggedIn) {
    return (
      <div className="login-page">
        <div className="login-card">
          <div className="login-header">
            <h1 className="login-logo">VoteGuard</h1>
            <p>Electoral Integrity Audit System</p>
          </div>
          <form onSubmit={handleLogin} className="login-form">
            <div className="form-group">
              <label>Username</label>
              <input
                type="text"
                placeholder="Enter admin username"
                value={loginData.username}
                onChange={(e) => setLoginData({ ...loginData, username: e.target.value })}
                required
              />
            </div>
            <div className="form-group">
              <label>Password</label>
              <input
                type="password"
                placeholder="Enter password"
                value={loginData.password}
                onChange={(e) => setLoginData({ ...loginData, password: e.target.value })}
                required
              />
            </div>
            <button type="submit" className="btn-login" disabled={loading}>
              {loading ? "Authenticating..." : "Login as Admin Auditor"}
            </button>
            {message && <p className="login-error">{message}</p>}
          </form>
          <div className="login-footer">
          </div>
        </div>
      </div>
    )
  }

  const highRisk = stats.flagged_as_both
  const mediumRisk = (stats.ghost_voters + stats.duplicate_voters) - (2 * stats.flagged_as_both)
  const totalFlagged = stats.ghost_voters + stats.duplicate_voters - stats.flagged_as_both
  const cleanRecords = stats.total_records > 0 ? (stats.total_records - totalFlagged) : 0

  const toggleSelection = (voterId) => {
    setSelectedRecords(prev => {
      const next = new Set(prev)
      if (next.has(voterId)) {
        next.delete(voterId)
      } else {
        next.add(voterId)
      }
      return next
    })
  }

  const toggleReviewedSelection = (voterId) => {
    setSelectedReviewedIds(prev => {
      const next = new Set(prev)
      if (next.has(voterId)) {
        next.delete(voterId)
      } else {
        next.add(voterId)
      }
      return next
    })
  }

  const handleApproveReviewed = async () => {
    if (selectedReviewedIds.size === 0) {
      setMessage('⚠️ Please select at least one ID to approve.')
      return
    }

    const voterIds = Array.from(selectedReviewedIds)
    setLoading(true)
    try {
      const res = await fetch(`${API_BASE}/delete`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          voter_ids: voterIds,
          decision: 'approved'
        })
      })

      const data = await res.json()
      if (data.status === 'success') {
        setMessage(`✅ ${voterIds.length} voter IDs APPROVED and added to Clean Records!`)
        setSelectedReviewedIds(new Set())
        await fetchStats()
        await fetchHistory()
      } else {
        setMessage('❌ Failed to approve records.')
      }
    } catch (err) {
      console.error('Approve error:', err)
      setMessage('⚠️ Connection error during approval.')
    } finally {
      setLoading(false)
    }
  }

  const handleDeleteReviewed = async () => {
    if (selectedReviewedIds.size === 0) {
      setMessage('⚠️ Please select at least one ID to delete.')
      return
    }

    if (!window.confirm(`Are you sure you want to permanently delete these ${selectedReviewedIds.size} IDs? They will be marked as deleted in history.`)) {
      return
    }

    const voterIds = Array.from(selectedReviewedIds)
    setLoading(true)
    try {
      const res = await fetch(`${API_BASE}/delete`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          voter_ids: voterIds,
          decision: 'deleted'
        })
      })

      const data = await res.json()
      if (data.status === 'success') {
        setMessage(`🗑️ ${voterIds.length} voter IDs moved to history and marked as DELETED.`)
        setSelectedReviewedIds(new Set())
        await fetchStats()
        await fetchHistory()
      } else {
        setMessage('❌ Failed to delete records.')
      }
    } catch (err) {
      console.error('Delete error:', err)
      setMessage('⚠️ Connection error during deletion.')
    } finally {
      setLoading(false)
    }
  }

  const handleReviewGhost = async () => {
    if (privacyMode) {
      setMessage('⚠️ Actions restricted: Cannot review records in Auditor Mode (Privacy Guard).')
      return
    }

    const ghostVoterIds = Array.from(selectedRecords).filter(id =>
      ghostRecords.some(r => r.voter_id === id)
    )

    if (ghostVoterIds.length === 0) {
      setMessage('⚠️ Please select at least one ghost voter record to review.')
      return
    }

    if (!window.confirm(`Are you sure you want to confirm review for ${ghostVoterIds.length} records and move them to history?`)) {
      return
    }

    setLoading(true)
    try {
      const res = await fetch(`${API_BASE}/delete`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ voter_ids: ghostVoterIds })
      })

      const data = await res.json()
      if (data.status === 'success') {
        setMessage(`✅ ${data.deleted_count} records reviewed and moved to history!`)
        setSelectedRecords(new Set())
        await fetchStats()
        await fetchAllFlagged(true) // Force update
        await fetchHistory()
      } else {
        setMessage('❌ Failed to review records.')
      }
    } catch (err) {
      console.error('Review error:', err)
      setMessage('⚠️ Connection error during review.')
    } finally {
      setLoading(false)
    }
  }

  const handleReviewDuplicate = async () => {
    if (privacyMode) {
      setMessage('⚠️ Actions restricted: Cannot review records in Auditor Mode (Privacy Guard).')
      return
    }

    const dupeVoterIds = Array.from(selectedRecords).filter(id =>
      duplicateRecords.some(r => r.voter_id === id)
    )

    if (dupeVoterIds.length === 0) {
      setMessage('⚠️ Please select at least one duplicate record to review.')
      return
    }

    if (!window.confirm(`Are you sure you want to confirm review for ${dupeVoterIds.length} duplicate records?`)) {
      return
    }

    setLoading(true)
    try {
      const res = await fetch(`${API_BASE}/delete`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ voter_ids: dupeVoterIds })
      })

      const data = await res.json()
      if (data.status === 'success') {
        setMessage(`✅ ${data.deleted_count} duplicate records reviewed and moved to history!`)
        setSelectedRecords(new Set())
        await fetchStats()
        await fetchAllFlagged(true)
        await fetchHistory()
      } else {
        setMessage('❌ Failed to review records.')
      }
    } catch (err) {
      console.error('Review error:', err)
      setMessage('⚠️ Connection error during review.')
    } finally {
      setLoading(false)
    }
  }

  const chartData = [
    { name: 'Clean', value: cleanRecords, color: '#10b981' },
    { name: 'Ghost', value: stats.ghost_voters, color: '#8b5cf6' },
    { name: 'Duplicate', value: stats.duplicate_voters, color: '#f59e0b' }
  ].filter(item => item.value > 0)

  const riskData = [
    { name: 'High Risk', value: highRisk, fill: '#ef4444' },
    { name: 'Med Risk', value: mediumRisk, fill: '#f59e0b' },
    { name: 'Safe', value: cleanRecords, fill: '#10b981' }
  ]

  return (
    <div className="app-container">
      {/* Top Navigation Bar */}
      <nav className="top-nav">
        <div className="nav-brand">
          <span className="nav-logo-icon">🗳️</span>
          <span className="nav-logo">VoteGuard</span>
        </div>

        <div className="nav-menu">
          <div className={`nav-link ${currentView === 'dashboard' ? 'active' : ''}`} onClick={() => setCurrentView('dashboard')}>
            🏠 Dashboard
          </div>
          <div className={`nav-link ${currentView === 'records' ? 'active' : ''}`} onClick={() => setCurrentView('records')}>
            📋 Records
          </div>
          <div className={`nav-link ${currentView === 'compliance' ? 'active' : ''}`} onClick={() => setCurrentView('compliance')}>
            🛡️ Compliance
          </div>
          <div className={`nav-link ${currentView === 'history' ? 'active' : ''}`} onClick={() => setCurrentView('history')}>
            🔄 History
          </div>
          <div className={`nav-link ${currentView === 'reviewed_ids' ? 'active' : ''}`} onClick={() => setCurrentView('reviewed_ids')}>
            🆔 Reviewed
          </div>
          <div className={`nav-link ${currentView === 'rules' ? 'active' : ''}`} onClick={() => setCurrentView('rules')}>
            📜 Rules
          </div>
        </div>

        <div className="nav-actions">
          <div className="nav-user">
            <div className="nav-avatar">{currentUser.initials}</div>
            <div className="nav-user-info">
              <div className="nav-user-name">{currentUser.name}</div>
              <div className="nav-user-role">{currentUser.role}</div>
            </div>
          </div>
          <button className="btn-logout" onClick={handleLogout}>
            🚪 Logout
          </button>
        </div>
      </nav>

      {/* Main Content Area */}
      <main className="main-content">
        {/* Main Content conditionally rendered based on view */}
        {currentView === 'dashboard' && (
          <div className="dashboard-wrapper">
            {/* Hero Section */}
            <section className="hero-section">
              <div className="hero-content">
                <div className="hero-text">
                  <h1>Welcome, {currentUser.name.split(' ')[0]}!</h1>
                  <p>Your comprehensive electoral integrity dashboard. Monitor, analyze, and maintain voter database security.</p>
                </div>
                <div className="hero-logo">
                  <img src={logo} alt="VoteGuard Logo" />
                </div>
              </div>
            </section>

            {/* Privacy Toggle - Top Right */}
            <div style={{ display: 'flex', justifyContent: 'flex-end', marginBottom: '2rem' }}>
              <div className="privacy-toggle">
                <span className="privacy-label">🛡️ Privacy Guard</span>
                <label className="switch">
                  <input
                    type="checkbox"
                    checked={privacyMode}
                    onChange={(e) => setPrivacyMode(e.target.checked)}
                  />
                  <span className="slider"></span>
                </label>
                <span className={`privacy-status ${privacyMode ? 'on' : 'off'}`}>
                  {privacyMode ? 'SECURE' : 'PUBLIC'}
                </span>
              </div>
            </div>

            {/* Stats Grid */}
            <div className="stats-grid">
              <div className="stat-card">
                <div className="stat-header">
                  <div className="stat-icon">🗳️</div>
                </div>
                <div className="stat-label">Total Voters</div>
                <div className="stat-value">{stats.total_records.toLocaleString()}</div>
                <div className="stat-change">Audited database</div>
              </div>

              <div className="stat-card">
                <div className="stat-header">
                  <div className="stat-icon" style={{ background: 'var(--gradient-fire)' }}>👻</div>
                </div>
                <div className="stat-label">Ghost Voters</div>
                <div className="stat-value" style={{ color: 'var(--secondary)' }}>{stats.ghost_voters}</div>
                <div className="stat-change">Flagged for review</div>
              </div>

              <div className="stat-card">
                <div className="stat-header">
                  <div className="stat-icon" style={{ background: 'var(--gradient-sunset)' }}>📋</div>
                </div>
                <div className="stat-label">Duplicates</div>
                <div className="stat-value" style={{ color: 'var(--warning)' }}>{stats.duplicate_voters}</div>
                <div className="stat-change">Potential duplicates</div>
              </div>

              <div className="stat-card">
                <div className="stat-header">
                  <div className="stat-icon" style={{ background: 'var(--gradient-forest)' }}>✓</div>
                </div>
                <div className="stat-label">Clean Records</div>
                <div className="stat-value" style={{ color: 'var(--success)' }}>{cleanRecords}</div>
                <div className="stat-change">Verified clean</div>
              </div>
            </div>

            {/* Action Cards */}
            <div className="actions-grid">
              <div className="action-card" onClick={() => document.getElementById('file-upload').click()}>
                <span className="action-icon">📂</span>
                <span className="action-label">Select File</span>
              </div>
              <div className="action-card" onClick={() => setCurrentView('records')}>
                <span className="action-icon">📋</span>
                <span className="action-label">View Records</span>
              </div>
              <div className="action-card" onClick={() => setCurrentView('history')}>
                <span className="action-icon">🔄</span>
                <span className="action-label">History</span>
              </div>
              <div className="action-card" onClick={() => setCurrentView('compliance')}>
                <span className="action-icon">🛡️</span>
                <span className="action-label">Compliance</span>
              </div>
            </div>

            {/* Dashboard Grid */}
            <div className="dashboard-grid">
              {/* Left Column - Metrics & Charts */}
              <div className="dashboard-card">
                <h2 className="card-title">🗳️ Detailed Analytics</h2>

                {/* Metrics Row */}
                <div className="metrics-row">
                  <div className="metric-main">
                    <div className="metric-main-label">TOTAL VOTERS</div>
                    <div className="metric-main-value">{stats.total_records.toLocaleString()}</div>
                    <div className="metric-main-badge">Audited</div>
                  </div>

                  <div className="metrics-mini-grid">
                    <div className="mini-metric">
                      <div className="mini-metric-label">Ghosts</div>
                      <div className="mini-metric-value" style={{ color: 'var(--secondary)' }}>{stats.ghost_voters}</div>
                    </div>
                    <div className="mini-metric">
                      <div className="mini-metric-label">Duplicates</div>
                      <div className="mini-metric-value" style={{ color: 'var(--warning)' }}>{stats.duplicate_voters}</div>
                    </div>
                    <div className="mini-metric">
                      <div className="mini-metric-label">Clean</div>
                      <div className="mini-metric-value" style={{ color: 'var(--success)' }}>{cleanRecords}</div>
                    </div>
                    <div className="mini-metric">
                      <div className="mini-metric-label">Flagged</div>
                      <div className="mini-metric-value" style={{ color: 'var(--danger)' }}>{totalFlagged}</div>
                    </div>
                  </div>
                </div>

                {/* Charts */}
                {stats.total_records > 0 && (
                  <div className="charts-container">
                    <div className="chart-wrapper">
                      <h3 className="chart-title">Distribution</h3>
                      <ResponsiveContainer width="100%" height={200}>
                        <PieChart>
                          <Pie
                            data={chartData}
                            cx="50%"
                            cy="50%"
                            innerRadius={40}
                            outerRadius={60}
                            paddingAngle={5}
                            dataKey="value"
                          >
                            {chartData.map((entry, index) => (
                              <Cell key={`cell-${index}`} fill={entry.color} />
                            ))}
                          </Pie>
                          <Tooltip contentStyle={{ borderRadius: '8px' }} />
                        </PieChart>
                      </ResponsiveContainer>
                    </div>
                    <div className="chart-wrapper">
                      <h3 className="chart-title">Risk Level</h3>
                      <ResponsiveContainer width="100%" height={200}>
                        <BarChart data={riskData}>
                          <CartesianGrid strokeDasharray="3 3" vertical={false} opacity={0.1} />
                          <XAxis dataKey="name" axisLine={false} tickLine={false} fontSize={12} />
                          <YAxis hide />
                          <Tooltip cursor={{ fill: 'transparent' }} contentStyle={{ borderRadius: '8px' }} />
                          <Bar dataKey="value" radius={[4, 4, 0, 0]} barSize={30} />
                        </BarChart>
                      </ResponsiveContainer>
                    </div>
                  </div>
                )}

                {stats.risk_by_region && stats.risk_by_region.length > 0 && (
                  <div className="heatmap-container">
                    <div className="heatmap-header">
                      <div className="heatmap-title">
                        <span>🗺️ Geospatial Risk Heatmap</span>
                      </div>
                      <div className="heatmap-badge">Regional Intelligence</div>
                    </div>
                    <div className="heatmap-chart-wrapper">
                      <ResponsiveContainer width="100%" height={Math.max(200, stats.risk_by_region.length * 40)}>
                        <BarChart
                          data={stats.risk_by_region}
                          layout="vertical"
                          margin={{ top: 5, right: 30, left: 40, bottom: 5 }}
                        >
                          <CartesianGrid strokeDasharray="3 3" horizontal={true} vertical={false} opacity={0.1} />
                          <XAxis type="number" hide />
                          <YAxis
                            dataKey="region"
                            type="category"
                            axisLine={false}
                            tickLine={false}
                            fontSize={11}
                            width={100}
                            tick={{ fontWeight: 600, fill: '#64748b' }}
                          />
                          <Tooltip
                            cursor={{ fill: 'rgba(59, 130, 246, 0.05)' }}
                            contentStyle={{ borderRadius: '12px', border: 'none', boxShadow: '0 10px 15px -3px rgba(0,0,0,0.1)' }}
                          />
                          <Legend wrapperStyle={{ paddingTop: '20px', fontSize: '11px' }} />
                          <Bar dataKey="ghost" name="Ghost Risk" stackId="a" fill="#8b5cf6" radius={[0, 0, 0, 0]} barSize={20} />
                          <Bar dataKey="duplicate" name="Duplicate Risk" stackId="a" fill="#f59e0b" radius={[0, 4, 4, 0]} barSize={20} />
                        </BarChart>
                      </ResponsiveContainer>
                    </div>
                  </div>
                )}

                {/* Upload Section */}
                <div className="upload-section">
                  <input
                    type="file"
                    id="file-upload"
                    className="file-input-custom"
                    accept=".csv"
                    onChange={handleFileUpload}
                  />
                  <button
                    className="btn-upload"
                    onClick={handleUpload}
                    disabled={loading}
                  >
                    {loading ? '⏳ PROCESSING...' : 'UPLOAD NEW BATCH'}
                  </button>
                  {message && <p className="message-box">{message}</p>}
                </div>
              </div>

              {/* Right Column - Risk Feed */}
              <div className="dashboard-card">
                <h2 className="card-title">🛡️ Risk Assessment</h2>
                <div className="risk-feed">
                  <div className="risk-item">
                    <div className="risk-info">
                      <div className="risk-title">High Risk Records</div>
                      <div className="risk-desc">Both Ghost & Duplicate flags</div>
                    </div>
                    <div className="risk-badge high">{highRisk} Found</div>
                  </div>
                  <div className="risk-item">
                    <div className="risk-info">
                      <div className="risk-title">Medium Risk Records</div>
                      <div className="risk-desc">Single anomaly detected</div>
                    </div>
                    <div className="risk-badge medium">{mediumRisk} Found</div>
                  </div>
                  <div className="risk-item">
                    <div className="risk-info">
                      <div className="risk-title">Safe Records</div>
                      <div className="risk-desc">Verified clean registrations</div>
                    </div>
                    <div className="risk-badge low">{cleanRecords} Verified</div>
                  </div>
                  <div style={{ marginTop: '1.5rem', textAlign: 'center' }}>
                    <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                      Last scan: {new Date().toLocaleDateString()}
                    </p>
                    <button className="btn-primary" onClick={() => setCurrentView('records')} style={{ marginTop: '1rem', width: '100%' }}>
                      View All Flagged Records →
                    </button>
                  </div>
                  <button className="btn-extract-report" onClick={() => handleExportCSV('audit')}>
                    📥 Download Audit Report
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}

        {currentView === 'records' && (
          <section className="records-view">
            <div className="records-header">
              <div className="header-text">
                <h2>Flagged Voter Records</h2>
                <p>Detailed analysis of potential ghost and duplicate entries</p>
              </div>
            </div>

            <div style={{ display: 'flex', justifyContent: 'flex-end', marginBottom: '2rem', marginTop: '-1.5rem' }}>
              <button className="btn-back" onClick={() => setCurrentView('dashboard')}>
                ← Back to Dashboard
              </button>
            </div>

            <div className="records-sub-sections">
              <div className="records-section-block">
                <div className="section-header-flex">
                  <h3 className="records-subtitle ghost-text">🛡️ Ghost Voter Records</h3>
                  <button
                    className="btn-delete-selected"
                    onClick={handleReviewGhost}
                    disabled={selectedRecords.size === 0 || loading || privacyMode}
                    title={privacyMode ? "Actions restricted in Privacy Mode" : ""}
                  >
                    👁️ Review Selected
                  </button>
                </div>
                <div className="records-table-container">
                  <table className="records-table">
                    <thead>
                      <tr>
                        <th>Voter ID</th>
                        <th>Voter Profile</th>
                        <th>Type</th>
                        <th>Confidence</th>
                        <th>Analysis & Reasons</th>
                      </tr>
                    </thead>
                    <tbody>
                      {ghostRecords.length > 0 ? (
                        ghostRecords.slice(0, visibleGhostCount).map((record) => (
                          <tr key={record.voter_id} className={selectedRecords.has(record.voter_id) ? 'row-selected' : ''}>
                            <td className="voter-id-cell">
                              <div className="voter-id-stack">
                                <span className="font-mono">{record.voter_id}</span>
                                <input
                                  type="checkbox"
                                  className="voter-checkbox"
                                  checked={selectedRecords.has(record.voter_id)}
                                  onChange={() => toggleSelection(record.voter_id)}
                                />
                              </div>
                            </td>
                            <td>
                              <div className="voter-name-cell">
                                <div className="voter-name">{maskText(record.voter_details?.name || 'N/A', 'name')}</div>
                                <div className="voter-meta">
                                  {record.voter_details?.Gender && <span className="meta-badge gender">{record.voter_details.Gender}</span>}
                                  {record.voter_details?.Age && <span className="meta-badge age">{record.voter_details.Age}y</span>}
                                </div>
                                <div className="voter-address-mini">{maskText(record.voter_details?.Address || 'No address provided', 'address')}</div>
                              </div>
                            </td>
                            <td><span className="record-type-tag ghost">GHOST</span></td>
                            <td>
                              <div className="confidence-pill" style={{
                                background: `linear-gradient(90deg, #8b5cf6 ${record.confidence * 100}%, #e2e8f0 0%)`
                              }}>
                                {(record.confidence * 100).toFixed(0)}%
                              </div>
                            </td>
                            <td className="reasons-cell">
                              <div className="voter-details-mini">
                                <strong>{record.primary_reason}</strong>
                                <ul className="reasons-list">
                                  {record.contributing_factors?.map((f, i) => (
                                    <li key={i}>{f.factor}: {f.value}</li>
                                  ))}
                                </ul>
                              </div>
                            </td>
                          </tr>
                        ))
                      ) : (
                        <tr><td colSpan="5" className="empty-state">No ghost voters detected in the current batch.</td></tr>
                      )}
                    </tbody>
                  </table>
                </div>
                {ghostRecords.length > visibleGhostCount && (
                  <div className="load-more-container">
                    <button className="btn-load-more" onClick={() => setVisibleGhostCount(prev => prev + 50)}>
                      Show More Records ({ghostRecords.length - visibleGhostCount} remaining)
                    </button>
                  </div>
                )}
              </div>

              <div className="records-section-block" style={{ marginTop: '3rem' }}>
                <div className="section-header-flex">
                  <h3 className="records-subtitle duplicate-text">🛡️ Duplicate Voter Records</h3>
                  <button
                    className="btn-delete-selected"
                    onClick={handleReviewDuplicate}
                    disabled={selectedRecords.size === 0 || loading || privacyMode}
                    title={privacyMode ? "Actions restricted in Privacy Mode" : ""}
                  >
                    👁️ Review Selected
                  </button>
                </div>
                <div className="records-table-container">
                  <table className="records-table">
                    <thead>
                      <tr>
                        <th>Voter ID</th>
                        <th>Voter Details</th>
                        <th>Type</th>
                        <th>Confidence</th>
                        <th>Analysis & Reasons</th>
                      </tr>
                    </thead>
                    <tbody>
                      {duplicateRecords.length > 0 ? (
                        duplicateRecords.slice(0, visibleDuplicateCount).map((record) => (
                          <tr key={record.voter_id} className={selectedRecords.has(record.voter_id) ? 'row-selected' : ''}>
                            <td className="voter-id-cell">
                              <div className="voter-id-stack">
                                <span className="font-mono">{record.voter_id}</span>
                                <input
                                  type="checkbox"
                                  className="voter-checkbox"
                                  checked={selectedRecords.has(record.voter_id)}
                                  onChange={() => toggleSelection(record.voter_id)}
                                />
                              </div>
                            </td>
                            <td>
                              <div className="voter-name-cell">
                                <div className="voter-name">{maskText(record.voter_details?.name || 'N/A', 'name')}</div>
                                <div className="voter-meta">
                                  {record.voter_details?.Gender && <span className="meta-badge gender">{record.voter_details.Gender}</span>}
                                  {record.voter_details?.Age && <span className="meta-badge age">{record.voter_details.Age}y</span>}
                                </div>
                                <div className="voter-address-mini">{maskText(record.voter_details?.Address || 'No address provided', 'address')}</div>
                              </div>
                            </td>
                            <td><span className="record-type-tag duplicate">DUPLICATE</span></td>
                            <td>
                              <div className="confidence-pill" style={{
                                background: `linear-gradient(90deg, #f59e0b ${record.confidence * 100}%, #e2e8f0 0%)`
                              }}>
                                {(record.confidence * 100).toFixed(0)}%
                              </div>
                            </td>
                            <td className="reasons-cell">
                              <div className="voter-details-mini">
                                <strong>{record.primary_reason}</strong>
                                <ul className="reasons-list">
                                  {record.contributing_factors?.map((f, i) => (
                                    <li key={i}>{f.factor}: {f.value}</li>
                                  ))}
                                </ul>
                              </div>
                            </td>
                          </tr>
                        ))
                      ) : (
                        <tr><td colSpan="5" className="empty-state">No duplicate voters detected in the current batch.</td></tr>
                      )}
                    </tbody>
                  </table>
                </div>
                {duplicateRecords.length > visibleDuplicateCount && (
                  <div className="load-more-container">
                    <button className="btn-load-more" onClick={() => setVisibleDuplicateCount(prev => prev + 50)}>
                      Show More Records ({duplicateRecords.length - visibleDuplicateCount} remaining)
                    </button>
                  </div>
                )}
              </div>
            </div>
          </section>
        )}

        {currentView === 'compliance' && (
          <section className="compliance-view">
            <div className="records-header">
              <div className="header-text">
                <h2>Security Compliance Report</h2>
                <p>Verification of electoral integrity and algorithmic transparency</p>
              </div>
              <button className="btn-back" onClick={() => setCurrentView('dashboard')}>
                ← Back to Dashboard
              </button>
            </div>

            <div className="compliance-grid">
              <div className="compliance-card main-status">
                <div className="compliance-score">
                  <div className="score-circle">
                    <span className="score-num">100</span>
                    <span className="score-pct">%</span>
                  </div>
                  <div className="score-label">Integrity Score</div>
                </div>
                <div className="compliance-meta">
                  <div className="meta-item">
                    <span className="meta-label">Session ID:</span>
                    <span className="meta-val font-mono">{complianceData?.session_id || 'N/A'}</span>
                  </div>
                  <div className="meta-item">
                    <span className="meta-label">Generated:</span>
                    <span className="meta-val">{complianceData?.generated_at ? new Date(complianceData.generated_at).toLocaleString() : 'N/A'}</span>
                  </div>
                </div>
              </div>

              <div className="compliance-card safeguards-list">
                <h3>Active Safeguards</h3>
                <div className="safeguard-items">
                  {complianceData?.safeguards ? Object.entries(complianceData.safeguards).map(([key, value]) => (
                    <div className="safeguard-row" key={key}>
                      <div className="safeguard-name">
                        <span className="status-dot active"></span>
                        {key.replace(/_/g, ' ')}
                      </div>
                      <div className="safeguard-status">{value}</div>
                    </div>
                  )) : (
                    <p className="empty-state">No active safeguards detected. Run analysis first.</p>
                  )}
                </div>
              </div>

              <div className="compliance-card democratic-principles">
                <h3>Democratic Principles</h3>
                <div className="principles-grid">
                  {complianceData?.compliance ? Object.entries(complianceData.compliance).map(([key, value]) => (
                    <div className={`principle-box ${value ? 'passed' : 'failed'}`} key={key}>
                      <span className="principle-icon">{value ? '✅' : '❌'}</span>
                      <span className="principle-name">{key.replace(/_/g, ' ')}</span>
                    </div>
                  )) : (
                    <p className="empty-state">Run analysis for audit findings.</p>
                  )}
                </div>
              </div>
            </div>

            <div className="audit-disclaimer">
              <p>🛡️ This report is cryptographically signed and forms part of the permanent electoral audit trail.</p>
            </div>
          </section>
        )}

        {currentView === 'rules' && (
          <section className="compliance-view rules-view">
            <div className="records-header">
              <div className="header-text">
                <h2>System Detection Rules</h2>
                <p>Technical transparency into the mathematical logic used to flag voter records</p>
              </div>
              <button className="btn-back" onClick={() => setCurrentView('dashboard')}>
                ← Back to Dashboard
              </button>
            </div>

            <div className="compliance-grid">
              <div className="compliance-card">
                <h3>🔍 Ghost Detection Logic</h3>
                <div className="safeguard-items">
                  <div className="safeguard-row">
                    <div className="safeguard-name">
                      <div className="status-dot active"></div>
                      Age Threshold
                    </div>
                    <div className="safeguard-status">Flag if Age ≥ 110 years</div>
                  </div>
                  <div className="safeguard-row">
                    <div className="safeguard-name">
                      <div className="status-dot active"></div>
                      Inactivity Rule
                    </div>
                    <div className="safeguard-status">Last voted before year 2000</div>
                  </div>
                  <div className="safeguard-row">
                    <div className="safeguard-name">
                      <div className="status-dot active"></div>
                      Isolation Forest
                    </div>
                    <div className="safeguard-status">ML Statistical Anomaly Check</div>
                  </div>
                </div>
                <div className="audit-disclaimer" style={{ marginTop: '1.5rem', textAlign: 'left' }}>
                  Rule: (Age ≥ 110) OR (Inactive) OR (ML Score &lt; -0.7)
                </div>
              </div>

              <div className="compliance-card">
                <h3>👯 Duplicate Detection Logic</h3>
                <div className="safeguard-items">
                  <div className="safeguard-row">
                    <div className="safeguard-name">
                      <div className="status-dot active"></div>
                      Clustering Key
                    </div>
                    <div className="safeguard-status">Exact Match: DOB + Pincode</div>
                  </div>
                  <div className="safeguard-row">
                    <div className="safeguard-name">
                      <div className="status-dot active"></div>
                      Fuzzy Name Match
                    </div>
                    <div className="safeguard-status">Token Sort Ratio ≥ 85%</div>
                  </div>
                  <div className="safeguard-row">
                    <div className="safeguard-name">
                      <div className="status-dot active"></div>
                      Confidence Score
                    </div>
                    <div className="safeguard-status">Similarity + Pincode Weight</div>
                  </div>
                </div>
                <div className="audit-disclaimer" style={{ marginTop: '1.5rem', textAlign: 'left' }}>
                  Rule: (Same DOB) AND (Same Pincode) AND (Fuzzy Name ≥ 85%)
                </div>
              </div>

              <div className="compliance-card main-status">
                <div className="compliance-score">
                  <div className="score-circle" style={{ borderColor: '#3b82f6', background: '#eff6ff' }}>
                    <span className="score-num" style={{ color: '#1e40af' }}>AI</span>
                  </div>
                  <p className="score-label">Logic Engine</p>
                </div>
                <div className="compliance-meta">
                  <div className="meta-item">
                    <span className="meta-label">Match Algorithm</span>
                    <span className="meta-val">RapidFuzz Native</span>
                  </div>
                  <div className="meta-item">
                    <span className="meta-label">ML Model</span>
                    <span className="meta-val">Scikit-IsolationForest</span>
                  </div>
                  <div className="meta-item">
                    <span className="meta-label">Sensitivity</span>
                    <span className="meta-val">Balanced (Standard)</span>
                  </div>
                </div>
              </div>
            </div>
          </section>
        )}

        {currentView === 'history' && (
          <section className="records-view history-view">
            <div className="records-header">
              <div className="header-text">
                <h2>Records History</h2>
                <p>Permanent log of all reviewed and archived records</p>
              </div>
              <div style={{ display: 'flex', gap: '1rem' }}>
                <button className="btn-load-more" onClick={() => handleExportCSV('history')} style={{ margin: 0, padding: '0.5rem 1rem' }}>
                  📥 Export History CSV
                </button>
                <button className="btn-back" onClick={() => setCurrentView('dashboard')}>
                  ← Back to Dashboard
                </button>
              </div>
            </div>

            <div className="records-table-container">
              <table className="records-table">
                <thead>
                  <tr>
                    <th>Voter ID</th>
                    <th>Voter Details</th>
                    <th>Archived Type</th>
                    <th>Decision</th>
                    <th>Archived Date</th>
                  </tr>
                </thead>
                <tbody>
                  {historyRecords.length > 0 ? (
                    historyRecords.map((record) => (
                      <tr key={record.voter_id}>
                        <td className="font-mono">{record.voter_id}</td>
                        <td>
                          <div className="voter-name-cell">
                            <div className="voter-name">{maskText(record.voter_details?.name || 'N/A', 'name')}</div>
                            <div className="voter-address-mini">{maskText(record.voter_details?.Address || 'No address provided', 'address')}</div>
                          </div>
                        </td>
                        <td>
                          <span className={`record-type-tag ${record.archive_type}`}>
                            {record.archive_type?.toUpperCase()}
                          </span>
                        </td>
                        <td>
                          <span className={`record-type-tag ${record.archive_status || 'archived'}`} style={
                            record.archive_status === 'approved'
                              ? { background: '#dcfce7', color: '#166534' }
                              : { background: '#fee2e2', color: '#991b1b' }
                          }>
                            {(record.archive_status || 'Archived').toUpperCase()}
                          </span>
                        </td>
                        <td>{new Date(record.archived_at).toLocaleString()}</td>
                      </tr>
                    ))
                  ) : (
                    <tr><td colSpan="5" className="empty-state">No records in history.</td></tr>
                  )}
                </tbody>
              </table>
            </div>
          </section>
        )}
        {currentView === 'reviewed_ids' && (
          <section className="records-view reviewed-ids-view">
            <div className="records-header">
              <div className="header-text">
                <h2>Reviewed Voter Initial Database</h2>
                <p>A specialized list containing only the unique Voter IDs that have completed the AI review process.</p>
              </div>
              <button className="btn-back" onClick={() => setCurrentView('dashboard')}>
                ← Back to Dashboard
              </button>
            </div>

            <div className="bulk-actions-outer-container">
              <div className="bulk-actions-reviewed">
                <button className="btn-approve-reviewed" onClick={handleApproveReviewed} disabled={selectedReviewedIds.size === 0}>
                  ✅ Approve Selected
                </button>
                <button className="btn-delete-reviewed" onClick={handleDeleteReviewed} disabled={selectedReviewedIds.size === 0}>
                  🗑️ Delete Selected
                </button>
              </div>
            </div>

            <div className="records-table-container">
              <table className="records-table">
                <thead>
                  <tr>
                    <th style={{ width: '40px' }}></th>
                    <th>Serial No.</th>
                    <th>Voter ID</th>
                    <th>Audit Timestamp</th>
                    <th>Status</th>
                    <th>Evidence / Action</th>
                  </tr>
                </thead>
                <tbody>
                  {historyRecords.filter(r => r.archive_status === 'pending' || !r.archive_status).length > 0 ? (
                    historyRecords.filter(r => r.archive_status === 'pending' || !r.archive_status).map((record, index) => (
                      <tr key={record.voter_id} className={selectedReviewedIds.has(record.voter_id) ? 'row-selected' : ''}>
                        <td>
                          <input
                            type="checkbox"
                            className="voter-checkbox"
                            checked={selectedReviewedIds.has(record.voter_id)}
                            onChange={() => toggleReviewedSelection(record.voter_id)}
                          />
                        </td>
                        <td>{index + 1}</td>
                        <td className="font-mono" style={{ color: 'var(--accent-blue)', fontWeight: 'bold' }}>{record.voter_id}</td>
                        <td>{new Date(record.archived_at).toLocaleString()}</td>
                        <td>
                          <span className="record-type-tag" style={{ background: '#fef9c3', color: '#854d0e' }}>
                            REVIEW PENDING
                          </span>
                        </td>
                        <td>
                          <div className="upload-btn-wrapper">
                            <label className="btn-upload-mini" title="Upload proof (JPG/PNG)">
                              📁 Upload Evidence
                              <input
                                type="file"
                                accept="image/png, image/jpeg"
                                style={{ display: 'none' }}
                                onChange={(e) => {
                                  if (e.target.files[0]) {
                                    setMessage(`📦 Evidence uploaded for ID: ${record.voter_id}`)
                                  }
                                }}
                              />
                            </label>
                          </div>
                        </td>
                      </tr>
                    ))
                  ) : (
                    <tr><td colSpan="6" className="empty-state">No pending reviews found. New records appear here after AI audit and initial review.</td></tr>
                  )}
                </tbody>
              </table>
            </div>
          </section>
        )}
      </main>
    </div>
  )
}

export default App

import React from 'react'
import { ShieldAlert, LayoutDashboard, Film, PlayCircle, History, BarChart3 } from 'lucide-react'

export default function Header({ currentTab, onSelectTab, runningJobCount }) {
  return (
    <header className="app-header">
      <div className="brand-wrapper">
        <div className="brand-icon">
          <ShieldAlert size={22} />
        </div>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span className="brand-title">AI SafetyGuard</span>
            <span className="brand-badge">Student ML Edition</span>
          </div>
          <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
            Multimodal Threat & Safety Detection Pipeline
          </div>
        </div>
      </div>

      <nav className="nav-tabs">
        <button
          className={`nav-tab-btn ${currentTab === 'dashboard' ? 'active' : ''}`}
          onClick={() => onSelectTab('dashboard')}
        >
          <LayoutDashboard size={16} />
          Dashboard
        </button>

        <button
          className={`nav-tab-btn ${currentTab === 'analyze' ? 'active' : ''}`}
          onClick={() => onSelectTab('analyze')}
        >
          <Film size={16} />
          Analyze Video
          {runningJobCount > 0 && (
            <span style={{
              background: '#2563eb',
              color: 'white',
              fontSize: '0.65rem',
              borderRadius: '999px',
              padding: '1px 6px',
              marginLeft: '4px'
            }}>
              {runningJobCount}
            </span>
          )}
        </button>

        <button
          className={`nav-tab-btn ${currentTab === 'results' ? 'active' : ''}`}
          onClick={() => onSelectTab('results')}
        >
          <PlayCircle size={16} />
          Player & Timeline
        </button>

        <button
          className={`nav-tab-btn ${currentTab === 'history' ? 'active' : ''}`}
          onClick={() => onSelectTab('history')}
        >
          <History size={16} />
          Reports & History
        </button>

        <button
          className={`nav-tab-btn ${currentTab === 'evaluation' ? 'active' : ''}`}
          onClick={() => onSelectTab('evaluation')}
        >
          <BarChart3 size={16} />
          Model Evaluation
        </button>
      </nav>
    </header>
  )
}

import React from 'react'
import {
  Video,
  AlertTriangle,
  Flame,
  CheckCircle2,
  Clock,
  ArrowRight,
  ExternalLink,
  ShieldAlert,
  Info
} from 'lucide-react'

export default function DashboardView({ stats, onNavigateTab, onSelectJob }) {
  const {
    total_videos_analyzed = 0,
    running_jobs = 0,
    total_incidents_flagged = 0,
    high_priority_incidents = 0,
    recent_jobs = []
  } = stats || {}

  return (
    <div>
      {/* Notice Banner */}
      <div className="disclaimer-banner">
        <Info size={18} style={{ flexShrink: 0 }} />
        <div>
          <strong>Potential Incident Screening System:</strong> This application assists human operators by flagging candidate intervals with observable warnings (aggressive motion jerk, shouting frequencies, or distress phrases). Predictions do not prove a crime, and absence of alerts does not establish safety.
        </div>
      </div>

      {/* Stats Summary */}
      <div className="stats-grid">
        <div className="stat-card">
          <div className="stat-icon blue">
            <Video size={24} />
          </div>
          <div>
            <div className="stat-value">{total_videos_analyzed}</div>
            <div className="stat-label">Total Videos Analyzed</div>
          </div>
        </div>

        <div className="stat-card">
          <div className="stat-icon red">
            <Flame size={24} />
          </div>
          <div>
            <div className="stat-value">{high_priority_incidents}</div>
            <div className="stat-label">High Priority Incidents</div>
          </div>
        </div>

        <div className="stat-card">
          <div className="stat-icon amber">
            <AlertTriangle size={24} />
          </div>
          <div>
            <div className="stat-value">{total_incidents_flagged}</div>
            <div className="stat-label">Total Candidate Alerts</div>
          </div>
        </div>

        <div className="stat-card">
          <div className="stat-icon green">
            <Clock size={24} />
          </div>
          <div>
            <div className="stat-value">{running_jobs}</div>
            <div className="stat-label">Jobs Currently Active</div>
          </div>
        </div>
      </div>

      {/* Action Banner */}
      <div className="card" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', background: 'linear-gradient(135deg, #eff6ff 0%, #ffffff 100%)', border: '1px solid #bfdbfe' }}>
        <div>
          <h2 style={{ fontSize: '1.2rem', fontWeight: '700', color: '#1e3a8a', marginBottom: '4px' }}>
            Ready to screen a new video?
          </h2>
          <p style={{ color: '#475569', fontSize: '0.9rem' }}>
            Upload a local CCTV/MP4 recording or submit a public YouTube video URL to run the multimodal analysis.
          </p>
        </div>
        <button
          className="primary-btn"
          onClick={() => onNavigateTab('analyze')}
          style={{ flexShrink: 0 }}
        >
          Start Analysis
          <ArrowRight size={16} />
        </button>
      </div>

      {/* Recent History Table */}
      <div className="card">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
          <div>
            <h3 className="card-title">Recent Analysis History</h3>
            <p className="card-subtitle">Real-time records from your SafetyGuard backend</p>
          </div>
          <button
            className="secondary-btn"
            style={{ fontSize: '0.8rem', padding: '4px 10px' }}
            onClick={() => onNavigateTab('history')}
          >
            View All
          </button>
        </div>

        {recent_jobs.length === 0 ? (
          <div style={{ textAlign: 'center', padding: '2.5rem', color: 'var(--text-muted)' }}>
            <Video size={40} style={{ margin: '0 auto 0.75rem', opacity: 0.4 }} />
            <p>No analysis jobs recorded yet. Run your first analysis above!</p>
          </div>
        ) : (
          <div className="data-table-wrapper">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Job ID</th>
                  <th>Source / Title</th>
                  <th>Type</th>
                  <th>Status</th>
                  <th>Candidate Incidents</th>
                  <th>Created At</th>
                  <th>Action</th>
                </tr>
              </thead>
              <tbody>
                {recent_jobs.slice(0, 6).map((job) => (
                  <tr key={job.job_id}>
                    <td style={{ fontFamily: 'monospace', fontSize: '0.8rem' }}>{job.job_id}</td>
                    <td style={{ fontWeight: '500', maxWidth: '300px', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                      {job.video_title || job.source || 'Video Recording'}
                    </td>
                    <td>
                      <span className="badge neutral" style={{ textTransform: 'uppercase', fontSize: '0.65rem' }}>
                        {job.job_type}
                      </span>
                    </td>
                    <td>
                      {job.status === 'completed' && <span className="badge success">Completed</span>}
                      {job.status === 'processing' && <span className="badge warning">Processing {job.progress_pct}%</span>}
                      {job.status === 'queued' && <span className="badge neutral">Queued</span>}
                      {job.status === 'failed' && <span className="badge danger">Failed</span>}
                    </td>
                    <td>
                      {job.incident_count > 0 ? (
                        <span className={`badge ${job.high_priority_count > 0 ? 'danger' : 'warning'}`}>
                          {job.incident_count} flagged ({job.high_priority_count} high)
                        </span>
                      ) : (
                        <span className="badge neutral" style={{ color: 'var(--text-muted)' }}>None flagged</span>
                      )}
                    </td>
                    <td style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
                      {new Date(job.created_at).toLocaleString([], { dateStyle: 'short', timeStyle: 'short' })}
                    </td>
                    <td>
                      <button
                        className="secondary-btn"
                        style={{ fontSize: '0.75rem', padding: '4px 8px' }}
                        onClick={() => onSelectJob(job.job_id)}
                      >
                        Inspect
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}

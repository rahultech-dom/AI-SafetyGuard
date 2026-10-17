import React, { useState } from 'react'
import { History, Download, Eye, Video, AlertTriangle, Flame, CheckCircle2, Search } from 'lucide-react'

export default function HistoryReportsView({ jobs, onSelectJob }) {
  const [search, setSearch] = useState('')

  const filteredJobs = (jobs || []).filter((j) => {
    if (!search.trim()) return true
    const q = search.toLowerCase()
    return (
      j.job_id.toLowerCase().includes(q) ||
      (j.source || '').toLowerCase().includes(q) ||
      (j.video_title || '').toLowerCase().includes(q)
    )
  })

  return (
    <div className="card">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.25rem', flexWrap: 'wrap', gap: '1rem' }}>
        <div>
          <h2 className="card-title">
            <History size={20} color="var(--primary)" />
            Analysis Archive & Reports
          </h2>
          <p className="card-subtitle" style={{ marginBottom: 0 }}>
            Inspect past video screenings, download forensic CSV/JSON records, and check verification logs.
          </p>
        </div>

        <div style={{ position: 'relative', minWidth: '240px' }}>
          <Search size={14} style={{ position: 'absolute', left: '10px', top: '10px', color: 'var(--text-muted)' }} />
          <input
            type="text"
            placeholder="Search jobs by ID or title..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            style={{
              width: '100%',
              padding: '6px 10px 6px 30px',
              borderRadius: '6px',
              border: '1px solid var(--border-color)',
              fontSize: '0.85rem'
            }}
          />
        </div>
      </div>

      {filteredJobs.length === 0 ? (
        <div style={{ textAlign: 'center', padding: '3rem', color: 'var(--text-muted)' }}>
          <Video size={40} style={{ margin: '0 auto 0.75rem', opacity: 0.4 }} />
          <p>No matching video analysis jobs found in the archive.</p>
        </div>
      ) : (
        <div className="data-table-wrapper">
          <table className="data-table">
            <thead>
              <tr>
                <th>Job Identifier</th>
                <th>Video Source / Title</th>
                <th>Type</th>
                <th>Status</th>
                <th>Flagged Intervals</th>
                <th>Created Timestamp</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {filteredJobs.map((j) => (
                <tr key={j.job_id}>
                  <td style={{ fontFamily: 'monospace', fontSize: '0.8rem', fontWeight: 600 }}>
                    {j.job_id}
                  </td>
                  <td style={{ fontWeight: 500, maxWidth: '280px', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                    {j.video_title || j.source || 'Video Recording'}
                  </td>
                  <td>
                    <span className="badge neutral" style={{ textTransform: 'uppercase', fontSize: '0.65rem' }}>
                      {j.job_type}
                    </span>
                  </td>
                  <td>
                    {j.status === 'completed' && <span className="badge success">Completed</span>}
                    {j.status === 'processing' && <span className="badge warning">Processing {j.progress_pct}%</span>}
                    {j.status === 'queued' && <span className="badge neutral">Queued</span>}
                    {j.status === 'failed' && <span className="badge danger">Failed</span>}
                  </td>
                  <td>
                    {j.incident_count > 0 ? (
                      <span className={`badge ${j.high_priority_count > 0 ? 'danger' : 'warning'}`}>
                        {j.incident_count} alerts ({j.high_priority_count} high)
                      </span>
                    ) : (
                      <span className="badge neutral" style={{ color: 'var(--text-muted)' }}>No alerts</span>
                    )}
                  </td>
                  <td style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
                    {new Date(j.created_at).toLocaleString([], { dateStyle: 'short', timeStyle: 'short' })}
                  </td>
                  <td>
                    <div style={{ display: 'flex', gap: '6px' }}>
                      <button
                        className="secondary-btn"
                        style={{ fontSize: '0.75rem', padding: '4px 8px' }}
                        onClick={() => onSelectJob(j.job_id)}
                      >
                        <Eye size={12} /> View
                      </button>
                      {j.status === 'completed' && (
                        <>
                          <a
                            href={`/api/results/${j.job_id}/export?format=csv`}
                            download
                            className="secondary-btn"
                            style={{ fontSize: '0.75rem', padding: '4px 8px' }}
                            title="Download CSV"
                          >
                            <Download size={12} /> CSV
                          </a>
                          <a
                            href={`/api/results/${j.job_id}/export?format=json`}
                            download
                            className="secondary-btn"
                            style={{ fontSize: '0.75rem', padding: '4px 8px' }}
                            title="Download JSON"
                          >
                            <Download size={12} /> JSON
                          </a>
                        </>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}

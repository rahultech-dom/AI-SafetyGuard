import React, { useState, useRef, useEffect } from 'react'
import {
  Play,
  Pause,
  Volume2,
  Clock,
  AlertTriangle,
  Flame,
  CheckCircle2,
  Download,
  Filter,
  Search,
  CheckSquare,
  FileText,
  HelpCircle,
  Activity,
  Mic
} from 'lucide-react'

export default function ResultsPlayerView({ jobResult, onUpdateReview }) {
  const [isPlaying, setIsPlaying] = useState(false)
  const [currentTime, setCurrentTime] = useState(0)
  const [duration, setDuration] = useState(0)
  const [selectedIncident, setSelectedIncident] = useState(null)
  const [severityFilter, setSeverityFilter] = useState('all') // 'all' | 'high' | 'medium'
  const [searchQuery, setSearchQuery] = useState('')
  const [isReviewOpen, setIsReviewOpen] = useState(false)
  const [reviewStatus, setReviewStatus] = useState('Pending Human Review')
  const [reviewNotes, setReviewNotes] = useState('')
  const [submittingReview, setSubmittingReview] = useState(false)

  const videoRef = useRef(null)

  const { job_id, video_metadata = {}, results = {} } = jobResult || {}
  const { summary = {}, incidents = [], timeline_windows = [], transcripts = [] } = results || {}

  const videoFilename = video_metadata.filename || results.video_file || ''
  const videoStreamUrl = videoFilename ? `/api/media/video/${encodeURIComponent(videoFilename)}` : ''

  // Sync video time
  const handleTimeUpdate = () => {
    if (videoRef.current) {
      setCurrentTime(videoRef.current.currentTime)
    }
  }

  const handleLoadedMetadata = () => {
    if (videoRef.current) {
      setDuration(videoRef.current.duration || video_metadata.duration || 0)
    }
  }

  const seekTo = (seconds) => {
    if (videoRef.current) {
      videoRef.current.currentTime = Math.max(0, seconds)
      videoRef.current.play().catch(() => {})
      setIsPlaying(true)
    }
  }

  const togglePlay = () => {
    if (!videoRef.current) return
    if (isPlaying) {
      videoRef.current.pause()
      setIsPlaying(false)
    } else {
      videoRef.current.play().catch(() => {})
      setIsPlaying(true)
    }
  }

  const openReviewModal = (inc) => {
    setSelectedIncident(inc)
    setReviewStatus(inc.review_status || 'Needs Human Review')
    setReviewNotes(inc.human_notes || '')
    setIsReviewOpen(true)
  }

  const handleSaveReview = async () => {
    if (!selectedIncident || !onUpdateReview) return
    setSubmittingReview(true)
    try {
      await onUpdateReview(job_id, selectedIncident.incident_id, reviewStatus, reviewNotes)
      selectedIncident.review_status = reviewStatus
      selectedIncident.human_notes = reviewNotes
      setIsReviewOpen(false)
    } catch (err) {
      alert('Failed to update review status: ' + err.message)
    } finally {
      setSubmittingReview(false)
    }
  }

  // Filter incidents
  const filteredIncidents = incidents.filter((inc) => {
    if (severityFilter !== 'all' && inc.severity !== severityFilter) return false
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase()
      const matchReason = inc.reasons.some((r) => r.toLowerCase().includes(q))
      const matchKw = inc.keywords.some((k) => k.toLowerCase().includes(q))
      const matchStatus = (inc.review_status || '').toLowerCase().includes(q)
      if (!matchReason && !matchKw && !matchStatus) return false
    }
    return true
  })

  // Format seconds to mm:ss
  const formatTime = (secs) => {
    const s = Math.floor(secs || 0)
    const m = Math.floor(s / 60)
    const remainingS = s % 60
    return `${m.toString().padStart(2, '0')}:${remainingS.toString().padStart(2, '0')}`
  }

  if (!jobResult || !results.incidents) {
    return (
      <div className="card" style={{ textAlign: 'center', padding: '3rem' }}>
        <HelpCircle size={44} style={{ color: 'var(--text-muted)', margin: '0 auto 1rem' }} />
        <h3 style={{ fontSize: '1.1rem', fontWeight: 600 }}>No Analysis Results Loaded</h3>
        <p style={{ color: 'var(--text-secondary)', marginTop: '0.5rem' }}>
          Select a completed job from History or initiate a new analysis above.
        </p>
      </div>
    )
  }

  return (
    <div>
      {/* Top Details & Export Bar */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.25rem', flexWrap: 'wrap', gap: '1rem' }}>
        <div>
          <h2 style={{ fontSize: '1.3rem', fontWeight: 700, color: 'var(--text-primary)' }}>
            Analysis: {video_metadata.title || video_metadata.filename || job_id}
          </h2>
          <div style={{ fontSize: '0.825rem', color: 'var(--text-secondary)', display: 'flex', gap: '1rem', marginTop: '2px' }}>
            <span>Duration: {formatTime(video_metadata.duration || duration)}</span>
            <span>Resolution: {video_metadata.width}x{video_metadata.height}</span>
            <span>FPS: {video_metadata.fps}</span>
            <span style={{ color: 'var(--primary)', fontWeight: 600 }}>Job: {job_id}</span>
          </div>
        </div>

        <div style={{ display: 'flex', gap: '0.5rem' }}>
          <a
            href={`/api/results/${job_id}/export?format=csv`}
            download
            className="secondary-btn"
            style={{ fontSize: '0.8rem' }}
          >
            <Download size={14} /> Export CSV
          </a>
          <a
            href={`/api/results/${job_id}/export?format=json`}
            download
            className="secondary-btn"
            style={{ fontSize: '0.8rem' }}
          >
            <Download size={14} /> Export JSON
          </a>
        </div>
      </div>

      {/* Main Results Grid */}
      <div className="results-grid">
        {/* Left Column: Player & Interactive Timeline */}
        <div>
          <div className="card" style={{ padding: '1rem', marginBottom: '1rem' }}>
            <div className="video-player-wrapper">
              {videoStreamUrl ? (
                <video
                  ref={videoRef}
                  className="video-element"
                  src={videoStreamUrl}
                  controls
                  onTimeUpdate={handleTimeUpdate}
                  onLoadedMetadata={handleLoadedMetadata}
                  onPlay={() => setIsPlaying(true)}
                  onPause={() => setIsPlaying(false)}
                />
              ) : (
                <div style={{ height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#94a3b8' }}>
                  Video stream not available
                </div>
              )}
            </div>

            {/* Interactive Timeline Track */}
            <div className="timeline-track-container">
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-secondary)', marginBottom: '4px' }}>
                <span>Interactive Incident Timeline (Click segment to seek)</span>
                <span>Current: {formatTime(currentTime)} / {formatTime(duration)}</span>
              </div>

              <div className="timeline-bars-row">
                {timeline_windows.length > 0 ? (
                  timeline_windows.map((w, idx) => (
                    <div
                      key={idx}
                      className={`timeline-bar-segment ${w.severity}`}
                      title={`${w.start_seconds.toFixed(0)}s: ${w.category} (Score: ${(w.confidence * 100).toFixed(0)}%)`}
                      onClick={() => seekTo(w.start_seconds)}
                    />
                  ))
                ) : (
                  <div style={{ width: '100%', height: '100%', background: '#bbf7d0' }} />
                )}
              </div>

              <div className="timeline-legend">
                <div className="legend-item">
                  <div className="legend-dot high" />
                  <span>High Priority Threat Indicators ({summary.high_priority_count || 0})</span>
                </div>
                <div className="legend-item">
                  <div className="legend-dot medium" />
                  <span>Potential Incident Review ({summary.medium_priority_count || 0})</span>
                </div>
                <div className="legend-item">
                  <div className="legend-dot low" />
                  <span>No Indicator Detected</span>
                </div>
              </div>
            </div>
          </div>

          {/* Audio Transcripts and Distress Snippets */}
          {transcripts.length > 0 && (
            <div className="card">
              <h3 className="card-title" style={{ fontSize: '1rem' }}>
                <Mic size={16} color="var(--primary)" />
                Detected Audio & Speech Intervals
              </h3>
              <div style={{ maxHeight: '180px', overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '6px', marginTop: '0.5rem' }}>
                {transcripts.map((t, idx) => (
                  <div
                    key={idx}
                    style={{
                      padding: '6px 10px',
                      borderRadius: '4px',
                      backgroundColor: t.matched_phrases?.length > 0 ? '#fef2f2' : '#f8fafc',
                      border: t.matched_phrases?.length > 0 ? '1px solid #fecaca' : '1px solid #e2e8f0',
                      fontSize: '0.8rem',
                      display: 'flex',
                      justifyContent: 'space-between',
                      alignItems: 'center',
                      cursor: 'pointer'
                    }}
                    onClick={() => seekTo(t.start_seconds)}
                  >
                    <div>
                      <span style={{ fontWeight: 600, color: 'var(--primary)', marginRight: '8px' }}>
                        [{formatTime(t.start_seconds)} - {formatTime(t.end_seconds)}]
                      </span>
                      <span>"{t.transcript}"</span>
                      {t.matched_phrases?.length > 0 && (
                        <span className="badge danger" style={{ marginLeft: '8px', fontSize: '0.7rem' }}>
                          Distress: {t.matched_phrases.join(', ')}
                        </span>
                      )}
                    </div>
                    <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>
                      {t.service} ({t.language})
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Right Column: Flagged Incidents List */}
        <div>
          <div className="card">
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
              <div>
                <h3 className="card-title">Candidate Incidents</h3>
                <p className="card-subtitle" style={{ marginBottom: 0 }}>
                  {filteredIncidents.length} intervals flagged for human verification
                </p>
              </div>

              {/* Severity Filter */}
              <div style={{ display: 'flex', gap: '4px' }}>
                <select
                  value={severityFilter}
                  onChange={(e) => setSeverityFilter(e.target.value)}
                  style={{
                    padding: '4px 8px',
                    borderRadius: '4px',
                    border: '1px solid var(--border-color)',
                    fontSize: '0.8rem'
                  }}
                >
                  <option value="all">All Severities</option>
                  <option value="high">High Priority</option>
                  <option value="medium">Medium Priority</option>
                </select>
              </div>
            </div>

            {/* Search Bar */}
            <div style={{ position: 'relative', marginBottom: '0.75rem' }}>
              <Search size={14} style={{ position: 'absolute', left: '10px', top: '10px', color: 'var(--text-muted)' }} />
              <input
                type="text"
                placeholder="Search reasons or distress phrases..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                style={{
                  width: '100%',
                  padding: '6px 10px 6px 30px',
                  borderRadius: '6px',
                  border: '1px solid var(--border-color)',
                  fontSize: '0.85rem'
                }}
              />
            </div>

            {/* Incidents Cards */}
            {filteredIncidents.length === 0 ? (
              <div style={{ textAlign: 'center', padding: '2.5rem', color: 'var(--text-muted)', fontSize: '0.9rem' }}>
                <CheckCircle2 size={36} color="var(--success)" style={{ margin: '0 auto 0.5rem' }} />
                No candidate incidents match current filters.
              </div>
            ) : (
              <div className="incidents-list">
                {filteredIncidents.map((inc) => (
                  <div
                    key={inc.incident_id}
                    className={`incident-card ${inc.severity}`}
                    onClick={() => seekTo(inc.start_seconds)}
                  >
                    <div className="incident-card-header">
                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                        <span className="incident-time-badge">
                          {formatTime(inc.start_seconds)} - {formatTime(inc.end_seconds)}
                        </span>
                        <span className={`badge ${inc.severity === 'high' ? 'danger' : 'warning'}`}>
                          {inc.severity === 'high' ? <Flame size={12} /> : <AlertTriangle size={12} />}
                          {inc.severity === 'high' ? 'High Priority' : 'Potential Warning'}
                        </span>
                      </div>

                      <div style={{ fontSize: '0.8rem', fontWeight: 600, color: 'var(--text-secondary)' }}>
                        Conf: {(inc.peak_confidence * 100).toFixed(0)}%
                      </div>
                    </div>

                    <div style={{ fontSize: '0.825rem', fontWeight: 600, color: 'var(--text-primary)' }}>
                      {inc.category}
                    </div>

                    {/* Reasons */}
                    <div>
                      {inc.reasons?.map((r, i) => (
                        <span key={i} className="reason-tag">
                          {r}
                        </span>
                      ))}
                    </div>

                    {/* Keywords if present */}
                    {inc.keywords?.length > 0 && (
                      <div style={{ fontSize: '0.75rem', color: '#b91c1c', display: 'flex', alignItems: 'center', gap: '4px' }}>
                        <Mic size={12} />
                        <strong>Distress Keywords:</strong> {inc.keywords.join(', ')}
                      </div>
                    )}

                    {/* Thumbnail preview if available */}
                    {inc.thumbnail && (
                      <div style={{ marginTop: '4px' }}>
                        <img
                          src={inc.thumbnail}
                          alt="Incident Keyframe"
                          style={{ width: '120px', height: '68px', borderRadius: '4px', objectFit: 'cover', border: '1px solid #cbd5e1' }}
                        />
                      </div>
                    )}

                    {/* Review Status & Action */}
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '6px', paddingTop: '6px', borderTop: '1px dashed #e2e8f0' }}>
                      <span style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
                        Status: <strong>{inc.review_status || 'Pending Review'}</strong>
                      </span>
                      <button
                        className="secondary-btn"
                        style={{ fontSize: '0.7rem', padding: '3px 8px' }}
                        onClick={(e) => {
                          e.stopPropagation()
                          openReviewModal(inc)
                        }}
                      >
                        <CheckSquare size={12} /> Update Review
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Operator Review Modal */}
      {isReviewOpen && selectedIncident && (
        <div className="review-modal-backdrop" onClick={() => setIsReviewOpen(false)}>
          <div className="review-modal" onClick={(e) => e.stopPropagation()}>
            <h3 style={{ fontSize: '1.1rem', fontWeight: 700, marginBottom: '0.5rem' }}>
              Human Incident Verification
            </h3>
            <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', marginBottom: '1rem' }}>
              Interval: {formatTime(selectedIncident.start_seconds)} - {formatTime(selectedIncident.end_seconds)} ({selectedIncident.category})
            </p>

            <div style={{ marginBottom: '1rem' }}>
              <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: 600, marginBottom: '4px' }}>
                Decision Status:
              </label>
              <select
                value={reviewStatus}
                onChange={(e) => setReviewStatus(e.target.value)}
                style={{
                  width: '100%',
                  padding: '8px',
                  borderRadius: '6px',
                  border: '1px solid var(--border-color)',
                  fontSize: '0.9rem'
                }}
              >
                <option value="Confirmed Potential Threat Incident">Confirmed Potential Threat Incident</option>
                <option value="False Positive / Safe Normal Activity">False Positive / Safe Normal Activity</option>
                <option value="Inconclusive / Requires Supervisor Review">Inconclusive / Requires Supervisor Review</option>
                <option value="Pending Human Review">Pending Human Review</option>
              </select>
            </div>

            <div style={{ marginBottom: '1.25rem' }}>
              <label style={{ display: 'block', fontSize: '0.8rem', fontWeight: 600, marginBottom: '4px' }}>
                Investigator Notes:
              </label>
              <textarea
                rows={3}
                value={reviewNotes}
                onChange={(e) => setReviewNotes(e.target.value)}
                placeholder="Document visible context (e.g., horseplay vs struggle, noise source)..."
                style={{
                  width: '100%',
                  padding: '8px',
                  borderRadius: '6px',
                  border: '1px solid var(--border-color)',
                  fontSize: '0.85rem'
                }}
              />
            </div>

            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.5rem' }}>
              <button
                className="secondary-btn"
                onClick={() => setIsReviewOpen(false)}
              >
                Cancel
              </button>
              <button
                className="primary-btn"
                disabled={submittingReview}
                onClick={handleSaveReview}
              >
                {submittingReview ? 'Saving...' : 'Save Decision'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

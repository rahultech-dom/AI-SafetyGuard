import React, { useState, useRef } from 'react'
import {
  UploadCloud,
  Globe,
  FileVideo,
  AlertCircle,
  Play,
  CheckCircle,
  Loader2,
  X,
  Info,
  Zap,
  ShieldCheck,
  ShieldAlert
} from 'lucide-react'

export default function VideoInputView({
  onStartUpload,
  onStartURL,
  onStartSample,
  activeJob,
  isLoading,
  error,
  onClearError
}) {
  const [activeTab, setActiveTab] = useState('samples') // 'samples' | 'upload' | 'url'
  const [selectedFile, setSelectedFile] = useState(null)
  const [fileError, setFileError] = useState('')
  const [videoUrl, setVideoUrl] = useState('')
  const [dragActive, setDragActive] = useState(false)
  const fileInputRef = useRef(null)

  const allowedExtensions = ['.mp4', '.avi', '.mov', '.mkv', '.webm']
  const maxSizeBytes = 250 * 1024 * 1024 // 250MB

  const sampleScenarios = [
    {
      id: 'brawl',
      title: 'Subway Altercation & Brawl',
      category: 'Violent Conflict',
      severity: 'HIGH',
      badgeColor: '#dc2626',
      badgeBg: '#fef2f2',
      description: 'Physical brawl in transit corridor with rapid motion jerk, chaotic spatial flow, and visual altercation.',
      expected: 'High-Priority Threat Alert'
    },
    {
      id: 'fall',
      title: 'Escalator Slip & Fall Incident',
      category: 'Slip & Fall Hazard',
      severity: 'HIGH',
      badgeColor: '#ea580c',
      badgeBg: '#fff7ed',
      description: 'Sudden vertical drop followed by post-fall person immobility. Flags rapid fall safety hazard.',
      expected: 'Fall Hazard Detected'
    },
    {
      id: 'patrol',
      title: 'Hallway Security Patrol',
      category: 'Normal Patrol',
      severity: 'SAFE',
      badgeColor: '#16a34a',
      badgeBg: '#f0fdf4',
      description: 'Routine security officer patrolling commercial hallway at steady pace. Safe baseline verification.',
      expected: 'Safe Baseline (0 False Alarms)'
    },
    {
      id: 'store',
      title: 'Retail Store Counter',
      category: 'Normal Commerce',
      severity: 'SAFE',
      badgeColor: '#16a34a',
      badgeBg: '#f0fdf4',
      description: 'Standard retail transaction and customer dialogue at checkout desk. Safe baseline verification.',
      expected: 'Safe Baseline (0 False Alarms)'
    }
  ]

  const sampleUrlPresets = [
    {
      label: 'CCTV Brawl Stream (.mp4)',
      url: 'https://raw.githubusercontent.com/rahultech-dom/AI-SafetyGuard/main/data/videos/cctv_crime_altercation_brawl.mp4'
    },
    {
      label: 'CCTV Slip & Fall Stream (.mp4)',
      url: 'https://raw.githubusercontent.com/rahultech-dom/AI-SafetyGuard/main/data/videos/cctv_crime_slip_fall.mp4'
    },
    {
      label: 'CCTV Safe Patrol Stream (.mp4)',
      url: 'https://raw.githubusercontent.com/rahultech-dom/AI-SafetyGuard/main/data/videos/cctv_normal_hallway_patrol.mp4'
    }
  ]

  const handleFileSelect = (file) => {
    setFileError('')
    if (onClearError) onClearError()

    if (!file) return

    const ext = '.' + file.name.split('.').pop().toLowerCase()
    if (!allowedExtensions.includes(ext)) {
      setFileError(`Unsupported format "${ext}". Allowed: ${allowedExtensions.join(', ')}`)
      setSelectedFile(null)
      return
    }

    if (file.size > maxSizeBytes) {
      setFileError(`File size (${(file.size / (1024 * 1024)).toFixed(1)}MB) exceeds 250MB limit.`)
      setSelectedFile(null)
      return
    }

    setSelectedFile(file)
  }

  const handleDrag = (e) => {
    e.preventDefault()
    e.stopPropagation()
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true)
    } else if (e.type === 'dragleave') {
      setDragActive(false)
    }
  }

  const handleDrop = (e) => {
    e.preventDefault()
    e.stopPropagation()
    setDragActive(false)
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFileSelect(e.dataTransfer.files[0])
    }
  }

  const handleStartAnalysis = () => {
    if (activeTab === 'upload') {
      if (!selectedFile) {
        setFileError('Please select a video file before starting analysis.')
        return
      }
      onStartUpload(selectedFile)
    } else if (activeTab === 'url') {
      const clean = videoUrl.trim()
      if (!clean) {
        setFileError('Please enter a direct video URL (.mp4, .webm).')
        return
      }
      if (clean.includes('youtube.com') || clean.includes('youtu.be')) {
        setFileError('YouTube links are not supported due to YouTube bot restrictions on cloud servers. Please use 1-Click CCTV Scenarios or upload your video file directly.')
        return
      }
      if (onStartURL) {
        onStartURL(clean)
      }
    }
  }

  const handleRunSample = (sampleId) => {
    if (onClearError) onClearError()
    setFileError('')
    if (onStartSample) {
      onStartSample(sampleId)
    }
  }

  // Stepper calculations
  const progressPct = activeJob?.progress_pct || 0
  const currentStage = activeJob?.current_stage || 'Preparing'
  const isJobRunning = activeJob && (activeJob.status === 'processing' || activeJob.status === 'queued')

  const stages = [
    { label: 'Video Acquisition', min: 0, max: 20 },
    { label: 'Preprocessing & OpenCV', min: 20, max: 40 },
    { label: 'Optical Flow & Jerk', min: 40, max: 65 },
    { label: 'Audio & Distress Speech', min: 65, max: 85 },
    { label: 'Multimodal Fusion & RF', min: 85, max: 100 },
  ]

  return (
    <div>
      {/* Active Analysis Progress Box if Job Running */}
      {isJobRunning && (
        <div className="progress-container">
          <div className="progress-header">
            <span style={{ display: 'flex', alignItems: 'center', gap: '8px', color: 'var(--primary)' }}>
              <Loader2 className="animate-spin" size={18} />
              {currentStage}
            </span>
            <span>{progressPct.toFixed(0)}%</span>
          </div>

          <div className="progress-bar-bg">
            <div className="progress-bar-fill" style={{ width: `${progressPct}%` }} />
          </div>

          <div className="progress-stages-stepper">
            {stages.map((stg, i) => {
              const isCompleted = progressPct >= stg.max
              const isActive = progressPct >= stg.min && progressPct < stg.max
              return (
                <div
                  key={i}
                  className={`stepper-item ${isCompleted ? 'completed' : ''} ${isActive ? 'active' : ''}`}
                >
                  <div style={{ fontWeight: 600 }}>{stg.label}</div>
                  <div style={{ fontSize: '0.65rem' }}>
                    {isCompleted ? '✓ Done' : isActive ? 'In Progress...' : 'Waiting'}
                  </div>
                </div>
              )
            })}
          </div>
        </div>
      )}

      {/* Main Input Card */}
      <div className="card">
        <h2 className="card-title">
          <FileVideo size={20} color="var(--primary)" />
          Video Source Selection
        </h2>
        <p className="card-subtitle">
          Screen surveillance footage, CCTV camera streams, or incident clips for physical altercation, slip & fall, or scream detection.
        </p>

        {/* Tab Selector */}
        <div className="input-tabs">
          <button
            className={`input-tab-btn ${activeTab === 'samples' ? 'active' : ''}`}
            onClick={() => setActiveTab('samples')}
          >
            <Zap size={16} style={{ display: 'inline', marginRight: '6px', verticalAlign: 'text-bottom' }} />
            1-Click CCTV Scenarios (Instant Demo)
          </button>
          <button
            className={`input-tab-btn ${activeTab === 'upload' ? 'active' : ''}`}
            onClick={() => setActiveTab('upload')}
          >
            <UploadCloud size={16} style={{ display: 'inline', marginRight: '6px', verticalAlign: 'text-bottom' }} />
            Local Video File Upload
          </button>
          <button
            className={`input-tab-btn ${activeTab === 'url' ? 'active' : ''}`}
            onClick={() => setActiveTab('url')}
          >
            <Globe size={16} style={{ display: 'inline', marginRight: '6px', verticalAlign: 'text-bottom' }} />
            Direct Video Stream URL (.mp4)
          </button>
        </div>

        {/* Error Alert */}
        {(error || fileError) && (
          <div style={{
            backgroundColor: 'var(--danger-bg)',
            border: '1px solid #fecaca',
            color: 'var(--danger)',
            padding: '0.75rem 1rem',
            borderRadius: 'var(--radius-sm)',
            marginBottom: '1rem',
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            fontSize: '0.85rem'
          }}>
            <AlertCircle size={16} style={{ flexShrink: 0 }} />
            <div style={{ flex: 1 }}>{error || fileError}</div>
            <button onClick={() => { setFileError(''); if (onClearError) onClearError(); }}>
              <X size={16} />
            </button>
          </div>
        )}

        {/* Mode 1: 1-Click CCTV Demo Scenarios */}
        {activeTab === 'samples' && (
          <div>
            <div style={{
              fontSize: '0.85rem',
              color: 'var(--text-secondary)',
              marginBottom: '1rem',
              lineHeight: 1.5
            }}>
              Select any pre-loaded real-world CCTV benchmark clip below for an <strong>instant end-to-end demonstration</strong> of multimodal threat screening, dense optical flow tracking, and AI incident scoring. Works 100% reliably on any device or cloud host.
            </div>

            <div style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))',
              gap: '1rem',
              marginBottom: '0.5rem'
            }}>
              {sampleScenarios.map((scen) => (
                <div
                  key={scen.id}
                  style={{
                    border: '1px solid var(--border-color)',
                    borderRadius: 'var(--radius-md)',
                    padding: '1rem',
                    backgroundColor: 'var(--bg-main)',
                    display: 'flex',
                    flexDirection: 'column',
                    justifyContent: 'space-between',
                    transition: 'all 0.2s ease',
                    boxShadow: '0 1px 3px rgba(0,0,0,0.05)'
                  }}
                >
                  <div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                      <span style={{
                        fontSize: '0.72rem',
                        fontWeight: 700,
                        textTransform: 'uppercase',
                        padding: '3px 8px',
                        borderRadius: '999px',
                        color: scen.badgeColor,
                        backgroundColor: scen.badgeBg,
                        display: 'inline-flex',
                        alignItems: 'center',
                        gap: '4px'
                      }}>
                        {scen.severity === 'HIGH' ? <ShieldAlert size={12} /> : <ShieldCheck size={12} />}
                        {scen.category}
                      </span>
                      <span style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
                        CCTV Clip
                      </span>
                    </div>

                    <h3 style={{ fontSize: '1rem', fontWeight: 600, color: 'var(--text-primary)', marginBottom: '6px' }}>
                      {scen.title}
                    </h3>
                    <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', lineHeight: 1.45, marginBottom: '12px' }}>
                      {scen.description}
                    </p>
                  </div>

                  <div>
                    <div style={{
                      fontSize: '0.75rem',
                      fontWeight: 500,
                      color: scen.severity === 'HIGH' ? '#b91c1c' : '#15803d',
                      marginBottom: '10px'
                    }}>
                      Expected: <strong>{scen.expected}</strong>
                    </div>

                    <button
                      className="primary-btn"
                      style={{ width: '100%', justifyContent: 'center', padding: '0.5rem 1rem', fontSize: '0.85rem' }}
                      disabled={isLoading || isJobRunning}
                      onClick={() => handleRunSample(scen.id)}
                    >
                      {isLoading || isJobRunning ? (
                        <>
                          <Loader2 size={14} className="animate-spin" />
                          Processing...
                        </>
                      ) : (
                        <>
                          <Play size={14} />
                          Run {scen.id === 'brawl' ? 'Brawl' : scen.id === 'fall' ? 'Fall' : 'Patrol'} Demo
                        </>
                      )}
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Mode 2: Local File Upload */}
        {activeTab === 'upload' && (
          <div>
            <input
              type="file"
              ref={fileInputRef}
              style={{ display: 'none' }}
              accept={allowedExtensions.join(',')}
              onChange={(e) => handleFileSelect(e.target.files?.[0])}
            />

            {!selectedFile ? (
              <div
                className={`dropzone ${dragActive ? 'drag-active' : ''}`}
                onDragEnter={handleDrag}
                onDragLeave={handleDrag}
                onDragOver={handleDrag}
                onDrop={handleDrop}
                onClick={() => fileInputRef.current?.click()}
              >
                <UploadCloud size={44} className="dropzone-icon" />
                <div style={{ fontWeight: 600, color: 'var(--text-primary)', marginBottom: '4px' }}>
                  Click to select or drag and drop a video file
                </div>
                <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
                  Supported formats: MP4, AVI, MOV, MKV, WebM (Max: 250MB, Recommended duration: under 10 minutes)
                </div>
              </div>
            ) : (
              <div className="file-preview-bar">
                <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                  <FileVideo size={24} color="var(--primary)" />
                  <div>
                    <div style={{ fontWeight: 600, fontSize: '0.9rem' }}>{selectedFile.name}</div>
                    <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
                      {(selectedFile.size / (1024 * 1024)).toFixed(2)} MB
                    </div>
                  </div>
                </div>
                <button
                  className="secondary-btn"
                  style={{ padding: '4px 10px', fontSize: '0.8rem' }}
                  onClick={() => { setSelectedFile(null); if (fileInputRef.current) fileInputRef.current.value = ''; }}
                >
                  Change File
                </button>
              </div>
            )}

            <div style={{ marginTop: '1.5rem', display: 'flex', justifyContent: 'flex-end' }}>
              <button
                className="primary-btn"
                disabled={isLoading || isJobRunning}
                onClick={handleStartAnalysis}
              >
                {isLoading || isJobRunning ? (
                  <>
                    <Loader2 size={16} className="animate-spin" />
                    Processing Pipeline...
                  </>
                ) : (
                  <>
                    <Play size={16} />
                    Initiate SafetyGuard Analysis
                  </>
                )}
              </button>
            </div>
          </div>
        )}

        {/* Mode 3: Direct Video Stream URL */}
        {activeTab === 'url' && (
          <div>
            <div style={{
              backgroundColor: '#eff6ff',
              border: '1px solid #bfdbfe',
              color: '#1e40af',
              padding: '0.85rem 1rem',
              borderRadius: 'var(--radius-sm)',
              marginBottom: '1rem',
              display: 'flex',
              alignItems: 'flex-start',
              gap: '10px',
              fontSize: '0.82rem',
              lineHeight: '1.5'
            }}>
              <Info size={16} style={{ flexShrink: 0, marginTop: '2px' }} />
              <div>
                <strong>Direct Video Stream Support:</strong> Paste any direct video stream URL (<code>.mp4</code>, <code>.webm</code>, AWS S3, GitHub raw, Cloudflare, CDN, or surveillance stream). Direct video streams download universally across all cloud servers with zero bot restrictions.
              </div>
            </div>

            <div className="url-input-group">
              <input
                type="url"
                className="url-input"
                placeholder="https://example.com/cctv_footage.mp4"
                value={videoUrl}
                onChange={(e) => {
                  setVideoUrl(e.target.value)
                  if (fileError) setFileError('')
                }}
              />
            </div>

            {/* Quick Presets */}
            <div style={{ marginTop: '0.75rem' }}>
              <span style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-secondary)', marginRight: '8px' }}>
                Quick Fill Direct Stream Links:
              </span>
              <div style={{ display: 'inline-flex', flexWrap: 'wrap', gap: '6px', marginTop: '4px' }}>
                {sampleUrlPresets.map((preset, idx) => (
                  <button
                    key={idx}
                    type="button"
                    style={{
                      fontSize: '0.75rem',
                      padding: '3px 8px',
                      background: 'var(--bg-main)',
                      border: '1px solid var(--border-color)',
                      borderRadius: '4px',
                      color: 'var(--primary)',
                      cursor: 'pointer'
                    }}
                    onClick={() => {
                      setVideoUrl(preset.url)
                      if (fileError) setFileError('')
                    }}
                  >
                    {preset.label}
                  </button>
                ))}
              </div>
            </div>

            <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginTop: '8px' }}>
              Supported formats: Direct MP4, WebM, MKV, AVI.
            </div>

            <div style={{ marginTop: '1.5rem', display: 'flex', justifyContent: 'flex-end' }}>
              <button
                className="primary-btn"
                disabled={isLoading || isJobRunning}
                onClick={handleStartAnalysis}
              >
                {isLoading || isJobRunning ? (
                  <>
                    <Loader2 size={16} className="animate-spin" />
                    Processing Pipeline...
                  </>
                ) : (
                  <>
                    <Play size={16} />
                    Analyze Video Stream
                  </>
                )}
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

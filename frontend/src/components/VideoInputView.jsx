import React, { useState, useRef } from 'react'
import {
  UploadCloud,
  Globe,
  FileVideo,
  AlertCircle,
  Play,
  CheckCircle,
  Loader2,
  X
} from 'lucide-react'

export default function VideoInputView({
  onStartUpload,
  onStartYouTube,
  activeJob,
  isLoading,
  error,
  onClearError
}) {
  const [activeTab, setActiveTab] = useState('upload') // 'upload' | 'youtube'
  const [selectedFile, setSelectedFile] = useState(null)
  const [fileError, setFileError] = useState('')
  const [youtubeUrl, setYoutubeUrl] = useState('')
  const [dragActive, setDragActive] = useState(false)
  const fileInputRef = useRef(null)

  const allowedExtensions = ['.mp4', '.avi', '.mov', '.mkv', '.webm']
  const maxSizeBytes = 250 * 1024 * 1024 // 250MB

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
    } else {
      if (!youtubeUrl.trim()) {
        setFileError('Please enter a YouTube video URL.')
        return
      }
      onStartYouTube(youtubeUrl.trim())
    }
  }

  // Stepper calculations
  const progressPct = activeJob?.progress_pct || 0
  const currentStage = activeJob?.current_stage || 'Preparing'
  const isJobRunning = activeJob && (activeJob.status === 'processing' || activeJob.status === 'queued')

  const stages = [
    { label: 'Upload / Download', min: 0, max: 20 },
    { label: 'Video Preprocessing', min: 20, max: 40 },
    { label: 'Optical Flow & Motion', min: 40, max: 65 },
    { label: 'Audio & Distress Words', min: 65, max: 85 },
    { label: 'Multimodal Fusion & ML', min: 85, max: 100 },
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
          Submit CCTV footage, surveillance clips, or public YouTube streams for observable threat screening.
        </p>

        {/* Tab Selector */}
        <div className="input-tabs">
          <button
            className={`input-tab-btn ${activeTab === 'upload' ? 'active' : ''}`}
            onClick={() => setActiveTab('upload')}
          >
            <UploadCloud size={16} style={{ display: 'inline', marginRight: '6px', verticalAlign: 'text-bottom' }} />
            Local Video File Upload
          </button>
          <button
            className={`input-tab-btn ${activeTab === 'youtube' ? 'active' : ''}`}
            onClick={() => setActiveTab('youtube')}
          >
            <Globe size={16} style={{ display: 'inline', marginRight: '6px', verticalAlign: 'text-bottom' }} />
            Public YouTube Video Link
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

        {/* Upload Mode */}
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
          </div>
        )}

        {/* YouTube Mode */}
        {activeTab === 'youtube' && (
          <div>
            <div className="url-input-group">
              <input
                type="url"
                className="url-input"
                placeholder="https://www.youtube.com/watch?v=..."
                value={youtubeUrl}
                onChange={(e) => setYoutubeUrl(e.target.value)}
              />
            </div>
            <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginTop: '6px' }}>
              Only publicly accessible YouTube URLs are supported. Age-restricted, private, or copyrighted streams cannot be extracted.
            </div>
          </div>
        )}

        {/* Start Button */}
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
    </div>
  )
}

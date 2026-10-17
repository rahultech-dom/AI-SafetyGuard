import React, { useState, useEffect, useRef } from 'react'
import Header from './components/Header'
import DashboardView from './components/DashboardView'
import VideoInputView from './components/VideoInputView'
import ResultsPlayerView from './components/ResultsPlayerView'
import HistoryReportsView from './components/HistoryReportsView'
import ModelEvaluationView from './components/ModelEvaluationView'

export default function App() {
  const [currentTab, setCurrentTab] = useState('dashboard') // 'dashboard' | 'analyze' | 'results' | 'history' | 'evaluation'
  const [stats, setStats] = useState({
    total_videos_analyzed: 0,
    running_jobs: 0,
    total_incidents_flagged: 0,
    high_priority_incidents: 0,
    recent_jobs: []
  })
  const [activeJobId, setActiveJobId] = useState(null)
  const [activeJob, setActiveJob] = useState(null)
  const [currentJobResult, setCurrentJobResult] = useState(null)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState('')

  const pollingTimerRef = useRef(null)

  // Fetch dashboard stats
  const fetchStats = async () => {
    try {
      const res = await fetch('/api/stats')
      if (res.ok) {
        const data = await res.json()
        setStats(data)
      }
    } catch (err) {
      console.warn('Could not fetch stats:', err)
    }
  }

  useEffect(() => {
    fetchStats()
    const timer = setInterval(fetchStats, 10000)
    return () => clearInterval(timer)
  }, [])

  // Poll active job status
  useEffect(() => {
    if (!activeJobId) return

    const pollJob = async () => {
      try {
        const res = await fetch(`/api/jobs/${activeJobId}`)
        if (res.ok) {
          const data = await res.json()
          setActiveJob(data)

          if (data.status === 'completed') {
            clearInterval(pollingTimerRef.current)
            pollingTimerRef.current = null
            fetchJobResults(activeJobId)
            fetchStats()
          } else if (data.status === 'failed') {
            clearInterval(pollingTimerRef.current)
            pollingTimerRef.current = null
            setError(data.error || 'Video analysis failed')
            fetchStats()
          }
        }
      } catch (err) {
        console.warn('Error polling job:', err)
      }
    }

    pollJob()
    pollingTimerRef.current = setInterval(pollJob, 1500)

    return () => {
      if (pollingTimerRef.current) {
        clearInterval(pollingTimerRef.current)
        pollingTimerRef.current = null
      }
    }
  }, [activeJobId])

  // Fetch full results for a job and switch to results player tab
  const fetchJobResults = async (jobId) => {
    try {
      const res = await fetch(`/api/results/${jobId}`)
      if (res.ok) {
        const data = await res.json()
        setCurrentJobResult(data)
        setCurrentTab('results')
      }
    } catch (err) {
      setError('Failed to fetch job results: ' + err.message)
    }
  }

  // Handle local file upload
  const handleStartUpload = async (file) => {
    setIsLoading(true)
    setError('')
    try {
      const formData = new FormData()
      formData.append('file', file)

      const res = await fetch('/api/analyze/upload', {
        method: 'POST',
        body: formData,
      })

      if (!res.ok) {
        const errData = await res.json().catch(() => ({}))
        throw new Error(errData.detail || `Upload failed with HTTP ${res.status}`)
      }

      const data = await res.json()
      setActiveJobId(data.job_id)
      fetchStats()
    } catch (err) {
      setError(err.message)
    } finally {
      setIsLoading(false)
    }
  }

  // Handle YouTube analysis
  const handleStartYouTube = async (url) => {
    setIsLoading(true)
    setError('')
    try {
      const res = await fetch('/api/analyze/youtube', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url }),
      })

      if (!res.ok) {
        const errData = await res.json().catch(() => ({}))
        throw new Error(errData.detail || `YouTube analysis failed with HTTP ${res.status}`)
      }

      const data = await res.json()
      setActiveJobId(data.job_id)
      fetchStats()
    } catch (err) {
      setError(err.message)
    } finally {
      setIsLoading(false)
    }
  }

  // Update human review decision
  const handleUpdateReview = async (jobId, incidentId, reviewStatus, humanNotes) => {
    const res = await fetch(`/api/results/${jobId}/review`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        incident_id: incidentId,
        review_status: reviewStatus,
        human_notes: humanNotes,
      }),
    })
    if (!res.ok) {
      const err = await res.json().catch(() => ({}))
      throw new Error(err.detail || 'Failed to update review status')
    }
    fetchStats()
  }

  return (
    <div className="app-container">
      <Header
        currentTab={currentTab}
        onSelectTab={setCurrentTab}
        runningJobCount={stats.running_jobs || 0}
      />

      <main className="main-content">
        {currentTab === 'dashboard' && (
          <DashboardView
            stats={stats}
            onNavigateTab={setCurrentTab}
            onSelectJob={fetchJobResults}
          />
        )}

        {currentTab === 'analyze' && (
          <VideoInputView
            onStartUpload={handleStartUpload}
            onStartYouTube={handleStartYouTube}
            activeJob={activeJob}
            isLoading={isLoading}
            error={error}
            onClearError={() => setError('')}
          />
        )}

        {currentTab === 'results' && (
          <ResultsPlayerView
            jobResult={currentJobResult}
            onUpdateReview={handleUpdateReview}
          />
        )}

        {currentTab === 'history' && (
          <HistoryReportsView
            jobs={stats.recent_jobs}
            onSelectJob={fetchJobResults}
          />
        )}

        {currentTab === 'evaluation' && (
          <ModelEvaluationView />
        )}
      </main>

      <footer className="app-footer">
        <div>
          <strong>AI SafetyGuard</strong> &bull; Multimodal Threat Screening & Computer Vision Pipeline &bull; Local & Offline-First Privacy Architecture
        </div>
      </footer>
    </div>
  )
}

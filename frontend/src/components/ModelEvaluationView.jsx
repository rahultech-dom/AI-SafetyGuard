import React, { useState, useEffect } from 'react'
import {
  BarChart3,
  ShieldCheck,
  AlertOctagon,
  RefreshCw,
  Cpu,
  Layers,
  CheckCircle,
  HelpCircle,
  Sliders
} from 'lucide-react'

export default function ModelEvaluationView() {
  const [evalData, setEvalData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const fetchEvaluation = async () => {
    setLoading(true)
    setError('')
    try {
      const res = await fetch('/api/ml/evaluation')
      if (!res.ok) throw new Error(`HTTP ${res.status}: Failed to fetch evaluation`)
      const data = await res.json()
      setEvalData(data)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchEvaluation()
  }, [])

  const {
    model_type = 'random_forest',
    calibrated_threshold = 0.5,
    test_samples = 0,
    test_distinct_videos = 0,
    metrics = {},
    confusion_matrix = {},
    operational_diagnostics = {},
    per_category_breakdown = {}
  } = evalData || {}

  const {
    accuracy = 0,
    precision = 0,
    recall = 0,
    f1_score = 0,
    roc_auc = 0
  } = metrics

  const {
    true_negatives = 0,
    false_positives = 0,
    false_negatives = 0,
    true_positives = 0
  } = confusion_matrix

  return (
    <div>
      {/* Top Banner */}
      <div className="card" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', background: 'linear-gradient(135deg, #f8fafc 0%, #ffffff 100%)' }}>
        <div>
          <h2 className="card-title">
            <BarChart3 size={20} color="var(--primary)" />
            Scientific Evaluation & ML Model Diagnostics
          </h2>
          <p className="card-subtitle" style={{ marginBottom: 0 }}>
            Evaluation performed on an independent, strictly grouped test set (split by source video ID to prevent temporal leakage).
          </p>
        </div>
        <button
          className="secondary-btn"
          onClick={fetchEvaluation}
          disabled={loading}
          style={{ fontSize: '0.8rem' }}
        >
          <RefreshCw size={14} className={loading ? 'animate-spin' : ''} />
          Re-evaluate
        </button>
      </div>

      {error && (
        <div style={{ padding: '1rem', background: 'var(--danger-bg)', color: 'var(--danger)', borderRadius: '8px', marginBottom: '1rem' }}>
          {error}
        </div>
      )}

      {/* Metrics Row */}
      <div className="stats-grid">
        <div className="stat-card">
          <div className="stat-icon blue">
            <ShieldCheck size={24} />
          </div>
          <div>
            <div className="stat-value">{(f1_score * 100).toFixed(1)}%</div>
            <div className="stat-label">Harmonic F1-Score</div>
          </div>
        </div>

        <div className="stat-card">
          <div className="stat-icon green">
            <CheckCircle size={24} />
          </div>
          <div>
            <div className="stat-value">{(precision * 100).toFixed(1)}%</div>
            <div className="stat-label">Model Precision (Few False Alarms)</div>
          </div>
        </div>

        <div className="stat-card">
          <div className="stat-icon amber">
            <Layers size={24} />
          </div>
          <div>
            <div className="stat-value">{(recall * 100).toFixed(1)}%</div>
            <div className="stat-label">Recall (Threat Sensitivity)</div>
          </div>
        </div>

        <div className="stat-card">
          <div className="stat-icon blue">
            <Cpu size={24} />
          </div>
          <div>
            <div className="stat-value">{operational_diagnostics.latency_per_window_ms || 0} ms</div>
            <div className="stat-label">Inference Latency / 1s Window</div>
          </div>
        </div>
      </div>

      {/* Details & Confusion Matrix */}
      <div className="results-grid">
        {/* Left: Confusion Matrix & Diagnostics */}
        <div className="card">
          <h3 className="card-title">Test Set Confusion Matrix</h3>
          <p className="card-subtitle">
            Evaluated on {test_samples} time windows across {test_distinct_videos} separate video sequences.
          </p>

          <div className="confusion-matrix-grid">
            <div />
            <div style={{ textAlign: 'center', fontWeight: 600, fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
              Predicted: Normal (0)
            </div>
            <div style={{ textAlign: 'center', fontWeight: 600, fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
              Predicted: Threat Alert (1)
            </div>

            <div style={{ fontWeight: 600, fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
              Actual: Normal
            </div>
            <div className="cm-cell">
              <div style={{ fontSize: '1.25rem', fontWeight: 700, color: 'var(--success)' }}>
                {true_negatives}
              </div>
              <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>True Negatives (TN)</div>
            </div>
            <div className="cm-cell highlight">
              <div style={{ fontSize: '1.25rem', fontWeight: 700, color: 'var(--warning)' }}>
                {false_positives}
              </div>
              <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>False Positives (FP)</div>
            </div>

            <div style={{ fontWeight: 600, fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
              Actual: Threat
            </div>
            <div className="cm-cell highlight">
              <div style={{ fontSize: '1.25rem', fontWeight: 700, color: 'var(--danger)' }}>
                {false_negatives}
              </div>
              <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>False Negatives (FN)</div>
            </div>
            <div className="cm-cell">
              <div style={{ fontSize: '1.25rem', fontWeight: 700, color: 'var(--primary)' }}>
                {true_positives}
              </div>
              <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>True Positives (TP)</div>
            </div>
          </div>

          <div style={{ marginTop: '1.25rem', padding: '0.75rem', background: 'var(--bg-subtle)', borderRadius: '6px', fontSize: '0.85rem' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '4px' }}>
              <span>ROC-AUC Discriminability:</span>
              <strong>{(roc_auc * 100).toFixed(1)}%</strong>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '4px' }}>
              <span>Estimated False Alarms per Hour:</span>
              <strong>{operational_diagnostics.false_positives_per_hour || 0} alerts / hr</strong>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span>Calibrated Decision Threshold:</span>
              <strong>{calibrated_threshold}</strong>
            </div>
          </div>
        </div>

        {/* Right: Technical Provenance & Safety Constraints */}
        <div className="card">
          <h3 className="card-title">
            <AlertOctagon size={18} color="var(--danger)" />
            Safety Constraints & Known Limitations
          </h3>
          <p className="card-subtitle">
            Ethical guidelines and technical boundary conditions for this student project.
          </p>

          <ul style={{ paddingLeft: '1.25rem', fontSize: '0.85rem', color: 'var(--text-secondary)', display: 'flex', flexDirection: 'column', gap: '0.6rem' }}>
            <li>
              <strong>Non-Deterministic Crime Detection:</strong> Optical flow acceleration and acoustic energy bursts detect observable anomalies (sudden changes in motion vectors, elevated volume, distress keywords). They cannot infer legal culpability or intent.
            </li>
            <li>
              <strong>High Motion vs Violence:</strong> Fast athletic activities (sprinting, rhythmic dancing, camera pans) can generate high motion scores. The pipeline incorporates spatial concentration and directional chaos to mitigate false alarms, but human operator confirmation remains mandatory.
            </li>
            <li>
              <strong>Data Leakage Prevention:</strong> Dataset splits are grouped strictly by <code>video_id</code> so that consecutive frames of the same video never appear in both train and test splits.
            </li>
            <li>
              <strong>Speech Recognition Limitations:</strong> Speech-to-text models can miss muffled or distorted distress cries in noisy environments, or falsely trigger on casual speech.
            </li>
            <li>
              <strong>Privacy & Offline Processing:</strong> Videos and acoustic features are processed locally without unauthorized cloud streaming.
            </li>
          </ul>
        </div>
      </div>
    </div>
  )
}

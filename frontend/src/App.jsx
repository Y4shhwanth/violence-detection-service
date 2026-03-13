import { useState, useEffect } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import Layout from './components/Layout'
import UploadSection from './components/UploadSection'
import AnalysisProgress from './components/AnalysisProgress'
import ResultsBanner from './components/ResultsBanner'
import ConfidenceMeter from './components/ConfidenceMeter'
import ViolationTimeline from './components/ViolationTimeline'
import ModalityBreakdown from './components/ModalityBreakdown'
import ExplanationPanel from './components/ExplanationPanel'
import ModalityContributions from './components/ModalityContributions'
import ViolenceHeatmap from './components/ViolenceHeatmap'
import FrameEvidenceGallery from './components/FrameEvidenceGallery'
import ModerationDashboard from './components/ModerationDashboard'
import RiskGauge from './components/RiskGauge'
import AIChatAssistant from './components/AIChatAssistant'
import FeedbackPanel from './components/FeedbackPanel'
import ExportButton from './components/ExportButton'
import LiveMonitoring from './components/LiveMonitoring'
import PipelineVisualization from './components/PipelineVisualization'
import AnalysisHistory from './components/AnalysisHistory'
import GlassCard from './components/ui/GlassCard'
import { Card, CardContent } from './components/ui/Card'
import { Spotlight } from './components/ui/Spotlight'
import { SplineScene } from './components/ui/SplineScene'
import { ContainerScroll } from './components/ui/ContainerScroll'
import { useAnalysis } from './hooks/useAnalysis'
import { useAnalysisHistory } from './hooks/useAnalysisHistory'

export default function App() {
  const [view, setView] = useState('analyze')
  const { results, loading, error, uploadProgress, analyze, reset, isAsync, currentStep, asyncProgress } = useAnalysis()
  const { history, addResult, getStats } = useAnalysisHistory()

  // Save results to history when analysis completes
  useEffect(() => {
    if (results?.success) {
      addResult(results)
    }
  }, [results, addResult])

  return (
    <Layout>
      <div className="grid gap-6">
        {/* View toggle */}
        <div className="flex gap-2 p-1 rounded-xl glass-card-strong gradient-border w-fit mx-auto">
          {[
            { id: 'analyze', label: 'Analyze', icon: 'M13 10V3L4 14h7v7l9-11h-7z' },
            { id: 'dashboard', label: 'Dashboard', icon: 'M4 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2V6zm10 0a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2V6zM4 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2v-2zm10 0a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2v-2z' },
            { id: 'live', label: 'Live Monitor', icon: 'M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z' },
            { id: 'history', label: 'History', icon: 'M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z' },
          ].map(btn => (
            <button
              key={btn.id}
              onClick={() => setView(btn.id)}
              className={`relative flex items-center gap-2 py-2.5 px-5 rounded-lg text-xs font-medium transition-all duration-300
                ${view === btn.id ? 'text-white' : 'text-white/30 hover:text-white/60'}`}
            >
              {view === btn.id && (
                <motion.div
                  layoutId="activeView"
                  className="absolute inset-0 rounded-lg"
                  style={{
                    background: 'linear-gradient(135deg, rgba(239,68,68,0.12), rgba(139,92,246,0.08))',
                    border: '1px solid rgba(239,68,68,0.2)',
                    boxShadow: '0 0 20px rgba(239,68,68,0.08), inset 0 1px 0 rgba(255,255,255,0.05)',
                  }}
                  transition={{ type: 'spring', stiffness: 400, damping: 30 }}
                />
              )}
              <svg className="w-3.5 h-3.5 relative z-10" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d={btn.icon} />
              </svg>
              <span className="relative z-10">{btn.label}</span>
            </button>
          ))}
        </div>

        {/* Dashboard view */}
        {view === 'dashboard' && (
          <ContainerScroll
            titleComponent={
              <h2 className="text-2xl md:text-4xl font-bold">
                <span className="gradient-text">Moderation Dashboard</span>
              </h2>
            }
          >
            <ModerationDashboard getStats={getStats} historyCount={history.length} />
          </ContainerScroll>
        )}

        {/* Live Monitor view */}
        {view === 'live' && <LiveMonitoring />}

        {/* History view */}
        {view === 'history' && <AnalysisHistory history={history} />}

        {/* Analyze view */}
        {view === 'analyze' && (
          <>
            {/* Spline hero card — visible before analysis starts */}
            {!results && !loading && (
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -20 }}
                transition={{ duration: 0.5 }}
              >
                <Card className="relative overflow-hidden min-h-[280px] md:min-h-[320px]">
                  <Spotlight className="-top-40 left-0 md:left-60 md:-top-20" fill="rgba(239, 68, 68, 0.15)" />
                  <div className="flex flex-col md:flex-row h-full">
                    <CardContent className="flex-1 flex flex-col justify-center p-8 md:p-12 relative z-10">
                      <h2 className="text-3xl md:text-4xl font-bold mb-4">
                        <span className="gradient-text">AI-Powered</span>
                        <br />
                        <span className="text-white/90">Content Safety</span>
                      </h2>
                      <p className="text-sm md:text-base text-white/40 max-w-md leading-relaxed">
                        Upload video, audio, or text content for real-time violence detection
                        powered by multimodal AI fusion analysis.
                      </p>
                    </CardContent>
                    <div className="flex-1 relative min-h-[200px]">
                      <SplineScene
                        scene="https://prod.spline.design/kZDDjO5HuC9GJUM2/scene.splinecode"
                        className="w-full h-full"
                      />
                    </div>
                  </div>
                </Card>
              </motion.div>
            )}

            <UploadSection onAnalyze={analyze} loading={loading} />

            {/* Loading state */}
            <AnimatePresence>
              {loading && (
                isAsync
                  ? <PipelineVisualization currentStep={currentStep} progress={asyncProgress} />
                  : <AnalysisProgress progress={uploadProgress} />
              )}
            </AnimatePresence>

            {/* Error */}
            <AnimatePresence>
              {error && (
                <motion.div
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0 }}
                  className="glass-card p-4 glow-border-red"
                >
                  <div className="flex items-center gap-3">
                    <div className="w-8 h-8 rounded-lg bg-red-500/10 flex items-center justify-center flex-shrink-0">
                      <svg className="w-4 h-4 text-red-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                      </svg>
                    </div>
                    <div className="flex-1">
                      <p className="text-sm text-red-400">{error}</p>
                    </div>
                    <button onClick={reset} className="text-xs text-white/40 hover:text-white transition-colors px-3 py-1.5 rounded-lg border border-white/[0.08] hover:border-white/[0.15]">
                      Retry
                    </button>
                  </div>
                </motion.div>
              )}
            </AnimatePresence>

            {/* Results */}
            <AnimatePresence>
              {results && results.success && (
                <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="space-y-6">
                  <ResultsBanner
                    decision={results.final_decision || (results.fused_prediction?.class === 'Violence' ? 'Violation' : 'Verified')}
                    confidence={results.confidence || results.fused_prediction?.confidence || 0}
                    message={results.message}
                  />

                  <div className="grid md:grid-cols-3 gap-6">
                    <GlassCard className="md:col-span-1 flex items-center justify-center">
                      <ConfidenceMeter
                        score={results.confidence || results.fused_prediction?.confidence || 0}
                        label="Overall"
                      />
                    </GlassCard>
                    <div className="md:col-span-2">
                      <ModalityBreakdown
                        video={results.video_prediction}
                        audio={results.audio_prediction}
                        text={results.text_prediction}
                        fused={results.fused_prediction}
                      />
                    </div>
                  </div>

                  {results.risk_score && <RiskGauge riskData={results.risk_score} />}

                  {results.modality_contributions && (
                    <ModalityContributions contributions={results.modality_contributions} />
                  )}

                  <ViolenceHeatmap violations={results.violations} />

                  <FrameEvidenceGallery violentFrames={results.video_prediction?.violent_frames} />

                  <ViolationTimeline violations={results.violations} />

                  <ExplanationPanel
                    explanation={results.structured_explanation}
                    severity={results.severity}
                    falsePositive={results.false_positive_analysis}
                    recommendedAction={results.recommended_action}
                  />

                  <AIChatAssistant analysisId={results.job_id} analysisData={results} />

                  {results.job_id && (
                    <div className="flex items-center gap-4">
                      <div className="flex-1"><FeedbackPanel jobId={results.job_id} /></div>
                      <ExportButton jobId={results.job_id} />
                    </div>
                  )}

                  {results.processing_time_ms && (
                    <p className="text-xs text-white/20 text-center">
                      Processed in {(results.processing_time_ms / 1000).toFixed(1)}s
                    </p>
                  )}

                  <details className="glass-card overflow-hidden">
                    <summary className="px-5 py-3 text-xs text-white/30 cursor-pointer hover:text-white/50 transition-colors">
                      Raw API Response
                    </summary>
                    <pre className="px-5 pb-4 text-xs text-white/20 overflow-x-auto max-h-96">
                      {JSON.stringify(results, null, 2)}
                    </pre>
                  </details>

                  <motion.button
                    whileHover={{ scale: 1.01 }}
                    whileTap={{ scale: 0.99 }}
                    onClick={reset}
                    className="w-full py-3 rounded-xl text-sm font-medium text-white/40
                      border border-white/[0.08] hover:border-white/[0.15] hover:text-white/70 transition-all"
                  >
                    Analyze Another
                  </motion.button>
                </motion.div>
              )}
            </AnimatePresence>
          </>
        )}
      </div>
    </Layout>
  )
}

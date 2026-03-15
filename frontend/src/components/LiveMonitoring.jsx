import { useState, useRef, useEffect, useCallback } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import GlassCard from './ui/GlassCard'
import AnimatedCounter from './ui/AnimatedCounter'
import { animation } from '../design/tokens'

function DetectionEntry({ entry }) {
  const color = entry.violence_detected
    ? entry.confidence >= 70 ? 'text-red-400' : 'text-yellow-400'
    : 'text-green-400'

  return (
    <div className="flex items-center gap-2 text-xs py-1.5 border-b border-white/[0.04] last:border-0">
      <span className="text-white/20 w-16">{entry.timestamp}</span>
      <span className={`w-1.5 h-1.5 rounded-full ${
        entry.violence_detected
          ? entry.confidence >= 70 ? 'bg-red-500' : 'bg-yellow-500'
          : 'bg-green-500'
      }`} />
      <span className={color}>
        {entry.violence_detected ? 'Violence' : 'Safe'}
      </span>
      <span className="text-white/30 ml-auto">{entry.confidence.toFixed(0)}%</span>
    </div>
  )
}

function ProbabilityMeter({ value }) {
  const getColor = (v) => {
    if (v >= 70) return '#dc2626'
    if (v >= 40) return '#eab308'
    return '#22c55e'
  }
  const color = getColor(value)

  return (
    <div className="space-y-1.5">
      <div className="flex justify-between text-xs">
        <span className="text-white/35">Violence Probability</span>
        <span style={{ color }} className="font-medium">{value.toFixed(0)}%</span>
      </div>
      <div className="h-3 bg-white/[0.04] rounded-full overflow-hidden">
        <motion.div
          className="h-full rounded-full"
          style={{ background: `linear-gradient(90deg, ${color}80, ${color})` }}
          animate={{ width: `${Math.min(100, value)}%` }}
          transition={{ duration: 0.3 }}
        />
      </div>
    </div>
  )
}

export default function LiveMonitoring() {
  const [isActive, setIsActive] = useState(false)
  const [socket, setSocket] = useState(null)
  const [sessionId, setSessionId] = useState(null)
  const [currentScore, setCurrentScore] = useState(0)
  const [detections, setDetections] = useState([])
  const [alerts, setAlerts] = useState([])
  const [status, setStatus] = useState('idle')
  const [error, setError] = useState(null)
  const [stats, setStats] = useState({ frames: 0, detections: 0, alerts: 0 })

  const videoRef = useRef(null)
  const streamRef = useRef(null)
  const canvasRef = useRef(null)
  const intervalRef = useRef(null)
  const MAX_HISTORY = 50

  const connectSocket = useCallback(async () => {
    try {
      const { io } = await import('socket.io-client')
      const sock = io(import.meta.env.VITE_API_URL || 'https://violence-detection-service.onrender.com', {
        path: '/socket.io',
        transports: ['websocket', 'polling'],
      })

      sock.on('connect', () => { setStatus('connected'); setError(null) })
      sock.on('detection_result', (data) => {
        setCurrentScore(data.confidence || 0)
        setDetections(prev => [data, ...prev].slice(0, MAX_HISTORY))
        setStats(prev => ({ ...prev, detections: prev.detections + 1 }))
      })
      sock.on('live_alert', (data) => {
        setAlerts(prev => [data, ...prev].slice(0, 20))
        setStats(prev => ({ ...prev, alerts: prev.alerts + 1 }))
      })
      sock.on('live_status', (data) => {
        setStatus(data.status)
        if (data.session_id) setSessionId(data.session_id)
        if (data.error) setError(data.error)
      })
      sock.on('disconnect', () => setStatus('disconnected'))
      sock.on('connect_error', (err) => {
        setError(`Connection failed: ${err.message}`)
        setStatus('error')
      })

      setSocket(sock)
      return sock
    } catch (err) {
      setError('WebSocket library not available.')
      return null
    }
  }, [])

  const startMonitoring = async () => {
    setError(null)
    setDetections([])
    setAlerts([])
    setStats({ frames: 0, detections: 0, alerts: 0 })

    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { width: 640, height: 480, facingMode: 'user' },
        audio: false,
      })
      streamRef.current = stream

      if (videoRef.current) {
        videoRef.current.srcObject = stream
        // Wait for video metadata to load before playing
        await new Promise((resolve) => {
          videoRef.current.onloadedmetadata = () => {
            videoRef.current.play().then(resolve).catch(resolve)
          }
          // Fallback if metadata already loaded
          if (videoRef.current.readyState >= 1) {
            videoRef.current.play().then(resolve).catch(resolve)
          }
        })
      }

      const sock = await connectSocket()
      if (sock) sock.emit('start_live_detection', { source: 'webcam' })

      intervalRef.current = setInterval(() => captureAndSend(), 500)
      setIsActive(true)
      setStatus('active')
    } catch (err) {
      setError(`Failed to start: ${err.message}`)
      setStatus('error')
    }
  }

  const captureAndSend = () => {
    if (!videoRef.current || !canvasRef.current) return
    const video = videoRef.current
    const canvas = canvasRef.current
    const ctx = canvas.getContext('2d')
    canvas.width = 640
    canvas.height = 480
    ctx.drawImage(video, 0, 0, 640, 480)
    const frameData = canvas.toDataURL('image/jpeg', 0.7)
    if (socket?.connected) {
      socket.emit('analyze_frame', { frame: frameData, timestamp: new Date().toISOString() })
    }
    setStats(prev => ({ ...prev, frames: prev.frames + 1 }))
  }

  const stopMonitoring = () => {
    if (intervalRef.current) { clearInterval(intervalRef.current); intervalRef.current = null }
    if (streamRef.current) { streamRef.current.getTracks().forEach(track => track.stop()); streamRef.current = null }
    if (socket) { socket.emit('stop_live_detection', { session_id: sessionId }); socket.disconnect(); setSocket(null) }
    setIsActive(false)
    setStatus('idle')
    setCurrentScore(0)
  }

  useEffect(() => {
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current)
      if (streamRef.current) streamRef.current.getTracks().forEach(track => track.stop())
      if (socket) socket.disconnect()
    }
  }, [socket])

  return (
    <div className="space-y-4">
      <GlassCard animate={false}>
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-3">
            {isActive ? (
              <motion.div
                className="flex items-center gap-1.5 bg-red-500/15 border border-red-500/20 px-2.5 py-1 rounded-full"
                animate={{ opacity: [1, 0.7, 1] }}
                transition={{ duration: 2, repeat: Infinity }}
              >
                <span className="w-2 h-2 rounded-full bg-red-500" />
                <span className="text-[10px] text-red-400 font-bold tracking-wider">LIVE</span>
              </motion.div>
            ) : (
              <div className="w-2.5 h-2.5 rounded-full bg-white/10" />
            )}
            <h3 className="text-sm font-medium text-white">Live Monitoring</h3>
            <span className="text-xs text-white/25 capitalize">{status}</span>
          </div>

          <button
            onClick={isActive ? stopMonitoring : startMonitoring}
            className={`px-4 py-2 rounded-xl text-xs font-medium transition-all ${
              isActive
                ? 'bg-red-500/15 border border-red-500/20 text-red-400 hover:bg-red-500/25'
                : 'bg-green-500/15 border border-green-500/20 text-green-400 hover:bg-green-500/25'
            }`}
          >
            {isActive ? 'Stop Monitoring' : 'Start Webcam'}
          </button>
        </div>

        {error && (
          <div className="glass-card !p-3 glow-border-red mb-4">
            <p className="text-xs text-red-400">{error}</p>
          </div>
        )}

        <div className="grid md:grid-cols-2 gap-4">
          {/* Video feed */}
          <div className="relative bg-black/50 rounded-xl overflow-hidden aspect-video border border-white/[0.06]">
            <video ref={videoRef} className="w-full h-full object-cover" autoPlay muted playsInline />
            <canvas ref={canvasRef} className="hidden" />

            {!isActive && (
              <div className="absolute inset-0 flex items-center justify-center bg-black/60">
                <div className="text-center">
                  <div className="w-12 h-12 mx-auto mb-2 rounded-2xl bg-white/[0.04] flex items-center justify-center">
                    <svg className="w-6 h-6 text-white/20" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
                        d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" />
                    </svg>
                  </div>
                  <p className="text-xs text-white/25">Click "Start Webcam" to begin</p>
                </div>
              </div>
            )}

            {isActive && (
              <div className="absolute top-3 left-3 flex items-center gap-1.5 bg-red-600/80 backdrop-blur-sm px-2 py-1 rounded-lg">
                <motion.span
                  className="w-1.5 h-1.5 rounded-full bg-white"
                  animate={{ opacity: [1, 0.3, 1] }}
                  transition={{ duration: 1, repeat: Infinity }}
                />
                <span className="text-[10px] text-white font-bold tracking-wider">LIVE</span>
              </div>
            )}
          </div>

          {/* Stats */}
          <div className="space-y-4">
            <ProbabilityMeter value={currentScore} />

            <div className="grid grid-cols-3 gap-2">
              {[
                { label: 'Frames', value: stats.frames },
                { label: 'Analyzed', value: stats.detections },
                { label: 'Alerts', value: stats.alerts },
              ].map(({ label, value }) => (
                <div key={label} className="glass-card !p-2 text-center">
                  <AnimatedCounter value={value} className="text-lg font-bold text-white" />
                  <p className="text-[10px] text-white/25">{label}</p>
                </div>
              ))}
            </div>

            <AnimatePresence>
              {alerts.length > 0 && (
                <motion.div
                  initial={{ opacity: 0, height: 0 }}
                  animate={{ opacity: 1, height: 'auto' }}
                  className="glass-card !p-3 glow-border-red"
                >
                  <span className="text-xs text-red-400 font-medium">Recent Alerts</span>
                  <div className="mt-2 space-y-1 max-h-24 overflow-y-auto">
                    {alerts.slice(0, 5).map((alert, i) => (
                      <div key={i} className="text-[11px] text-red-300/70 flex justify-between">
                        <span>{alert.timestamp}</span>
                        <span>{alert.confidence}% confidence</span>
                      </div>
                    ))}
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        </div>
      </GlassCard>

      {detections.length > 0 && (
        <GlassCard>
          <h4 className="text-xs text-white/30 mb-3">Detection History ({detections.length})</h4>
          <div className="max-h-48 overflow-y-auto">
            {detections.slice(0, 20).map((d, i) => (
              <DetectionEntry key={i} entry={d} />
            ))}
          </div>
        </GlassCard>
      )}
    </div>
  )
}

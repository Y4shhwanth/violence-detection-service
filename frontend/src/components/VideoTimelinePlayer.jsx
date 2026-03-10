import { useRef, useState, useMemo } from 'react'
import { motion } from 'framer-motion'

export default function VideoTimelinePlayer({ videoUrl, violations = [], duration = 0 }) {
  const videoRef = useRef(null)
  const [currentTime, setCurrentTime] = useState(0)
  const [isPlaying, setIsPlaying] = useState(false)

  const videoViolations = useMemo(
    () => violations.filter(v => v.modality === 'video' || v.modality === 'audio'),
    [violations]
  )

  if (!videoUrl || videoViolations.length === 0) return null

  const videoDuration = duration || 60

  const seekTo = (seconds) => {
    if (videoRef.current) {
      videoRef.current.currentTime = seconds
      videoRef.current.play()
      setIsPlaying(true)
    }
  }

  const handleTimeUpdate = () => {
    if (videoRef.current) {
      setCurrentTime(videoRef.current.currentTime)
    }
  }

  const handleLoadedMetadata = () => {
    // Update duration if available
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className="bg-gray-900/80 backdrop-blur-xl border border-red-500/20 rounded-2xl p-6"
    >
      <h3 className="text-sm font-semibold text-white mb-4">Video Timeline</h3>

      {/* Video player */}
      <video
        ref={videoRef}
        src={videoUrl}
        className="w-full max-h-64 rounded-lg mb-4 bg-black"
        controls
        onTimeUpdate={handleTimeUpdate}
        onLoadedMetadata={handleLoadedMetadata}
        onPlay={() => setIsPlaying(true)}
        onPause={() => setIsPlaying(false)}
      />

      {/* Timeline bar with violation overlays */}
      <div className="relative w-full h-8 bg-gray-800 rounded-lg overflow-hidden mb-3">
        {/* Violation segments */}
        {videoViolations.map((v, i) => {
          const start = (v.start_seconds || 0) / videoDuration * 100
          const end = (v.end_seconds || v.start_seconds + 1) / videoDuration * 100
          const width = Math.max(end - start, 1)

          return (
            <div
              key={i}
              className="absolute top-0 h-full bg-red-500/40 border-l border-r border-red-500 cursor-pointer hover:bg-red-500/60 transition-colors"
              style={{ left: `${start}%`, width: `${width}%` }}
              onClick={() => seekTo(v.start_seconds || 0)}
              title={`${v.modality}: ${v.reason || ''} (${v.start_time}-${v.end_time})`}
            />
          )
        })}

        {/* Playhead */}
        <div
          className="absolute top-0 h-full w-0.5 bg-white z-10"
          style={{ left: `${(currentTime / videoDuration) * 100}%` }}
        />
      </div>

      {/* Violation list */}
      <div className="space-y-1.5 max-h-32 overflow-y-auto">
        {videoViolations.map((v, i) => (
          <button
            key={i}
            onClick={() => seekTo(v.start_seconds || 0)}
            className="w-full text-left px-3 py-1.5 rounded-lg text-xs hover:bg-gray-800 transition-colors flex items-center gap-2"
          >
            <span className={`w-2 h-2 rounded-full ${v.modality === 'video' ? 'bg-red-500' : 'bg-blue-500'}`} />
            <span className="text-gray-400">{v.start_time}-{v.end_time}</span>
            <span className="text-gray-300 truncate">{v.reason || v.modality}</span>
          </button>
        ))}
      </div>
    </motion.div>
  )
}

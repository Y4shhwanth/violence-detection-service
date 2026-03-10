import { useState, useCallback, useRef } from 'react'
import { useDropzone } from 'react-dropzone'
import { motion, AnimatePresence } from 'framer-motion'
import GlassCard from './ui/GlassCard'
import { animation } from '../design/tokens'

export default function UploadSection({ onAnalyze, loading, mode = 'quick' }) {
  const [videoFile, setVideoFile] = useState(null)
  const [videoPreview, setVideoPreview] = useState(null)
  const [textInput, setTextInput] = useState('')
  const videoRef = useRef(null)

  const onDrop = useCallback((accepted) => {
    if (accepted.length > 0) {
      const file = accepted[0]
      setVideoFile(file)
      setVideoPreview(URL.createObjectURL(file))
    }
  }, [])

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: { 'video/*': ['.mp4', '.avi', '.mov', '.mkv', '.webm'] },
    maxFiles: 1,
    disabled: loading,
  })

  const handleSubmit = () => {
    if (!videoFile && !textInput.trim()) return
    onAnalyze(videoFile, textInput.trim())
  }

  const handleClear = () => {
    setVideoFile(null)
    if (videoPreview) URL.revokeObjectURL(videoPreview)
    setVideoPreview(null)
    setTextInput('')
  }

  return (
    <motion.div {...animation.fadeInUp} className="space-y-4">
      {/* Video Upload */}
      <div
        {...getRootProps()}
        className={`
          relative rounded-2xl p-10 text-center cursor-pointer transition-all duration-500 gradient-border
          ${isDragActive
            ? 'glass-card-strong glow-border-red'
            : 'glass-card hover:shadow-lg hover:shadow-purple-500/5'
          }
          ${loading ? 'opacity-50 pointer-events-none' : ''}
        `}
        style={isDragActive ? { borderStyle: 'dashed', borderColor: 'rgba(239,68,68,0.4)' } : undefined}
      >
        <input {...getInputProps()} />

        {/* Background decoration */}
        <div className="absolute inset-0 rounded-2xl overflow-hidden pointer-events-none">
          <div className="absolute top-0 left-1/2 -translate-x-1/2 w-[300px] h-[1px]"
            style={{ background: 'linear-gradient(90deg, transparent, rgba(239,68,68,0.3), rgba(139,92,246,0.2), transparent)' }}
          />
        </div>

        <AnimatePresence mode="wait">
          {videoPreview ? (
            <motion.div
              key="preview"
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0 }}
              className="space-y-3"
            >
              <video
                ref={videoRef}
                src={videoPreview}
                className="max-h-48 mx-auto rounded-xl shadow-2xl shadow-black/50 border border-white/[0.06]"
                muted
                onMouseEnter={(e) => e.target.play()}
                onMouseLeave={(e) => { e.target.pause(); e.target.currentTime = 0 }}
              />
              <p className="text-sm text-white/60">{videoFile?.name}</p>
              <p className="text-xs text-white/30">
                {(videoFile?.size / (1024 * 1024)).toFixed(1)} MB
              </p>
            </motion.div>
          ) : (
            <motion.div
              key="upload"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="space-y-4"
            >
              <div className="w-20 h-20 mx-auto rounded-2xl flex items-center justify-center relative">
                <div className="absolute inset-0 rounded-2xl bg-gradient-to-br from-red-500/10 via-purple-500/10 to-cyan-500/10 border border-white/[0.06]" />
                <div className="absolute inset-0 rounded-2xl bg-gradient-to-br from-red-500/5 to-purple-500/5 animate-pulse" />
                <svg className="w-8 h-8 text-white/40 relative z-10" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
                </svg>
              </div>
              <div>
                <p className="text-white/60 font-medium">
                  {isDragActive ? 'Drop video here...' : 'Drag & drop video or click to browse'}
                </p>
                <p className="text-xs text-white/25 mt-1">MP4, AVI, MOV, MKV, WebM (max 50MB)</p>
              </div>
              <div className="flex items-center justify-center gap-4 pt-1">
                {['Video', 'Audio', 'Text'].map((m, i) => (
                  <div key={m} className="flex items-center gap-1.5">
                    <div className="w-1.5 h-1.5 rounded-full" style={{ backgroundColor: ['#8b5cf6', '#06b6d4', '#f59e0b'][i] }} />
                    <span className="text-[10px] text-white/20">{m}</span>
                  </div>
                ))}
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      {/* Text Input */}
      <div className="relative glass-card !p-0 overflow-hidden">
        <textarea
          value={textInput}
          onChange={(e) => setTextInput(e.target.value)}
          placeholder="Enter text to analyze (optional)..."
          disabled={loading}
          className="w-full h-28 bg-transparent px-5 py-4 text-sm
            text-white placeholder-white/20 resize-none
            focus:outline-none
            disabled:opacity-50 transition-all"
        />
        {textInput && (
          <span className="absolute bottom-3 right-3 text-xs text-white/25">
            {textInput.length} chars
          </span>
        )}
      </div>

      {/* Action Buttons */}
      <div className="flex gap-3">
        <motion.button
          whileHover={{ scale: 1.01 }}
          whileTap={{ scale: 0.99 }}
          onClick={handleSubmit}
          disabled={loading || (!videoFile && !textInput.trim())}
          className="flex-1 py-3.5 px-6 rounded-xl font-semibold text-sm
            bg-gradient-to-r from-red-500 via-pink-500 to-purple-600
            hover:shadow-xl hover:shadow-red-500/25 hover:scale-[1.01]
            disabled:opacity-40 disabled:cursor-not-allowed
            transition-all duration-300 relative overflow-hidden btn-glow"
        >
          {loading && (
            <div className="absolute inset-0 shimmer" />
          )}
          <span className="relative">
            {loading ? 'Analyzing...' : mode === 'advanced' ? 'Advanced Analysis' : 'Analyze Content'}
          </span>
        </motion.button>

        {(videoFile || textInput) && (
          <motion.button
            initial={{ opacity: 0, scale: 0.8 }}
            animate={{ opacity: 1, scale: 1 }}
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
            onClick={handleClear}
            disabled={loading}
            className="py-3 px-4 rounded-xl text-sm text-white/40 border border-white/[0.08]
              hover:border-white/[0.15] hover:text-white/70 disabled:opacity-40 transition-all"
          >
            Clear
          </motion.button>
        )}
      </div>
    </motion.div>
  )
}

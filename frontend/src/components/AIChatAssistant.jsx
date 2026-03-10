import { useState, useRef, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import axios from 'axios'
import GlassCard from './ui/GlassCard'
import { animation, colors } from '../design/tokens'

export default function AIChatAssistant({ analysisId, analysisData }) {
  const [messages, setMessages] = useState([
    {
      role: 'assistant',
      content: 'Hello! I\'m your AI moderation assistant. Ask me anything about the analysis results.',
      timestamp: new Date().toLocaleTimeString(),
    },
  ])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [isExpanded, setIsExpanded] = useState(false)
  const messagesEndRef = useRef(null)

  const suggestions = [
    'Why was this flagged?',
    'Show me the evidence',
    'What policies apply?',
    'Is this a false positive?',
  ]

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const sendMessage = async (text) => {
    if (!text.trim() || loading) return

    setMessages(prev => [...prev, {
      role: 'user', content: text.trim(), timestamp: new Date().toLocaleTimeString(),
    }])
    setInput('')
    setLoading(true)

    try {
      const payload = { question: text.trim() }
      if (analysisId) payload.analysis_id = analysisId
      if (analysisData) payload.analysis_data = analysisData

      const { data } = await axios.post('/ask-analysis', payload)
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: data.answer || 'I could not generate an answer.',
        timestamp: new Date().toLocaleTimeString(),
        evidence: data.evidence_frames || [],
        policies: data.policies || [],
        questionType: data.question_type,
      }])
    } catch (err) {
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: `Sorry, I encountered an error: ${err.response?.data?.error || err.message}`,
        timestamp: new Date().toLocaleTimeString(),
        isError: true,
      }])
    } finally {
      setLoading(false)
    }
  }

  const handleSubmit = (e) => {
    e.preventDefault()
    sendMessage(input)
  }

  if (!isExpanded) {
    return (
      <motion.button
        {...animation.scaleIn}
        whileHover={{ scale: 1.01 }}
        onClick={() => setIsExpanded(true)}
        className="w-full glass-card p-4 text-left hover:border-purple-500/20 transition-colors"
      >
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-xl flex items-center justify-center"
            style={{ background: colors.modality.video.glow }}
          >
            <svg className="w-4 h-4 text-purple-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" />
            </svg>
          </div>
          <div>
            <span className="text-sm font-medium text-white">AI Moderation Copilot</span>
            <p className="text-xs text-white/30 mt-0.5">Ask questions about this analysis</p>
          </div>
        </div>
      </motion.button>
    )
  }

  return (
    <motion.div
      initial={{ opacity: 0, height: 0 }}
      animate={{ opacity: 1, height: 'auto' }}
      className="glass-card overflow-hidden"
      style={{ borderColor: 'rgba(139, 92, 246, 0.15)' }}
    >
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-white/[0.06]">
        <div className="flex items-center gap-2">
          <div className="w-6 h-6 rounded-lg flex items-center justify-center" style={{ background: colors.modality.video.glow }}>
            <svg className="w-3 h-3 text-purple-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" />
            </svg>
          </div>
          <span className="text-sm font-medium text-white">AI Copilot</span>
        </div>
        <button onClick={() => setIsExpanded(false)} className="text-white/30 hover:text-white transition-colors text-xs">
          Minimize
        </button>
      </div>

      {/* Messages */}
      <div className="h-80 overflow-y-auto px-4 py-3 space-y-3">
        <AnimatePresence>
          {messages.map((msg, i) => (
            <motion.div
              key={i}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
            >
              <div className={`max-w-[85%] rounded-xl px-3 py-2.5 ${
                msg.role === 'user'
                  ? 'glass-card !border-purple-500/20'
                  : msg.isError
                    ? 'glass-card !border-red-500/20'
                    : 'bg-white/[0.03] border border-white/[0.06] rounded-xl'
              }`}>
                <p className="text-xs text-white/80 whitespace-pre-wrap leading-relaxed">{msg.content}</p>

                {msg.evidence?.length > 0 && (
                  <div className="mt-2 space-y-1 border-t border-white/[0.06] pt-2">
                    <span className="text-[10px] text-white/25 uppercase">Evidence</span>
                    {msg.evidence.slice(0, 3).map((ev, j) => (
                      <div key={j} className="text-[11px] text-white/40 flex items-center gap-1">
                        <span className="w-1 h-1 rounded-full bg-red-500" />
                        {ev.type === 'video_frame'
                          ? `Frame at ${ev.timestamp} (score: ${ev.score})`
                          : `${ev.modality}: ${ev.reason} (${ev.time_range})`
                        }
                      </div>
                    ))}
                  </div>
                )}

                {msg.policies?.length > 0 && (
                  <div className="mt-2 space-y-1 border-t border-white/[0.06] pt-2">
                    <span className="text-[10px] text-white/25 uppercase">Policies</span>
                    {msg.policies.slice(0, 2).map((p, j) => (
                      <div key={j} className="text-[11px] text-purple-300/70">{p.title}</div>
                    ))}
                  </div>
                )}

                <span className="text-[10px] text-white/15 mt-1 block">{msg.timestamp}</span>
              </div>
            </motion.div>
          ))}
        </AnimatePresence>

        {loading && (
          <div className="flex justify-start">
            <div className="bg-white/[0.03] border border-white/[0.06] rounded-xl px-3 py-2.5">
              <div className="flex gap-1.5">
                {[0, 1, 2].map(i => (
                  <motion.span
                    key={i}
                    className="w-1.5 h-1.5 rounded-full"
                    style={{ background: 'linear-gradient(135deg, #8b5cf6, #6366f1)' }}
                    animate={{ opacity: [0.3, 1, 0.3] }}
                    transition={{ duration: 1, repeat: Infinity, delay: i * 0.2 }}
                  />
                ))}
              </div>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Suggested questions */}
      {messages.length <= 2 && (
        <div className="px-4 pb-2 flex flex-wrap gap-1.5">
          {suggestions.map((q, i) => (
            <button
              key={i}
              onClick={() => sendMessage(q)}
              disabled={loading}
              className="text-[11px] px-2.5 py-1 rounded-lg bg-white/[0.03] border border-white/[0.06]
                text-white/40 hover:text-white/70 hover:border-purple-500/20 hover:bg-purple-500/[0.04]
                transition-colors disabled:opacity-50"
            >
              {q}
            </button>
          ))}
        </div>
      )}

      {/* Input */}
      <form onSubmit={handleSubmit} className="px-4 pb-3 pt-1">
        <div className="flex gap-2">
          <input
            type="text"
            value={input}
            onChange={e => setInput(e.target.value)}
            placeholder="Ask about this analysis..."
            disabled={loading}
            className="flex-1 bg-white/[0.03] border border-white/[0.08] rounded-lg px-3 py-2
              text-xs text-white placeholder-white/25 focus:outline-none focus:border-purple-500/40
              disabled:opacity-50 transition-colors"
          />
          <button
            type="submit"
            disabled={loading || !input.trim()}
            className="px-3.5 py-2 rounded-lg text-xs text-white font-medium disabled:opacity-30 transition-colors"
            style={{ background: 'linear-gradient(135deg, rgba(139,92,246,0.6), rgba(99,102,241,0.6))' }}
          >
            Send
          </button>
        </div>
      </form>
    </motion.div>
  )
}

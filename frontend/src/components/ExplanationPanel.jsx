import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { severityColor } from '../utils/formatters'
import GlassCard from './ui/GlassCard'
import { animation } from '../design/tokens'

function Section({ title, icon, children, defaultOpen = true, accentColor }) {
  const [open, setOpen] = useState(defaultOpen)
  return (
    <div className="border border-white/[0.06] rounded-xl overflow-hidden">
      <button
        onClick={() => setOpen(!open)}
        className="w-full flex items-center gap-2 px-4 py-2.5 text-left hover:bg-white/[0.02] transition-colors"
      >
        <div className="w-6 h-6 rounded-lg flex items-center justify-center" style={{ backgroundColor: `${accentColor || 'rgba(255,255,255,0.06)'}` }}>
          {icon}
        </div>
        <span className="text-xs font-medium text-white/60 flex-1">{title}</span>
        <motion.svg
          className="w-3.5 h-3.5 text-white/30"
          fill="none" stroke="currentColor" viewBox="0 0 24 24"
          animate={{ rotate: open ? 180 : 0 }}
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </motion.svg>
      </button>
      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="overflow-hidden"
          >
            <div className="px-4 pb-3">{children}</div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}

export default function ExplanationPanel({ explanation, severity, falsePositive, recommendedAction }) {
  if (!explanation) return null

  const riskLevel = explanation.risk_level || severity?.severity_label || 'Unknown'
  const riskColor = severityColor(riskLevel)

  return (
    <GlassCard>
      <h3 className="text-sm font-semibold text-white/60 mb-4">Analysis Explanation</h3>

      {explanation.summary && (
        <p className="text-sm text-white/50 mb-4">{explanation.summary}</p>
      )}

      <div className="space-y-3">
        {/* Risk Level + Severity */}
        <div className="flex gap-3">
          <div className="flex-1 p-3 rounded-xl bg-white/[0.03] border border-white/[0.06]">
            <span className="text-[10px] text-white/30 uppercase tracking-wider block mb-1">Risk Level</span>
            <span className="text-sm font-semibold" style={{ color: riskColor }}>{riskLevel}</span>
          </div>
          {severity && (
            <div className="flex-1 p-3 rounded-xl bg-white/[0.03] border border-white/[0.06]">
              <span className="text-[10px] text-white/30 uppercase tracking-wider block mb-1">Severity</span>
              <span className="text-sm font-semibold" style={{ color: severityColor(severity.severity_label) }}>
                {severity.severity_score}/100 ({severity.severity_label})
              </span>
            </div>
          )}
        </div>

        {/* Why Flagged */}
        {explanation.why_flagged && explanation.why_flagged !== 'Content was not flagged.' && (
          <Section
            title="Why Flagged"
            accentColor="rgba(239,68,68,0.12)"
            icon={<svg className="w-3 h-3 text-red-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01" /></svg>}
          >
            <p className="text-sm text-white/60">{explanation.why_flagged}</p>
          </Section>
        )}

        {/* Compliance Suggestion */}
        {(explanation.compliance_suggestion || recommendedAction) && (
          <Section
            title="Recommended Action"
            accentColor="rgba(34,197,94,0.12)"
            icon={<svg className="w-3 h-3 text-green-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4" /></svg>}
          >
            <p className="text-sm text-white/60">{recommendedAction || explanation.compliance_suggestion}</p>
          </Section>
        )}

        {/* Keywords */}
        {explanation.keywords?.length > 0 && (
          <Section
            title="Detected Keywords"
            accentColor="rgba(236,72,153,0.12)"
            icon={<svg className="w-3 h-3 text-pink-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 7h.01M7 3h5c.512 0 1.024.195 1.414.586l7 7a2 2 0 010 2.828l-7 7a2 2 0 01-2.828 0l-7-7A1.994 1.994 0 013 12V7a4 4 0 014-4z" /></svg>}
          >
            <div className="flex flex-wrap gap-1.5">
              {explanation.keywords.map((kw, i) => (
                <span key={i} className="text-xs px-2.5 py-1 rounded-full gradient-text font-medium"
                  style={{ background: 'rgba(239,68,68,0.08)', border: '1px solid rgba(239,68,68,0.15)' }}
                >
                  <span style={{ background: 'linear-gradient(135deg, #ef4444, #ec4899)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>{kw}</span>
                </span>
              ))}
            </div>
          </Section>
        )}

        {/* Top Factors */}
        {explanation.top_factors?.length > 0 && (
          <Section
            title="Contributing Factors"
            accentColor="rgba(245,158,11,0.12)"
            icon={<svg className="w-3 h-3 text-amber-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" /></svg>}
          >
            <ul className="space-y-1.5">
              {explanation.top_factors.map((factor, i) => (
                <li key={i} className="text-xs text-white/50 flex items-start gap-2">
                  <span className="w-1 h-1 rounded-full bg-amber-500 mt-1.5 flex-shrink-0" />
                  {factor}
                </li>
              ))}
            </ul>
          </Section>
        )}

        {/* False Positive */}
        {falsePositive && falsePositive.category !== 'not_applicable' && falsePositive.category !== 'error' && (
          <Section
            title="False Positive Check"
            accentColor="rgba(234,179,8,0.12)"
            icon={<svg className="w-3 h-3 text-yellow-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" /></svg>}
            defaultOpen={false}
          >
            <p className="text-sm text-white/60">
              Category: <span className="font-medium text-yellow-400">{falsePositive.category}</span>
              {falsePositive.confidence > 0 && (
                <span className="text-white/30"> ({falsePositive.confidence.toFixed(0)}% confidence)</span>
              )}
            </p>
          </Section>
        )}
      </div>
    </GlassCard>
  )
}

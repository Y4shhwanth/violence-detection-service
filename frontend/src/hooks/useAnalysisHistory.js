import { useState, useCallback } from 'react'

const STORAGE_KEY = 'analysis_history'
const MAX_ENTRIES = 500

function loadHistory() {
  try {
    return JSON.parse(localStorage.getItem(STORAGE_KEY) || '[]')
  } catch (_) {
    return []
  }
}

function saveHistory(history) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(history))
  } catch (_) {
    // QuotaExceededError — trim aggressively and retry
    const trimmed = history.slice(0, Math.floor(MAX_ENTRIES / 2))
    localStorage.setItem(STORAGE_KEY, JSON.stringify(trimmed))
  }
}

export function useAnalysisHistory() {
  const [history, setHistory] = useState(loadHistory)

  const addResult = useCallback((results) => {
    const entryId = results.job_id || Date.now().toString()

    setHistory(prev => {
      // Deduplicate — skip if this id already exists (Strict Mode guard)
      if (prev.some(e => e.id === entryId)) return prev

      const entry = {
        id: entryId,
        date: new Date().toISOString(),
        decision: results.final_decision || (results.fused_prediction?.class === 'Violence' ? 'Violation' : 'Verified'),
        confidence: results.confidence || results.fused_prediction?.confidence || 0,
        modalities: [
          results.video_prediction && 'video',
          results.audio_prediction && 'audio',
          results.text_prediction && 'text',
        ].filter(Boolean),
        processing_time: results.processing_time_ms || 0,
      }

      // Cap at MAX_ENTRIES
      const updated = [entry, ...prev].slice(0, MAX_ENTRIES)
      saveHistory(updated)
      return updated
    })
  }, [])

  const getStats = useCallback((days = 30) => {
    const all = loadHistory()
    const cutoff = new Date()
    cutoff.setDate(cutoff.getDate() - days)
    const filtered = all.filter(e => new Date(e.date) >= cutoff)

    const violations = filtered.filter(e => e.decision === 'Violation').length
    const reviews = filtered.filter(e => e.decision === 'Review').length
    const verified = filtered.length - violations - reviews

    // Build daily buckets
    const dailyMap = {}
    filtered.forEach(e => {
      const day = e.date.slice(0, 10)
      if (!dailyMap[day]) dailyMap[day] = { date: day, total_analyses: 0, violations: 0 }
      dailyMap[day].total_analyses++
      if (e.decision === 'Violation') dailyMap[day].violations++
    })
    const daily = Object.values(dailyMap).sort((a, b) => b.date.localeCompare(a.date))

    return {
      success: filtered.length > 0,
      totals: {
        total_analyses: filtered.length,
        violations,
        reviews,
        verified,
        false_positives: 0,
        false_negatives: 0,
      },
      daily,
    }
  }, [])

  return { history, addResult, getStats }
}

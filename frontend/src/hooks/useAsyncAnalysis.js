import { useState, useCallback, useRef } from 'react'
import { submitAnalysis, pollStatus, fetchResult } from '../api/asyncClient'

const POLL_INTERVAL = 2000

export function useAsyncAnalysis() {
  const [jobId, setJobId] = useState(null)
  const [status, setStatus] = useState(null)
  const [progress, setProgress] = useState(0)
  const [currentStep, setCurrentStep] = useState('')
  const [results, setResults] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const pollRef = useRef(null)

  const stopPolling = useCallback(() => {
    if (pollRef.current) {
      clearInterval(pollRef.current)
      pollRef.current = null
    }
  }, [])

  const startPolling = useCallback((id) => {
    stopPolling()
    pollRef.current = setInterval(async () => {
      try {
        const statusData = await pollStatus(id)
        setStatus(statusData.status)
        setProgress(statusData.progress || 0)
        setCurrentStep(statusData.current_step || '')

        if (statusData.status === 'completed') {
          stopPolling()
          const resultData = await fetchResult(id)
          setResults(resultData)
          setLoading(false)
        } else if (statusData.status === 'failed') {
          stopPolling()
          setError(statusData.error || 'Analysis failed')
          setLoading(false)
        }
      } catch (err) {
        // Don't stop on transient errors
        console.warn('Poll error:', err)
      }
    }, POLL_INTERVAL)
  }, [stopPolling])

  const analyze = useCallback(async (videoFile, textInput) => {
    setLoading(true)
    setError(null)
    setResults(null)
    setProgress(0)
    setCurrentStep('Uploading...')
    setStatus('uploading')

    try {
      const formData = new FormData()
      if (videoFile) formData.append('video', videoFile)
      if (textInput) formData.append('text', textInput)

      const data = await submitAnalysis(formData)
      setJobId(data.job_id)
      setStatus('queued')
      setCurrentStep('Queued for processing')
      startPolling(data.job_id)
    } catch (err) {
      const message = err.response?.data?.message || err.message || 'Submission failed'
      setError(message)
      setLoading(false)
    }
  }, [startPolling])

  const reset = useCallback(() => {
    stopPolling()
    setJobId(null)
    setStatus(null)
    setProgress(0)
    setCurrentStep('')
    setResults(null)
    setLoading(false)
    setError(null)
  }, [stopPolling])

  return {
    jobId, status, progress, currentStep,
    results, loading, error,
    analyze, reset,
  }
}

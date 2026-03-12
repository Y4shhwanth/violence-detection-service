import { useState, useCallback } from 'react'
import { analyzeContent } from '../api/client'

export function useAnalysis() {
  const [results, setResults] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [uploadProgress, setUploadProgress] = useState(0)

  const analyze = useCallback(async (videoFile, textInput) => {
    setLoading(true)
    setError(null)
    setResults(null)
    setUploadProgress(0)

    try {
      const formData = new FormData()
      if (videoFile) {
        formData.append('video', videoFile)
      }
      if (textInput) {
        formData.append('text', textInput)
      }

      const data = await analyzeContent(formData, setUploadProgress)
      setResults(data)
      return data
    } catch (err) {
      let message = err.response?.data?.message || err.message || 'Analysis failed'
      if (err.code === 'ECONNABORTED' || message.includes('timeout')) {
        message = 'Server is waking up (free tier). Please try again in 30 seconds.'
      } else if (err.message?.includes('Network Error')) {
        message = 'Cannot reach server. It may be starting up — please retry shortly.'
      }
      setError(message)
      throw err
    } finally {
      setLoading(false)
      setUploadProgress(0)
    }
  }, [])

  const reset = useCallback(() => {
    setResults(null)
    setError(null)
    setLoading(false)
    setUploadProgress(0)
  }, [])

  return { results, loading, error, uploadProgress, analyze, reset }
}

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
      const message = err.response?.data?.message || err.message || 'Analysis failed'
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

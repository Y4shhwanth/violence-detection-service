import { useState, useCallback, useRef } from 'react'
import { analyzeContent } from '../api/client'
import { submitAnalysis, pollStatus, fetchResult } from '../api/asyncClient'

const FILE_SIZE_THRESHOLD = 10 * 1024 * 1024 // 10MB

export function useAnalysis() {
  const [results, setResults] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [uploadProgress, setUploadProgress] = useState(0)
  const [isAsync, setIsAsync] = useState(false)
  const [currentStep, setCurrentStep] = useState('')
  const [asyncProgress, setAsyncProgress] = useState(0)
  const pollRef = useRef(null)

  const analyze = useCallback(async (videoFile, textInput) => {
    setLoading(true)
    setError(null)
    setResults(null)
    setUploadProgress(0)
    setIsAsync(false)
    setCurrentStep('')
    setAsyncProgress(0)

    const useAsyncFlow = videoFile && videoFile.size > FILE_SIZE_THRESHOLD

    try {
      const formData = new FormData()
      if (videoFile) formData.append('video', videoFile)
      if (textInput) formData.append('text', textInput)

      if (useAsyncFlow) {
        // Async flow: submit → poll → fetch result
        setIsAsync(true)
        setCurrentStep('Uploading...')
        setAsyncProgress(5)

        const { job_id } = await submitAnalysis(formData)
        setCurrentStep('Queued for processing')
        setAsyncProgress(10)

        // Poll until complete
        const data = await new Promise((resolve, reject) => {
          pollRef.current = setInterval(async () => {
            try {
              const status = await pollStatus(job_id)
              setCurrentStep(status.current_step || status.status)
              setAsyncProgress(status.progress || 0)

              if (status.status === 'completed') {
                clearInterval(pollRef.current)
                pollRef.current = null
                const result = await fetchResult(job_id)
                resolve(result)
              } else if (status.status === 'failed') {
                clearInterval(pollRef.current)
                pollRef.current = null
                reject(new Error(status.error || 'Analysis failed'))
              }
            } catch (err) {
              clearInterval(pollRef.current)
              pollRef.current = null
              reject(err)
            }
          }, 2000)
        })

        setResults(data)
        return data
      } else {
        // Sync flow: direct /predict
        const data = await analyzeContent(formData, setUploadProgress)
        setResults(data)
        return data
      }
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
      if (pollRef.current) {
        clearInterval(pollRef.current)
        pollRef.current = null
      }
    }
  }, [])

  const reset = useCallback(() => {
    setResults(null)
    setError(null)
    setLoading(false)
    setUploadProgress(0)
    setIsAsync(false)
    setCurrentStep('')
    setAsyncProgress(0)
    if (pollRef.current) {
      clearInterval(pollRef.current)
      pollRef.current = null
    }
  }, [])

  return { results, loading, error, uploadProgress, analyze, reset, isAsync, currentStep, asyncProgress }
}

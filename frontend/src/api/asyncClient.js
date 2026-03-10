import client from './client'

export async function submitAnalysis(formData) {
  const response = await client.post('/analyze', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
  return response.data
}

export async function pollStatus(jobId) {
  const response = await client.get(`/status/${jobId}`)
  return response.data
}

export async function fetchResult(jobId) {
  const response = await client.get(`/result/${jobId}`)
  return response.data
}

export async function submitFeedback(jobId, feedbackType, comment = '') {
  const response = await client.post('/feedback', {
    job_id: jobId,
    feedback_type: feedbackType,
    comment,
  })
  return response.data
}

export async function fetchDashboardStats(days = 30) {
  const response = await client.get(`/dashboard/stats?days=${days}`)
  return response.data
}

export async function exportReport(jobId) {
  const response = await client.get(`/export/${jobId}`, {
    responseType: 'blob',
  })
  // Trigger download
  const url = window.URL.createObjectURL(new Blob([response.data]))
  const link = document.createElement('a')
  link.href = url
  link.setAttribute('download', `report_${jobId.slice(0, 8)}.pdf`)
  document.body.appendChild(link)
  link.click()
  link.remove()
  window.URL.revokeObjectURL(url)
}

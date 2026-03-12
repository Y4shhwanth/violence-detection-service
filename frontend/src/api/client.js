import axios from 'axios'

const API_URL = import.meta.env.VITE_API_URL || 'https://violence-detection-service.onrender.com'

const client = axios.create({
  baseURL: API_URL,
  timeout: 300000, // 5 min — Render free tier cold starts can take 30-60s
})

export async function analyzeContent(formData, onProgress) {
  const response = await client.post('/predict', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    onUploadProgress: (event) => {
      if (onProgress && event.total) {
        onProgress(Math.round((event.loaded / event.total) * 100))
      }
    },
  })
  return response.data
}

export async function checkHealth() {
  const response = await client.get('/health')
  return response.data
}

export default client

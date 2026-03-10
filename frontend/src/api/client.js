import axios from 'axios'

const client = axios.create({
  baseURL: import.meta.env.VITE_API_URL || '',
  timeout: 120000,
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

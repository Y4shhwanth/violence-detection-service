import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    port: 5173,
    proxy: {
      '/predict': 'http://localhost:5001',
      '/predict_text': 'http://localhost:5001',
      '/predict_video': 'http://localhost:5001',
      '/health': 'http://localhost:5001',
      '/analyze': 'http://localhost:5001',
      '/status': 'http://localhost:5001',
      '/result': 'http://localhost:5001',
      '/dashboard': 'http://localhost:5001',
      '/feedback': 'http://localhost:5001',
      '/export': 'http://localhost:5001',
      '/ask-analysis': 'http://localhost:5001',
      '/socket.io': {
        target: 'http://localhost:5001',
        ws: true,
      },
    },
  },
  build: {
    outDir: 'dist',
  },
})

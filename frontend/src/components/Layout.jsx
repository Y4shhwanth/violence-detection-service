import { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import ShaderBackground from './ui/ShaderBackground'
import SpecialText from './ui/SpecialText'
import { checkHealth } from '../api/client'

export default function Layout({ children }) {
  const [healthStatus, setHealthStatus] = useState('waking') // 'healthy' | 'waking' | 'offline'

  useEffect(() => {
    let mounted = true
    const check = async () => {
      if (!navigator.onLine) {
        if (mounted) setHealthStatus('offline')
        return
      }
      try {
        await checkHealth()
        if (mounted) setHealthStatus('healthy')
      } catch (_) {
        if (mounted) setHealthStatus(prev => prev === 'healthy' ? 'offline' : prev)
      }
    }
    check()
    const interval = setInterval(check, 60000)
    const goOnline = () => check()
    const goOffline = () => { if (mounted) setHealthStatus('offline') }
    window.addEventListener('online', goOnline)
    window.addEventListener('offline', goOffline)
    return () => {
      mounted = false
      clearInterval(interval)
      window.removeEventListener('online', goOnline)
      window.removeEventListener('offline', goOffline)
    }
  }, [])
  return (
    <div className="min-h-screen text-white relative" style={{ background: '#050508' }}>
      {/* WebGL shader background */}
      <ShaderBackground />

      {/* Top fade for readability */}
      <div
        className="fixed inset-x-0 top-0 h-40 pointer-events-none z-0"
        style={{ background: 'linear-gradient(to bottom, #050508, transparent)' }}
      />

      {/* Header */}
      <header className="relative z-10 border-b border-white/[0.06]" style={{ background: 'rgba(5, 5, 8, 0.8)', backdropFilter: 'blur(20px)' }}>
        <div className="max-w-6xl mx-auto px-6 py-4 flex items-center justify-between">
          <motion.div
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            className="flex items-center gap-3"
          >
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-red-500 via-pink-500 to-purple-600 flex items-center justify-center shadow-lg shadow-red-500/30 relative">
              <div className="absolute inset-0 rounded-xl bg-gradient-to-br from-red-500 via-pink-500 to-purple-600 animate-pulse opacity-50 blur-md" />
              <svg className="w-5 h-5 text-white relative z-10" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
              </svg>
            </div>
            <div>
              <h1 className="text-lg font-bold tracking-tight">
                <SpecialText speed={40} delay={0.3} className="gradient-text">
                  Violence Detection
                </SpecialText>
                <span className="text-white/50 ml-1.5 font-normal">System</span>
              </h1>
              <p className="text-[10px] text-white/20 -mt-0.5 tracking-widest uppercase">AI-Powered Content Moderation</p>
            </div>
          </motion.div>
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.3 }}
            className="hidden sm:flex items-center gap-3"
          >
            <div className={`flex items-center gap-2 px-3 py-1.5 rounded-full border ${
              healthStatus === 'healthy' ? 'border-green-500/20 bg-green-500/[0.06]'
                : healthStatus === 'waking' ? 'border-yellow-500/20 bg-yellow-500/[0.06]'
                : 'border-red-500/20 bg-red-500/[0.06]'
            }`}>
              <div className={`w-1.5 h-1.5 rounded-full animate-pulse ${
                healthStatus === 'healthy' ? 'bg-green-400 shadow-lg shadow-green-400/50'
                  : healthStatus === 'waking' ? 'bg-yellow-400 shadow-lg shadow-yellow-400/50'
                  : 'bg-red-400 shadow-lg shadow-red-400/50'
              }`} />
              <span className={`text-[11px] font-medium ${
                healthStatus === 'healthy' ? 'text-green-400/80'
                  : healthStatus === 'waking' ? 'text-yellow-400/80'
                  : 'text-red-400/80'
              }`}>
                {healthStatus === 'healthy' ? 'Online' : healthStatus === 'waking' ? 'Waking Up' : 'Offline'}
              </span>
            </div>
          </motion.div>
        </div>
      </header>

      {/* Main content */}
      <main className="relative z-10 max-w-6xl mx-auto px-6 py-8">
        {children}
      </main>
    </div>
  )
}

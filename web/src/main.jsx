import { useEffect, useState } from 'react'
import { createRoot } from 'react-dom/client'
import './style.css'

function Workspace() {
  const [status, setStatus] = useState('Checking API connection…')

  useEffect(() => {
    const signal = AbortSignal.timeout(5000)

    async function checkHealth() {
      try {
        const response = await fetch('/api/health', { signal, cache: 'no-store' })
        if (!response.ok) throw new Error('Health request failed')
        const health = await response.json()
        if (health.status !== 'ok') throw new Error('Unexpected health response')
        setStatus('FastAPI is connected.')
      } catch {
        setStatus('FastAPI is unavailable. Start the API on port 8000 and reload.')
      }
    }

    checkHealth()
  }, [])

  return (
    <main>
      <a href="/">Back to home</a>
      <h1>Prototype workspace</h1>
      <p role="status">{status}</p>
    </main>
  )
}

function Landing() {
  return (
    <main>
      <p>Autonomous Agentic OS</p>
      <h1>Turn a CRM task into a working tool.</h1>
      <p>The prototype will generate, test, and run tools for lead follow-up.</p>
      <a className="button" href="/workspace">Open prototype workspace</a>
    </main>
  )
}

createRoot(document.getElementById('root')).render(
  window.location.pathname === '/workspace' ? <Workspace /> : <Landing />,
)

import { useEffect, useRef, useState } from 'react'

const publicKey = import.meta.env.VITE_VAPI_PUBLIC_KEY?.trim()
const assistantId = import.meta.env.VITE_VAPI_ASSISTANT_ID?.trim()

export function VoiceAssistant() {
  const call = useRef(null)
  const [status, setStatus] = useState('idle')
  const [error, setError] = useState('')

  function endCall() {
    const session = call.current
    call.current = null
    session?.client?.stop()
    setStatus('idle')
  }

  useEffect(() => () => {
    const session = call.current
    call.current = null
    session?.client?.stop()
  }, [])

  async function startCall() {
    if (!publicKey || !assistantId || call.current) return
    const session = {}
    call.current = session
    setStatus('connecting')
    setError('')

    function fail() {
      if (call.current !== session) return
      endCall()
      setError('Could not connect the voice call. Check microphone access and try again.')
    }

    try {
      const { default: Vapi } = await import('@vapi-ai/web')
      if (call.current !== session) return
      const client = new Vapi(publicKey)
      session.client = client
      client.on('call-start', () => {
        if (call.current === session) setStatus('connected')
        else client.stop()
      })
      client.on('call-end', () => {
        if (call.current !== session) return
        call.current = null
        setStatus('idle')
      })
      client.on('error', fail)
      const started = await client.start(assistantId)
      if (call.current !== session) client.stop()
      else if (!started) fail()
    } catch {
      fail()
    }
  }

  return (
    <section className="card" aria-label="Voice call">
      <p>Talk with the Agentic OS assistant for help finding your way around the workspace.</p>
      {!publicKey || !assistantId ? (
        <p role="status">Voice calls are unavailable in this environment.</p>
      ) : (
        <>
          <p role="status">{{
            idle: 'Starting a call uses your microphone.',
            connecting: 'Connecting…',
            connected: 'Voice call connected',
          }[status]}</p>
          {error && <p role="alert" className="error">{error}</p>}
          <button type="button" className="button" onClick={status === 'idle' ? startCall : endCall}>
            {status === 'idle' ? 'Start voice call' : status === 'connecting' ? 'Cancel' : 'End call'}
          </button>
        </>
      )}
    </section>
  )
}

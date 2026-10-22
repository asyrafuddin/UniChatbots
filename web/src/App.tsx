import { useEffect, useRef, useState } from 'react'
import { LuCircleCheck, LuMenu, LuTriangleAlert } from 'react-icons/lu'
import { ask, checkBackend } from './api'
import { ChatMessage } from './components/ChatMessage'
import { Composer } from './components/Composer'
import { EmptyState } from './components/EmptyState'
import { Sidebar } from './components/Sidebar'
import { detectLanguage } from './lib/language'
import type { Message } from './types'

const newId = () => crypto.randomUUID()

export default function App() {
  const [messages, setMessages] = useState<Message[]>([])
  const [draft, setDraft] = useState('')
  const [busy, setBusy] = useState(false)
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [backendUp, setBackendUp] = useState<boolean | null>(null)
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    checkBackend().then(setBackendUp)
  }, [])

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  async function send(text = draft) {
    const question = text.trim()
    if (!question || busy) return
    const language = detectLanguage(question)
    const pendingId = newId()
    setMessages((m) => [
      ...m,
      { id: newId(), role: 'user', text: question, language },
      { id: pendingId, role: 'assistant', text: '', pending: true },
    ])
    setDraft('')
    setBusy(true)
    try {
      const res = await ask(question, language)
      setMessages((m) => m.map((msg) =>
        msg.id === pendingId ? { ...msg, text: res.answer, citations: res.citations, pending: false } : msg))
      setBackendUp(true)
    } catch {
      const up = await checkBackend()
      setBackendUp(up)
      const text = up
        ? 'Something went wrong while answering. Please try again.'
        : 'The assistant’s server isn’t running. Start it with: uvicorn src.api.main:app --port 8000'
      setMessages((m) => m.map((msg) => msg.id === pendingId ? { ...msg, text, pending: false } : msg))
    } finally {
      setBusy(false)
    }
  }

  function pickTopic(question: string) {
    setDraft(question)
    setSidebarOpen(false)
  }

  return (
    <div className="flex h-full">
      <Sidebar
        open={sidebarOpen}
        onClose={() => setSidebarOpen(false)}
        onNewChat={() => { setMessages([]); setDraft(''); setSidebarOpen(false) }}
        onPickTopic={pickTopic}
      />

      <main className="flex min-w-0 flex-1 flex-col">
        <header className="flex items-center gap-3 border-b border-slate-200 bg-white/80 px-4 py-3 backdrop-blur
          dark:border-slate-800 dark:bg-slate-950/80">
          <button
            onClick={() => setSidebarOpen(true)}
            className="rounded-md p-1.5 text-slate-600 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-800 md:hidden"
            aria-label="Open menu"
          >
            <LuMenu className="size-5" />
          </button>
          <h2 className="font-medium">University Assistant</h2>
          {backendUp ? (
            <span className="ml-auto flex items-center gap-1.5 rounded-full bg-emerald-100 px-2.5 py-0.5 text-xs
              font-medium text-emerald-800 dark:bg-emerald-900/40 dark:text-emerald-200">
              <LuCircleCheck className="size-3.5" aria-hidden />
              Backend connected
            </span>
          ) : (
            <span className="ml-auto flex items-center gap-1.5 rounded-full bg-amber-100 px-2.5 py-0.5 text-xs
              font-medium text-amber-800 dark:bg-amber-900/40 dark:text-amber-200">
              <LuTriangleAlert className="size-3.5" aria-hidden />
              {backendUp === null ? 'Checking backend…' : 'Backend offline'}
            </span>
          )}
        </header>

        <div className="flex-1 overflow-y-auto">
          {messages.length === 0 ? (
            <EmptyState onPick={(q) => send(q)} />
          ) : (
            <div className="mx-auto max-w-3xl space-y-6 px-4 py-6">
              {messages.map((m) => <ChatMessage key={m.id} message={m} />)}
              <div ref={bottomRef} />
            </div>
          )}
        </div>

        <div className="mx-auto w-full max-w-3xl px-4 pb-4">
          <Composer value={draft} onChange={setDraft} onSend={() => send()} disabled={busy} />
          <p className="mt-2 text-center text-xs text-slate-500 dark:text-slate-400">
            Answers come only from official documents. If it isn’t in them, the assistant will say so.
          </p>
        </div>
      </main>
    </div>
  )
}

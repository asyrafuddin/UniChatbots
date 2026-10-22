import type { Citation, Language } from './types'

/** The Python backend (FastAPI). Set VITE_API_URL in .env.local when it runs somewhere else. */
const API_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

export interface AskResponse {
  id: string | null
  answer: string
  citations: Citation[]
  found: boolean
}

/**
 * Ask the assistant a question: the backend retrieves + re-ranks document chunks from Supabase,
 * an LLM writes the answer, and the exchange is saved to Supabase.
 */
export async function ask(question: string, language: Language): Promise<AskResponse> {
  const res = await fetch(`${API_URL}/api/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ question, language }),
  })
  if (!res.ok) throw new Error(`Backend error ${res.status}`)
  return res.json()
}

/** True if the backend answers its health check. */
export async function checkBackend(): Promise<boolean> {
  try {
    const res = await fetch(`${API_URL}/api/health`)
    return res.ok
  } catch {
    return false
  }
}

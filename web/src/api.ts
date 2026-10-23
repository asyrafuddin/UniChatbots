import { supabase } from './lib/supabase'
import type { Citation, Language } from './types'

export interface AskResponse {
  id: string | null
  answer: string
  citations: Citation[]
  found: boolean
}

/** A failed request; status 429 means the backend's rate limit was hit. */
export class BackendError extends Error {
  status: number
  constructor(status: number) {
    super(`Backend error ${status}`)
    this.status = status
  }
}

const isLocalSite = ['localhost', '127.0.0.1'].includes(window.location.hostname)
let cachedUrl: Promise<string | null> | null = null

/**
 * Where the Python backend is:
 * 1. VITE_API_URL if set at build time,
 * 2. http://localhost:8000 when the site itself runs locally (npm run dev),
 * 3. otherwise the address the Cloudflare tunnel saved in Supabase (it changes on every restart).
 */
async function resolveApiUrl(): Promise<string | null> {
  if (import.meta.env.VITE_API_URL) return import.meta.env.VITE_API_URL
  if (isLocalSite) return 'http://localhost:8000'
  if (!supabase) return null
  const { data } = await supabase.from('public_config').select('value').eq('key', 'api_url').maybeSingle()
  return data?.value ?? null
}

/** The backend URL, looked up once and re-checked after a failure (the tunnel may have restarted). */
function apiUrl(fresh = false): Promise<string | null> {
  if (fresh || !cachedUrl) cachedUrl = resolveApiUrl().catch(() => null)
  return cachedUrl
}

/**
 * Ask the assistant a question: the backend retrieves + re-ranks document chunks from Supabase,
 * an LLM writes the answer, and the exchange is saved to Supabase.
 */
export async function ask(question: string, language: Language): Promise<AskResponse> {
  const url = await apiUrl()
  if (!url) throw new BackendError(503)
  let res: Response
  try {
    res = await fetch(`${url}/api/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ question, language }),
    })
  } catch (err) {
    cachedUrl = null // look the address up again next time
    throw err
  }
  if (!res.ok) throw new BackendError(res.status)
  return res.json()
}

/** True if the backend answers its health check (always re-reads the address first). */
export async function checkBackend(): Promise<boolean> {
  const url = await apiUrl(true)
  if (!url) return false
  try {
    const res = await fetch(`${url}/api/health`)
    return res.ok
  } catch {
    return false
  }
}

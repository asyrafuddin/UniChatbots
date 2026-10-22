import { createClient, type SupabaseClient } from '@supabase/supabase-js'

const url = import.meta.env.VITE_SUPABASE_URL
const publishableKey = import.meta.env.VITE_SUPABASE_PUBLISHABLE_KEY

if (publishableKey?.startsWith('sb_secret_')) {
  // A secret key in browser code would give every visitor full database access.
  throw new Error('VITE_SUPABASE_PUBLISHABLE_KEY holds a SECRET key. Use the publishable key instead.')
}

/** The shared Supabase client, or null until web/.env.local is filled in. */
export const supabase: SupabaseClient | null =
  url && publishableKey ? createClient(url, publishableKey) : null

export type SupabaseStatus = 'not-configured' | 'checking' | 'connected' | 'error'

/** Ping the project's Auth health endpoint to confirm the URL and key work. */
export async function checkSupabaseConnection(): Promise<Exclude<SupabaseStatus, 'checking'>> {
  if (!url || !publishableKey) return 'not-configured'
  try {
    const res = await fetch(`${url}/auth/v1/health`, { headers: { apikey: publishableKey } })
    return res.ok ? 'connected' : 'error'
  } catch {
    return 'error'
  }
}

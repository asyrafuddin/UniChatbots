import { useEffect, useState } from 'react'
import { LuDatabase } from 'react-icons/lu'
import { checkSupabaseConnection, type SupabaseStatus } from '../lib/supabase'

const STYLE: Record<SupabaseStatus, { dot: string; label: string }> = {
  'not-configured': { dot: 'bg-slate-400', label: 'Supabase not configured' },
  checking: { dot: 'bg-amber-400 animate-pulse', label: 'Connecting to Supabase…' },
  connected: { dot: 'bg-emerald-500', label: 'Supabase connected' },
  error: { dot: 'bg-red-500', label: 'Supabase connection failed' },
}

/** Small indicator showing whether the Supabase URL + key in .env.local actually work. */
export function ConnectionStatus() {
  const [status, setStatus] = useState<SupabaseStatus>('checking')

  useEffect(() => {
    checkSupabaseConnection().then(setStatus)
  }, [])

  const { dot, label } = STYLE[status]
  return (
    <p className="flex items-center gap-2 px-5 pb-4 text-xs text-slate-500 dark:text-slate-400">
      <LuDatabase className="size-3.5 shrink-0" aria-hidden />
      <span className={`size-2 rounded-full ${dot}`} aria-hidden />
      {label}
    </p>
  )
}

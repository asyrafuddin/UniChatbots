import { type FormEvent, type KeyboardEvent, useEffect, useRef } from 'react'
import { LuSendHorizontal } from 'react-icons/lu'

interface ComposerProps {
  value: string
  onChange: (value: string) => void
  onSend: () => void
  disabled: boolean
}

/** Message box: Enter sends, Shift+Enter adds a new line, grows with its content. */
export function Composer({ value, onChange, onSend, disabled }: ComposerProps) {
  const ref = useRef<HTMLTextAreaElement>(null)

  useEffect(() => {
    const el = ref.current
    if (!el) return
    el.style.height = 'auto'
    el.style.height = `${Math.min(el.scrollHeight, 200)}px`
  }, [value])

  const submit = (e?: FormEvent) => {
    e?.preventDefault()
    if (value.trim() && !disabled) onSend()
  }

  const onKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey && !e.nativeEvent.isComposing) submit(e)
  }

  return (
    <form onSubmit={submit} className="flex items-end gap-2 rounded-2xl border border-slate-300 bg-white p-2
      shadow-sm focus-within:border-brand-500 dark:border-slate-700 dark:bg-slate-900">
      <textarea
        ref={ref}
        rows={1}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        onKeyDown={onKeyDown}
        placeholder="Ask in English, Bahasa Melayu or 한국어…"
        className="max-h-[200px] flex-1 resize-none bg-transparent px-2 py-1.5 outline-none placeholder:text-slate-500"
      />
      <button
        type="submit"
        disabled={disabled || !value.trim()}
        className="grid size-9 place-items-center rounded-xl bg-brand-600 text-white hover:bg-brand-700
          disabled:cursor-not-allowed disabled:opacity-40"
        aria-label="Send"
      >
        <LuSendHorizontal className="size-4" />
      </button>
    </form>
  )
}

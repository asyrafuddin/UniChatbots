import { LuLanguages } from 'react-icons/lu'
import { LANGUAGE_LABEL } from '../lib/language'
import type { Message } from '../types'
import { BrandMark } from './BrandMark'
import { SourceList } from './SourceList'

/** Wraps [1], [2] markers in small badges and renders the LLM's **bold** text (no other Markdown). */
function withCitationBadges(text: string) {
  return text.split(/(\[\d+\]|\*\*[^*]+\*\*)/g).map((part, i) => {
    if (/^\[\d+\]$/.test(part)) {
      return (
        <sup key={i} className="mx-0.5 rounded bg-brand-100 px-1 text-[0.7rem] font-semibold text-brand-700
          dark:bg-slate-700 dark:text-slate-200">
          {part.slice(1, -1)}
        </sup>
      )
    }
    if (/^\*\*[^*]+\*\*$/.test(part)) return <strong key={i}>{part.slice(2, -2)}</strong>
    return part
  })
}

export function ChatMessage({ message }: { message: Message }) {
  if (message.role === 'user') {
    return (
      <div className="flex flex-col items-end gap-1">
        <div className="max-w-[85%] whitespace-pre-wrap rounded-2xl rounded-br-sm bg-brand-600 px-4 py-2.5 text-white">
          {message.text}
        </div>
        {message.language && (
          <span className="flex items-center gap-1 text-xs text-slate-500 dark:text-slate-400">
            <LuLanguages className="size-3" aria-hidden />
            {LANGUAGE_LABEL[message.language]}
          </span>
        )}
      </div>
    )
  }

  return (
    <div className="flex gap-3">
      <BrandMark size="sm" />
      <div className="min-w-0 max-w-[85%] rounded-2xl rounded-tl-sm border border-slate-200 bg-white px-4 py-3
        dark:border-slate-800 dark:bg-slate-900">
        {message.pending ? (
          <span className="flex gap-1 py-1" aria-label="Thinking">
            {[0, 150, 300].map((delay) => (
              <span key={delay} className="size-2 animate-bounce rounded-full bg-slate-400"
                style={{ animationDelay: `${delay}ms` }} />
            ))}
          </span>
        ) : (
          <>
            <p className="whitespace-pre-wrap leading-relaxed">{withCitationBadges(message.text)}</p>
            {message.citations && message.citations.length > 0 && <SourceList citations={message.citations} />}
          </>
        )}
      </div>
    </div>
  )
}

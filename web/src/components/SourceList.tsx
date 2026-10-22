import { LuExternalLink, LuFileText, LuGlobe } from 'react-icons/lu'
import type { Citation } from '../types'

/** Numbered sources under an answer; [n] in the answer text refers to item n. */
export function SourceList({ citations }: { citations: Citation[] }) {
  return (
    <div className="mt-3 border-t border-slate-200 pt-3 dark:border-slate-700">
      <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">Sources</p>
      <ol className="space-y-1.5">
        {citations.map((c, i) => {
          // Web pages without a known URL are cited as "local:<file>" — show those as text, not a link
          const isUrl = typeof c.page_or_url === 'string' && /^https?:\/\//.test(c.page_or_url)
          const isPage = typeof c.page_or_url === 'number'
          const Icon = isPage ? LuFileText : LuGlobe
          return (
            <li key={c.id} className="flex gap-2 text-sm">
              <span className="grid size-5 shrink-0 place-items-center rounded bg-brand-100 text-xs
                font-semibold text-brand-700 dark:bg-slate-700 dark:text-slate-200">
                {i + 1}
              </span>
              <Icon className="mt-0.5 size-4 shrink-0 text-slate-400" aria-hidden />
              <span className="min-w-0">
                {isUrl ? (
                  <a href={String(c.page_or_url)} target="_blank" rel="noreferrer"
                    className="inline-flex items-center gap-1 font-medium text-brand-600 hover:underline dark:text-brand-100">
                    {c.source}
                    <LuExternalLink className="size-3" aria-hidden />
                  </a>
                ) : (
                  <span className="font-medium">
                    {c.source} {isPage && <span className="text-slate-500">· p. {c.page_or_url}</span>}
                  </span>
                )}
                <span className="block truncate text-xs text-slate-500 dark:text-slate-400">{c.section}</span>
              </span>
            </li>
          )
        })}
      </ol>
    </div>
  )
}

import { LuMessageSquareText } from 'react-icons/lu'
import { EXAMPLES } from '../data/topics'
import { BrandMark } from './BrandMark'

/** First screen of a new chat: what the assistant does + example questions to click. */
export function EmptyState({ onPick }: { onPick: (question: string) => void }) {
  return (
    <div className="mx-auto flex max-w-2xl flex-col items-center px-4 pt-16 text-center md:pt-24">
      <BrandMark size="lg" />
      <h1 className="mt-5 text-2xl font-semibold md:text-3xl">Ask about life at ERICA</h1>
      <p className="mt-2 max-w-md text-slate-500 dark:text-slate-400">
        Rules, courses, fees, scholarships, dorms and deadlines — answered from official university
        documents, with the page each answer comes from.
      </p>
      <div className="mt-8 grid w-full gap-3 sm:grid-cols-2">
        {EXAMPLES.map((q) => (
          <button
            key={q}
            onClick={() => onPick(q)}
            className="flex items-start gap-3 rounded-xl border border-slate-200 bg-white px-4 py-3 text-left text-sm
              hover:border-brand-500 hover:bg-brand-50 dark:border-slate-800 dark:bg-slate-900
              dark:hover:border-slate-600 dark:hover:bg-slate-800"
          >
            <LuMessageSquareText className="mt-0.5 size-4 shrink-0 text-slate-400" aria-hidden />
            {q}
          </button>
        ))}
      </div>
    </div>
  )
}

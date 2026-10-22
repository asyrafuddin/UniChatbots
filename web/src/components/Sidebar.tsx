import { LuInfo, LuPlus, LuX } from 'react-icons/lu'
import { TOPICS } from '../data/topics'
import { BrandMark } from './BrandMark'
import { ConnectionStatus } from './ConnectionStatus'

interface SidebarProps {
  open: boolean
  onClose: () => void
  onNewChat: () => void
  onPickTopic: (question: string) => void
}

/** Left panel: new chat + topic shortcuts. Slides in over the chat on small screens. */
export function Sidebar({ open, onClose, onNewChat, onPickTopic }: SidebarProps) {
  return (
    <>
      {open && (
        <div className="fixed inset-0 z-20 bg-slate-900/40 md:hidden" onClick={onClose} aria-hidden />
      )}
      <aside
        className={`fixed inset-y-0 left-0 z-30 flex w-72 flex-col border-r border-slate-200 bg-white
          transition-transform dark:border-slate-800 dark:bg-slate-900 md:static md:translate-x-0
          ${open ? 'translate-x-0' : '-translate-x-full'}`}
      >
        <div className="flex items-center gap-3 px-5 py-5">
          <BrandMark />
          <div>
            <p className="font-semibold leading-tight">ERICA Assistant</p>
            <p className="text-xs text-slate-500 dark:text-slate-400">EN · BM · 한국어</p>
          </div>
          <button
            onClick={onClose}
            className="ml-auto rounded-md p-1.5 text-slate-500 hover:bg-slate-100 dark:hover:bg-slate-800 md:hidden"
            aria-label="Close menu"
          >
            <LuX className="size-5" />
          </button>
        </div>

        <div className="px-4">
          <button
            onClick={onNewChat}
            className="flex w-full items-center gap-2 rounded-lg border border-slate-200 px-3 py-2 text-sm font-medium
              hover:bg-slate-50 dark:border-slate-700 dark:hover:bg-slate-800"
          >
            <LuPlus className="size-4" aria-hidden />
            New chat
          </button>
        </div>

        <nav className="mt-6 flex-1 overflow-y-auto px-4">
          <p className="px-2 pb-2 text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">Topics</p>
          <ul className="space-y-1">
            {TOPICS.map(({ label, icon: Icon, question }) => (
              <li key={label}>
                <button
                  onClick={() => onPickTopic(question)}
                  className="flex w-full items-center gap-3 rounded-lg px-2 py-2 text-left text-sm
                    text-slate-700 hover:bg-brand-50 hover:text-brand-700 dark:text-slate-300
                    dark:hover:bg-slate-800 dark:hover:text-white"
                >
                  <Icon className="size-4 shrink-0 text-slate-400" aria-hidden />
                  {label}
                </button>
              </li>
            ))}
          </ul>
        </nav>

        <p className="flex gap-2 border-t border-slate-200 px-5 py-4 text-xs leading-relaxed text-slate-500
          dark:border-slate-800 dark:text-slate-400">
          <LuInfo className="mt-0.5 size-3.5 shrink-0" aria-hidden />
          Unofficial student project. Always confirm with the official office.
        </p>
        <ConnectionStatus />
      </aside>
    </>
  )
}

import type { Language } from '../types'

const MALAY_WORDS = new Set([
  'boleh', 'berapa', 'kali', 'bila', 'macam', 'mana', 'saya', 'nak', 'tak', 'apa', 'yuran',
  'biasiswa', 'asrama', 'ke', 'ini', 'itu', 'dan', 'untuk', 'bagaimana', 'adakah', 'perlu',
])
const ENGLISH_WORDS = new Set([
  'the', 'is', 'can', 'how', 'what', 'when', 'where', 'i', 'my', 'do', 'subject', 'repeat',
  'apply', 'fee', 'fees', 'deadline', 'course', 'register', 'scholarship', 'dorm',
])

/** Rough guess of a question's language, only used to label messages in the UI. */
export function detectLanguage(text: string): Language {
  if (/[가-힣]/.test(text)) return 'ko'
  const words = text.toLowerCase().match(/[a-z]+/g) ?? []
  const malay = words.filter((w) => MALAY_WORDS.has(w)).length
  const english = words.filter((w) => ENGLISH_WORDS.has(w)).length
  if (malay && english) return 'mixed'
  return malay > english ? 'ms' : 'en'
}

export const LANGUAGE_LABEL: Record<Language, string> = {
  en: 'English',
  ms: 'Bahasa Melayu',
  ko: '한국어',
  mixed: 'Rojak',
}

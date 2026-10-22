/** A passage the answer is based on — same fields as a row in data/processed/chunks.jsonl. */
export interface Citation {
  id: string
  source: string
  page_or_url: number | string
  section: string
}

export type Language = 'en' | 'ms' | 'ko' | 'mixed'

export interface Message {
  id: string
  role: 'user' | 'assistant'
  text: string
  language?: Language
  citations?: Citation[]
  pending?: boolean
}

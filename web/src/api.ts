import type { Citation, Language } from './types'

export interface AskResponse {
  answer: string
  citations: Citation[]
}

// Placeholders — deliberately not real documents/pages, so nobody mistakes them for real citations.
const DEMO_CITATIONS: Citation[] = [
  { id: 'demo-1', source: 'example_document.pdf', page_or_url: 1, section: 'Example section' },
  { id: 'demo-2', source: 'example_page.html', page_or_url: 'https://example.com', section: 'Example web page' },
]

const DEMO_ANSWER: Record<Language, string> = {
  en: 'This is a demo answer — the retrieval and LLM backend isn’t connected yet. Real answers will quote the university documents and cite them like this [1][2].',
  ms: 'Ini jawapan demo — backend carian dan LLM belum disambungkan lagi. Jawapan sebenar akan memetik dokumen universiti dan merujuknya seperti ini [1][2].',
  ko: '데모 답변입니다. 검색 및 LLM 백엔드는 아직 연결되지 않았습니다. 실제 답변은 대학 문서를 근거로 이렇게 출처를 표시합니다 [1][2].',
  mixed: 'Ini demo answer je — backend belum connect lagi. Nanti jawapan sebenar akan cite dokumen universiti macam ni [1][2].',
}

/**
 * Ask the assistant a question.
 * DEMO ONLY: returns a canned answer after a short delay. Later this becomes a
 * fetch() to the Python backend (retrieve → re-rank → LLM) with the same response shape.
 */
export async function ask(_question: string, language: Language): Promise<AskResponse> {
  await new Promise((resolve) => setTimeout(resolve, 900))
  return { answer: DEMO_ANSWER[language], citations: DEMO_CITATIONS }
}

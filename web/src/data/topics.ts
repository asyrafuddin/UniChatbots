import type { IconType } from 'react-icons'
import { LuAward, LuCalendarDays, LuGraduationCap, LuHouse, LuNotebookPen, LuShieldCheck } from 'react-icons/lu'

export interface Topic {
  label: string
  icon: IconType
  question: string
}

/** Sidebar shortcuts — each one fills the composer with a starter question. */
export const TOPICS: Topic[] = [
  { label: 'Academic calendar', icon: LuCalendarDays, question: 'When is the course registration period this semester?' },
  { label: 'Course registration', icon: LuNotebookPen, question: 'How do I register for courses on the portal?' },
  { label: 'Scholarships', icon: LuAward, question: 'What scholarships can international students apply for?' },
  { label: 'Dormitory', icon: LuHouse, question: 'How do I apply for the ERICA dormitory?' },
  { label: 'Visa & insurance', icon: LuShieldCheck, question: 'Do I need National Health Insurance as a D-2 student?' },
  { label: 'Graduation', icon: LuGraduationCap, question: 'What are the graduation requirements?' },
]

/** Example questions shown on the empty chat screen, one per supported language style. */
export const EXAMPLES: string[] = [
  'How many times can I repeat a failed course?',
  'Boleh repeat subject berapa kali?',
  '기숙사 신청은 언제 해요?',
  'Biasiswa untuk pelajar antarabangsa ada apa?',
]

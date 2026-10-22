import { LuGraduationCap } from 'react-icons/lu'

/** The app's logo tile, reused in the sidebar, chat avatar and start screen. */
export function BrandMark({ size = 'md' }: { size?: 'sm' | 'md' | 'lg' }) {
  const box = { sm: 'size-8 rounded-full', md: 'size-9 rounded-lg', lg: 'size-14 rounded-2xl' }[size]
  const icon = { sm: 'size-4', md: 'size-5', lg: 'size-7' }[size]
  return (
    <div className={`grid shrink-0 place-items-center bg-brand-600 text-white ${box}`}>
      <LuGraduationCap className={icon} aria-hidden />
    </div>
  )
}

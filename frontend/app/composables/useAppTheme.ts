import { useDark, useToggle } from '@vueuse/core'

const storageKey = 'hibou-color-scheme'

export function useAppTheme() {
  const isDark = useDark({
    storageKey,
    attribute: 'class',
    valueDark: 'dark',
    valueLight: '',
  })
  const toggle = useToggle(isDark)

  return { isDark, toggle }
}

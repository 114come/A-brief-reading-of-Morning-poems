import { defineStore } from 'pinia'
import { ref } from 'vue'

export const THEME_KEY = 'english-theme'
export type Theme = 'light' | 'dark'

/** 读取初始主题：localStorage 优先，其次跟随系统偏好 */
export function getInitialTheme(): Theme {
  const stored = localStorage.getItem(THEME_KEY)
  if (stored === 'light' || stored === 'dark') return stored
  if (typeof window !== 'undefined' && window.matchMedia?.('(prefers-color-scheme: dark)').matches) {
    return 'dark'
  }
  return 'light'
}

export function applyTheme(theme: Theme): void {
  document.documentElement.setAttribute('data-theme', theme)
}

export const useThemeStore = defineStore('theme', () => {
  const theme = ref<Theme>(getInitialTheme())
  const isDark = ref(theme.value === 'dark')

  function toggle(): void {
    theme.value = isDark.value ? 'light' : 'dark'
    isDark.value = theme.value === 'dark'
    localStorage.setItem(THEME_KEY, theme.value)
    applyTheme(theme.value)
  }

  return { theme, isDark, toggle }
})

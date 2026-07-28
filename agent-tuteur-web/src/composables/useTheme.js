import { ref } from 'vue'

const THEME_KEY = 'tuteur_theme'
// 'light' | 'dark' | 'system' — défaut clair (outil destiné aux élèves).
const theme = ref(localStorage.getItem(THEME_KEY) || 'light')

function apply(value) {
  const root = document.documentElement
  if (value === 'system') {
    root.removeAttribute('data-theme')
  } else {
    root.setAttribute('data-theme', value)
  }
}

apply(theme.value)

export function useTheme() {
  function setTheme(value) {
    theme.value = value
    localStorage.setItem(THEME_KEY, value)
    apply(value)
  }
  function toggle() {
    setTheme(theme.value === 'dark' ? 'light' : 'dark')
  }
  return { theme, setTheme, toggle }
}

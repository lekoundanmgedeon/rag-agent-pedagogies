import { marked } from 'marked'
import DOMPurify from 'dompurify'

marked.setOptions({ breaks: true, gfm: true })

/**
 * Rendu markdown -> HTML assaini. Le contenu vient du LLM : on le passe toujours
 * par DOMPurify avant injection (v-html) pour éviter toute exécution de script.
 */
export function renderMarkdown(text) {
  if (!text) return ''
  return DOMPurify.sanitize(marked.parse(text))
}

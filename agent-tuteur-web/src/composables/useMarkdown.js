import { marked } from 'marked'
import DOMPurify from 'dompurify'
import katex from 'katex'

/**
 * Rendu markdown + LaTeX robuste pour les réponses du tuteur.
 *
 * Le LLM émet des maths avec des délimiteurs variés — `$…$`, `$$…$$` (style
 * dollar) et `\(…\)`, `\[…\]` (style MathJax que renvoie souvent Mistral). Deux
 * pièges classiques, à l'origine des « fuites de caractères » observées avant :
 *
 *  1. Markdown mange les `\` et `_` à l'intérieur des formules (`\frac`, `x_1`)
 *     s'il les voit → LaTeX cassé. On tokenise donc les maths **avant** le
 *     parsing markdown (extension `marked`), pour les soustraire à son influence.
 *  2. DOMPurify peut mutiler le balisage KaTeX. On rend donc chaque formule en
 *     HTML de confiance, on la remplace par un jeton neutre pendant le markdown
 *     et la sanitisation, puis on réinjecte le HTML KaTeX **après** DOMPurify.
 *
 * KaTeX est appelé avec `throwOnError: false` : une formule invalide s'affiche en
 * erreur localisée (rouge) plutôt que de faire échouer tout le message.
 */

marked.setOptions({ breaks: true, gfm: true })

// Sentinelles issues de la zone à usage privé Unicode : n'apparaissent jamais
// dans un texte réel ni dans du HTML, et traversent markdown/DOMPurify intactes.
const PH_OPEN = '\uE000'
const PH_CLOSE = '\uE001'

let mathStore = []

function renderTex(tex, displayMode) {
  const trimmed = (tex || '').trim()
  let html
  try {
    html = katex.renderToString(trimmed, {
      displayMode,
      throwOnError: false,
      strict: 'ignore',
      output: 'htmlAndMathml',
    })
  } catch {
    const raw = displayMode ? `$$${trimmed}$$` : `$${trimmed}$`
    html = `<code class="math-error">${escapeHtml(raw)}</code>`
  }
  const index = mathStore.push(html) - 1
  return `${PH_OPEN}${index}${PH_CLOSE}`
}

function escapeHtml(s) {
  return s.replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]))
}

// ── Extension marked : maths bloc ($$…$$, \[…\]) et inline ($…$, $$…$$, \(…\)) ──
const mathExtension = {
  extensions: [
    {
      name: 'blockMath',
      level: 'block',
      start(src) {
        const m = src.match(/\$\$|\\\[/)
        return m ? m.index : undefined
      },
      tokenizer(src) {
        const m = /^ {0,3}(?:\$\$([\s\S]+?)\$\$|\\\[([\s\S]+?)\\\])\s*(?:\n|$)/.exec(src)
        if (m) return { type: 'blockMath', raw: m[0], tex: m[1] ?? m[2] }
      },
      renderer(token) {
        return renderTex(token.tex, true) + '\n'
      },
    },
    {
      name: 'inlineMath',
      level: 'inline',
      start(src) {
        const m = src.match(/\$|\\\(/)
        return m ? m.index : undefined
      },
      tokenizer(src) {
        // $$…$$ inline (au milieu d'une phrase) → mode display.
        let m = /^\$\$([^\n]+?)\$\$/.exec(src)
        if (m) return { type: 'inlineMath', raw: m[0], tex: m[1], display: true }
        // \( … \) inline MathJax.
        m = /^\\\(([\s\S]+?)\\\)/.exec(src)
        if (m) return { type: 'inlineMath', raw: m[0], tex: m[1], display: false }
        // $ … $ inline, avec garde anti-devise : pas d'espace collé aux `$`,
        // et le `$` d'ouverture n'est pas immédiatement suivi d'un chiffre.
        m = /^\$(?!\s)((?:\\.|[^$\n])+?)(?<!\s)\$(?!\d)/.exec(src)
        if (m) return { type: 'inlineMath', raw: m[0], tex: m[1], display: false }
      },
      renderer(token) {
        return renderTex(token.tex, token.display)
      },
    },
  ],
}

marked.use(mathExtension)

function reinject(html) {
  // Réinjecte le HTML KaTeX (de confiance) à la place des sentinelles.
  return html.replace(new RegExp(`${PH_OPEN}(\\d+)${PH_CLOSE}`, 'g'), (_, i) => mathStore[Number(i)] ?? '')
}

export function renderMarkdown(text) {
  if (!text) return ''
  mathStore = []
  const clean = DOMPurify.sanitize(marked.parse(text))
  return reinject(clean)
}

/** Variante sans DOMPurify — réservée aux tests (pas de DOM en Node). */
export function _renderNoSanitize(text) {
  if (!text) return ''
  mathStore = []
  return reinject(marked.parse(text))
}

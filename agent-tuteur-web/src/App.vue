<template>
  <router-view />
</template>

<script setup>
import { onMounted } from 'vue'
import { useAuthStore } from '@/stores/auth.js'

const auth = useAuthStore()
onMounted(() => {
  if (auth.isAuthenticated && !auth.user) auth.restore()
})
</script>

<style>
/* ═══════════════════════════════════════════════════════════════════════════
   DESIGN SYSTEM — Agent Tuteur Sénégal
   Clair par défaut (outil élève), sombre via [data-theme="dark"] ou système.
   Palette : fonds neutres, accent indigo, typographie system-ui.
   ═══════════════════════════════════════════════════════════════════════════ */

*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

:root {
  --bg-app:       #f5f6f8;
  --bg-surface:   #ffffff;
  --bg-elevated:  #ffffff;
  --bg-sidebar:   #ffffff;
  --bg-hover:     #f0f1f4;
  --bg-active:    #e9ebf0;
  --bg-inset:     #f2f3f6;

  --text-primary:   #1b2130;
  --text-secondary: #5c6675;
  --text-muted:     #97a0af;
  --text-on-accent: #ffffff;

  --accent:       #4f46e5;
  --accent-hover: #4338ca;
  --accent-soft:  rgba(79, 70, 229, 0.10);
  --accent-ring:  rgba(79, 70, 229, 0.35);

  --border:        rgba(20, 24, 33, 0.10);
  --border-strong: rgba(20, 24, 33, 0.18);

  --success: #0e9f6e;
  --success-soft: rgba(14, 159, 110, 0.12);
  --error:   #e02424;
  --error-soft: rgba(224, 36, 36, 0.10);
  --warning: #c27803;
  --warning-soft: rgba(194, 120, 3, 0.12);
  --info:    #3f83f8;

  --font-sans: system-ui, -apple-system, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
  --font-mono: 'SFMono-Regular', 'JetBrains Mono', Menlo, Consolas, monospace;

  --radius-sm: 6px;
  --radius-md: 10px;
  --radius-lg: 14px;
  --radius-xl: 20px;

  --shadow-sm: 0 1px 2px rgba(20, 24, 33, 0.06);
  --shadow-md: 0 4px 16px rgba(20, 24, 33, 0.08);
  --shadow-lg: 0 12px 32px rgba(20, 24, 33, 0.14);

  --sidebar-w: 272px;
  --ease: cubic-bezier(0.16, 1, 0.3, 1);
}

:root[data-theme="dark"] {
  --bg-app:       #0f1216;
  --bg-surface:   #171b21;
  --bg-elevated:  #1c212a;
  --bg-sidebar:   #13171c;
  --bg-hover:     #20262f;
  --bg-active:    #262d38;
  --bg-inset:     #10141a;

  --text-primary:   #e7ecf2;
  --text-secondary: #99a3b2;
  --text-muted:     #67717f;
  --text-on-accent: #ffffff;

  --accent:       #7c8cff;
  --accent-hover: #93a0ff;
  --accent-soft:  rgba(124, 140, 255, 0.14);
  --accent-ring:  rgba(124, 140, 255, 0.40);

  --border:        rgba(255, 255, 255, 0.09);
  --border-strong: rgba(255, 255, 255, 0.16);

  --success-soft: rgba(14, 159, 110, 0.18);
  --error-soft:   rgba(224, 36, 36, 0.18);
  --warning-soft: rgba(194, 120, 3, 0.18);

  --shadow-sm: 0 1px 2px rgba(0, 0, 0, 0.4);
  --shadow-md: 0 4px 16px rgba(0, 0, 0, 0.5);
  --shadow-lg: 0 12px 32px rgba(0, 0, 0, 0.6);
}

/* Suit le système quand aucun thème explicite n'est choisi. */
@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]):not([data-theme="dark"]) {
    --bg-app: #0f1216; --bg-surface: #171b21; --bg-elevated: #1c212a;
    --bg-sidebar: #13171c; --bg-hover: #20262f; --bg-active: #262d38; --bg-inset: #10141a;
    --text-primary: #e7ecf2; --text-secondary: #99a3b2; --text-muted: #67717f;
    --accent: #7c8cff; --accent-hover: #93a0ff; --accent-soft: rgba(124,140,255,0.14); --accent-ring: rgba(124,140,255,0.40);
    --border: rgba(255,255,255,0.09); --border-strong: rgba(255,255,255,0.16);
  }
}

html, body {
  height: 100%;
  background: var(--bg-app);
  color: var(--text-primary);
  font-family: var(--font-sans);
  font-size: 14.5px;
  line-height: 1.6;
  -webkit-font-smoothing: antialiased;
  text-rendering: optimizeLegibility;
}
#app { height: 100%; }

a { color: var(--accent); text-decoration: none; }
a:hover { text-decoration: underline; }

::-webkit-scrollbar { width: 8px; height: 8px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: var(--border-strong); border-radius: 4px; }
::-webkit-scrollbar-thumb:hover { background: var(--text-muted); }

::selection { background: var(--accent-soft); }

:focus-visible { outline: 2px solid var(--accent-ring); outline-offset: 2px; border-radius: var(--radius-sm); }

/* ── Boutons ── */
.btn {
  display: inline-flex; align-items: center; justify-content: center; gap: 8px;
  padding: 9px 16px; border: 1px solid var(--border); border-radius: var(--radius-md);
  background: var(--bg-surface); color: var(--text-primary);
  font: inherit; font-weight: 550; cursor: pointer;
  transition: background 0.15s var(--ease), border-color 0.15s, transform 0.05s;
  white-space: nowrap;
}
.btn:hover { background: var(--bg-hover); }
.btn:active { transform: translateY(1px); }
.btn:disabled { opacity: 0.5; cursor: not-allowed; }
.btn-primary { background: var(--accent); border-color: var(--accent); color: var(--text-on-accent); }
.btn-primary:hover { background: var(--accent-hover); border-color: var(--accent-hover); }
.btn-ghost { background: transparent; border-color: transparent; }
.btn-ghost:hover { background: var(--bg-hover); }
.btn-danger { color: var(--error); border-color: var(--border); }
.btn-danger:hover { background: var(--error-soft); border-color: var(--error); }
.btn-sm { padding: 5px 10px; font-size: 13px; border-radius: var(--radius-sm); }
.btn-icon { padding: 8px; border-radius: var(--radius-md); }

/* ── Champs ── */
.input, .select, textarea.input {
  width: 100%; padding: 9px 12px; border: 1px solid var(--border);
  border-radius: var(--radius-md); background: var(--bg-surface); color: var(--text-primary);
  font: inherit; transition: border-color 0.15s, box-shadow 0.15s;
}
.input:focus, .select:focus, textarea.input:focus {
  outline: none; border-color: var(--accent); box-shadow: 0 0 0 3px var(--accent-ring);
}
.field { display: flex; flex-direction: column; gap: 6px; }
.field label { font-size: 12.5px; font-weight: 600; color: var(--text-secondary); }

/* ── Cartes ── */
.card {
  background: var(--bg-surface); border: 1px solid var(--border);
  border-radius: var(--radius-lg); box-shadow: var(--shadow-sm);
}
.card-pad { padding: 20px; }

/* ── Badges ── */
.badge {
  display: inline-flex; align-items: center; gap: 5px; padding: 2px 9px;
  border-radius: 999px; font-size: 12px; font-weight: 600;
  background: var(--bg-inset); color: var(--text-secondary);
}
.badge-accent { background: var(--accent-soft); color: var(--accent); }
.badge-success { background: var(--success-soft); color: var(--success); }
.badge-error { background: var(--error-soft); color: var(--error); }
.badge-warning { background: var(--warning-soft); color: var(--warning); }

/* ── Divers ── */
.muted { color: var(--text-secondary); }
.mono { font-family: var(--font-mono); }
.truncate { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.spinner {
  width: 16px; height: 16px; border: 2px solid var(--border-strong);
  border-top-color: var(--accent); border-radius: 50%; animation: spin 0.7s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }
@keyframes fadeIn { from { opacity: 0; transform: translateY(6px); } to { opacity: 1; transform: none; } }
@keyframes blink { 0%,100% { opacity: 1; } 50% { opacity: 0.15; } }

/* ── Markdown ── */
.markdown-body { line-height: 1.7; word-wrap: break-word; }
.markdown-body > *:first-child { margin-top: 0; }
.markdown-body > *:last-child { margin-bottom: 0; }
.markdown-body p { margin: 0 0 0.7rem; }
.markdown-body h1, .markdown-body h2, .markdown-body h3 { font-weight: 650; margin: 1.1rem 0 0.5rem; line-height: 1.3; }
.markdown-body h1 { font-size: 1.35em; }
.markdown-body h2 { font-size: 1.2em; }
.markdown-body h3 { font-size: 1.05em; }
.markdown-body ul, .markdown-body ol { padding-left: 1.4rem; margin: 0 0 0.7rem; }
.markdown-body li { margin-bottom: 0.25rem; }
.markdown-body blockquote {
  border-left: 3px solid var(--accent); padding-left: 1rem; margin: 0.7rem 0; color: var(--text-secondary);
}
.markdown-body code {
  font-family: var(--font-mono); font-size: 0.86em; background: var(--bg-inset);
  padding: 2px 6px; border-radius: var(--radius-sm);
}
.markdown-body pre {
  background: var(--bg-inset); border: 1px solid var(--border); border-radius: var(--radius-md);
  padding: 14px; overflow-x: auto; margin: 0.7rem 0;
}
.markdown-body pre code { background: none; padding: 0; }
.markdown-body table { width: 100%; border-collapse: collapse; margin: 0.7rem 0; font-size: 0.92em; }
.markdown-body th { text-align: left; padding: 7px 10px; border-bottom: 1px solid var(--border-strong); color: var(--text-secondary); }
.markdown-body td { padding: 7px 10px; border-bottom: 1px solid var(--border); }
.markdown-body a { text-decoration: underline; }
.markdown-body strong { font-weight: 650; }
</style>

<template>
  <div class="msg" :class="message.role">
    <div class="msg-avatar" :class="message.role">{{ message.role === 'user' ? '🙂' : '🎓' }}</div>
    <div class="msg-body">
      <div v-if="message.role === 'user'" class="msg-user">{{ message.content }}</div>

      <template v-else>
        <div class="msg-top">
          <StatusBanner :trace="message.trace" />
          <span v-if="streaming && !message.content" class="badge">
            <span class="spinner" /> Le tuteur réfléchit…
          </span>
        </div>

        <div class="markdown-body" v-html="rendered" />
        <span v-if="streaming" class="caret" />

        <details v-if="message.trace && (message.trace.sources?.length || message.trace.node_trace?.length)" class="msg-details">
          <summary>Détails RAG & orchestration</summary>
          <div class="details-body">
            <div v-if="message.trace.tool_used" class="detail-line">🧮 Outil : <span class="mono">{{ message.trace.tool_used }}</span></div>
            <div v-if="message.trace.frustration_score != null" class="detail-line">
              Frustration détectée : {{ message.trace.frustration_score }}
            </div>
            <template v-if="message.trace.sources?.length">
              <div class="detail-title">Sources RAG</div>
              <ul class="src-list">
                <li v-for="s in message.trace.sources" :key="s.id">
                  <span class="badge mono">{{ s.score?.toFixed?.(3) ?? s.score }}</span>
                  {{ s.label }} <span class="muted">({{ s.type_chunk }})</span>
                </li>
              </ul>
            </template>
            <template v-if="message.trace.node_trace?.length">
              <div class="detail-title">Orchestration (question → réponse)</div>
              <ol class="node-list">
                <li v-for="(n, i) in message.trace.node_trace" :key="i">
                  <span class="mono">{{ n.node }}</span>
                  <span class="muted"> · {{ n.duration_ms }} ms</span>
                </li>
              </ol>
            </template>
          </div>
        </details>

        <div v-if="message.messageId && !streaming" class="msg-actions">
          <button class="fb-btn" :class="{ on: message.feedback === 1 }" title="Utile" @click="$emit('feedback', 1)">👍</button>
          <button class="fb-btn" :class="{ on: message.feedback === -1 }" title="Pas utile" @click="$emit('feedback', -1)">👎</button>
        </div>
      </template>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { renderMarkdown } from '@/composables/useMarkdown.js'
import StatusBanner from './StatusBanner.vue'

const props = defineProps({
  message: { type: Object, required: true },
  streaming: { type: Boolean, default: false },
})
defineEmits(['feedback'])

const rendered = computed(() => renderMarkdown(props.message.content))
</script>

<style scoped>
.msg { display: flex; gap: 14px; padding: 18px 0; animation: fadeIn 0.25s var(--ease); }
.msg-avatar {
  width: 34px; height: 34px; border-radius: 50%; display: grid; place-items: center;
  font-size: 18px; flex-shrink: 0; background: var(--bg-inset); border: 1px solid var(--border);
}
.msg-avatar.assistant { background: var(--accent-soft); border-color: transparent; }
.msg-body { flex: 1; min-width: 0; padding-top: 3px; }
.msg-user { white-space: pre-wrap; }
.msg-top { display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 8px; }
.caret { display: inline-block; width: 8px; height: 1.1em; background: var(--accent); vertical-align: text-bottom; margin-left: 2px; animation: blink 1s step-start infinite; border-radius: 1px; }
.msg-details { margin-top: 12px; border: 1px solid var(--border); border-radius: var(--radius-md); background: var(--bg-inset); }
.msg-details summary { cursor: pointer; padding: 9px 12px; font-size: 13px; font-weight: 600; color: var(--text-secondary); }
.details-body { padding: 4px 14px 14px; font-size: 13px; }
.detail-line { margin: 4px 0; color: var(--text-secondary); }
.detail-title { font-weight: 700; margin: 12px 0 6px; font-size: 12px; text-transform: uppercase; letter-spacing: 0.04em; color: var(--text-muted); }
.src-list, .node-list { padding-left: 4px; list-style: none; display: flex; flex-direction: column; gap: 4px; }
.node-list { counter-reset: n; }
.msg-actions { display: flex; gap: 4px; margin-top: 12px; }
.fb-btn { border: 1px solid var(--border); background: var(--bg-surface); border-radius: var(--radius-md); padding: 3px 9px; cursor: pointer; font-size: 14px; transition: background 0.15s; }
.fb-btn:hover { background: var(--bg-hover); }
.fb-btn.on { background: var(--accent-soft); border-color: var(--accent); }
</style>

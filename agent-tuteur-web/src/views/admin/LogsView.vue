<template>
  <div class="admin-view">
    <header class="page-header">
      <div><h2>🪵 Logs de chat</h2><p class="muted">Derniers tours d'orchestration, tous élèves confondus.</p></div>
      <div class="actions">
        <select class="select limit-select" v-model.number="limit" @change="load">
          <option :value="25">25</option><option :value="50">50</option><option :value="100">100</option>
        </select>
        <button class="btn btn-sm" @click="load"><span v-if="loading" class="spinner" />Actualiser</button>
      </div>
    </header>

    <div class="page-scroll">
      <div class="page-inner">
        <p v-if="!entries.length && !loading" class="muted">Aucun log pour l'instant.</p>

        <details v-for="e in entries" :key="e.message_id" class="card log">
          <summary class="log-summary">
            <span class="badge">{{ e.student_id }}</span>
            <span class="log-q truncate">{{ e.trace?.question || '(question inconnue)' }}</span>
            <span class="muted small">{{ formatDate(e.created_at) }}</span>
          </summary>
          <div class="log-body">
            <div v-if="e.trace?.node_trace?.length" class="log-section">
              <div class="log-title">Orchestration</div>
              <ol class="node-list">
                <li v-for="(n, i) in e.trace.node_trace" :key="i">
                  <span class="mono">{{ n.node }}</span><span class="muted"> · {{ n.duration_ms }} ms</span>
                </li>
              </ol>
            </div>
            <div v-if="e.trace?.sources?.length" class="log-section">
              <div class="log-title">Sources</div>
              <ul class="src-list">
                <li v-for="s in e.trace.sources" :key="s.id"><span class="badge mono">{{ s.score?.toFixed?.(3) }}</span> {{ s.label }}</li>
              </ul>
            </div>
            <div v-if="e.trace?.generation" class="log-section">
              <div class="log-title">Génération</div>
              <pre class="gen mono">{{ JSON.stringify(e.trace.generation, null, 2) }}</pre>
            </div>
          </div>
        </details>
      </div>
    </div>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { logsApi, apiErrorMessage } from '@/services/api.js'

const entries = ref([])
const loading = ref(false)
const limit = ref(50)

function formatDate(iso) {
  try { return new Date(iso).toLocaleString('fr-FR', { dateStyle: 'short', timeStyle: 'medium' }) } catch { return iso }
}

async function load() {
  loading.value = true
  try {
    const { data } = await logsApi.chat(limit.value)
    entries.value = data
  } catch (e) {
    console.error(apiErrorMessage(e))
  } finally {
    loading.value = false
  }
}
onMounted(load)
</script>

<style scoped>
.admin-view { display: flex; flex-direction: column; height: 100%; }
.page-header { display: flex; align-items: center; justify-content: space-between; padding: 16px 24px; border-bottom: 1px solid var(--border); background: var(--bg-surface); }
.page-header h2 { font-size: 17px; }
.page-header p { font-size: 12.5px; margin-top: 2px; }
.actions { display: flex; gap: 8px; align-items: center; }
.limit-select { width: auto; padding: 6px 10px; }
.page-scroll { flex: 1; overflow-y: auto; padding: 24px; }
.page-inner { max-width: 900px; margin: 0 auto; display: flex; flex-direction: column; gap: 10px; }
.log-summary { display: flex; align-items: center; gap: 12px; padding: 13px 16px; cursor: pointer; }
.log-q { flex: 1; font-weight: 550; }
.small { font-size: 12px; }
.log-body { padding: 4px 16px 16px; display: flex; flex-direction: column; gap: 14px; }
.log-title { font-size: 11.5px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.04em; color: var(--text-muted); margin-bottom: 6px; }
.node-list, .src-list { list-style: none; display: flex; flex-direction: column; gap: 4px; font-size: 13px; }
.gen { background: var(--bg-inset); padding: 12px; border-radius: var(--radius-md); font-size: 12px; overflow-x: auto; }
</style>

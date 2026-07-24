<template>
  <div class="admin-view">
    <header class="page-header">
      <div><h2>📊 Tableau de bord</h2><p class="muted">État du système et raccourcis.</p></div>
      <button class="btn btn-sm" @click="load"><span v-if="loading" class="spinner" />Actualiser</button>
    </header>

    <div class="page-scroll">
      <div class="page-inner">
        <div class="grid">
          <div class="card card-pad tile">
            <div class="tile-label muted">API</div>
            <div class="tile-value"><span class="dot" :class="health.status === 'ok' ? 'ok' : 'warn'" />{{ health.status || '—' }}</div>
          </div>
          <div class="card card-pad tile">
            <div class="tile-label muted">Base de données</div>
            <div class="tile-value"><span class="dot" :class="health.db ? 'ok' : 'err'" />{{ health.db ? 'connectée' : 'indisponible' }}</div>
          </div>
          <div class="card card-pad tile">
            <div class="tile-label muted">Redis (file d'ingestion)</div>
            <div class="tile-value"><span class="dot" :class="health.redis === 'ok' ? 'ok' : 'warn'" />{{ health.redis || '—' }}</div>
          </div>
          <div class="card card-pad tile">
            <div class="tile-label muted">Vectorstore (Qdrant)</div>
            <div class="tile-value"><span class="dot" :class="qdrantClass" />{{ health.qdrant || '—' }}</div>
          </div>
          <div class="card card-pad tile">
            <div class="tile-label muted">Chaîne LLM</div>
            <div class="tile-value small">{{ (health.llm || []).join(' → ') || '—' }}</div>
          </div>
          <div class="card card-pad tile">
            <div class="tile-label muted">Documents orphelins</div>
            <div class="tile-value"><span class="dot" :class="health.documents_orphaned ? 'warn' : 'ok'" />{{ health.documents_orphaned ?? 0 }}</div>
          </div>
        </div>

        <div v-if="health.documents_orphaned" class="card card-pad alert">
          ⚠️ {{ health.documents_orphaned }} document(s) orphelin(s) détecté(s).
          <RouterLink to="/admin/documents">Voir les documents</RouterLink> pour les ré-uploader.
        </div>

        <section class="quick">
          <RouterLink to="/admin/documents" class="card card-pad quick-link">📚 Gérer les documents</RouterLink>
          <RouterLink to="/admin/search" class="card card-pad quick-link">🔍 Tester la recherche RAG</RouterLink>
          <RouterLink to="/admin/logs" class="card card-pad quick-link">🪵 Consulter les logs</RouterLink>
          <RouterLink to="/admin/users" class="card card-pad quick-link">👥 Gérer les comptes</RouterLink>
        </section>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { healthApi } from '@/services/api.js'

const loading = ref(false)
const health = ref({})

const qdrantClass = computed(() => {
  const q = health.value.qdrant
  if (q === 'ok') return 'ok'
  if (q === 'unreachable') return 'err'
  return 'muted-dot'
})

async function load() {
  loading.value = true
  try {
    const { data } = await healthApi.get()
    health.value = data
  } catch {
    health.value = { status: 'degraded', db: false }
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
.page-scroll { flex: 1; overflow-y: auto; padding: 24px; }
.page-inner { max-width: 960px; margin: 0 auto; display: flex; flex-direction: column; gap: 20px; }
.grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(210px, 1fr)); gap: 16px; }
.tile-label { font-size: 12.5px; margin-bottom: 8px; }
.tile-value { font-size: 20px; font-weight: 650; display: flex; align-items: center; gap: 8px; }
.tile-value.small { font-size: 15px; font-family: var(--font-mono); }
.dot { width: 10px; height: 10px; border-radius: 50%; flex-shrink: 0; }
.dot.ok { background: var(--success); }
.dot.warn { background: var(--warning); }
.dot.err { background: var(--error); }
.dot.muted-dot { background: var(--text-muted); }
.alert { background: var(--warning-soft); border-color: var(--warning); }
.quick { display: grid; grid-template-columns: repeat(auto-fill, minmax(230px, 1fr)); gap: 16px; }
.quick-link { text-decoration: none; color: var(--text-primary); font-weight: 600; transition: background 0.15s, transform 0.05s; }
.quick-link:hover { background: var(--bg-hover); text-decoration: none; }
</style>

<template>
  <div class="admin-view">
    <header class="page-header">
      <div><h2>🔍 Recherche RAG</h2><p class="muted">Interroge directement le retriever hybride (debug).</p></div>
    </header>

    <div class="page-scroll">
      <div class="page-inner">
        <form class="search-form card card-pad" @submit.prevent="run">
          <div class="field query-field">
            <label>Requête</label>
            <input class="input" v-model="query" placeholder="ex. dériver un quotient de fonctions" required />
          </div>
          <div class="opts">
            <div class="field"><label>Série</label><input class="input" v-model="serie" placeholder="S1, T1…" /></div>
            <div class="field"><label>Discipline</label><input class="input" v-model="discipline" placeholder="Mathématiques" /></div>
            <div class="field"><label>top_k</label><input class="input" type="number" min="1" max="50" v-model.number="topK" /></div>
            <button class="btn btn-primary run-btn" type="submit" :disabled="loading || !query.trim()">
              <span v-if="loading" class="spinner" />Rechercher
            </button>
          </div>
        </form>

        <p v-if="error" class="badge badge-error">{{ error }}</p>
        <p v-if="searched && !results.length && !loading" class="muted">Aucun résultat.</p>

        <div v-for="(r, i) in results" :key="r.id" class="card card-pad result">
          <div class="result-head">
            <span class="badge badge-accent mono">#{{ i + 1 }} · {{ r.score.toFixed(4) }}</span>
            <span v-if="r.dense_score != null" class="badge mono" title="score dense">D {{ r.dense_score.toFixed(3) }}</span>
            <span v-if="r.sparse_score != null" class="badge mono" title="score sparse">S {{ r.sparse_score.toFixed(3) }}</span>
            <span class="muted meta-inline">{{ metaLine(r.metadata) }}</span>
          </div>
          <p class="result-text">{{ r.text }}</p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { searchApi, apiErrorMessage } from '@/services/api.js'

const query = ref('')
const serie = ref('')
const discipline = ref('')
const topK = ref(5)
const results = ref([])
const loading = ref(false)
const searched = ref(false)
const error = ref('')

function metaLine(m = {}) {
  return [m.source_document, m.type_chunk, m.serie, m.chapitre].filter(Boolean).join(' · ')
}

async function run() {
  loading.value = true
  error.value = ''
  try {
    const ctx = {}
    if (serie.value) ctx.serie = serie.value
    if (discipline.value) ctx.discipline = discipline.value
    const { data } = await searchApi.search(query.value, ctx, topK.value)
    results.value = data
    searched.value = true
  } catch (e) {
    error.value = apiErrorMessage(e)
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.admin-view { display: flex; flex-direction: column; height: 100%; }
.page-header { padding: 16px 24px; border-bottom: 1px solid var(--border); background: var(--bg-surface); }
.page-header h2 { font-size: 17px; }
.page-header p { font-size: 12.5px; margin-top: 2px; }
.page-scroll { flex: 1; overflow-y: auto; padding: 24px; }
.page-inner { max-width: 860px; margin: 0 auto; display: flex; flex-direction: column; gap: 16px; }
.search-form { display: flex; flex-direction: column; gap: 14px; }
.opts { display: grid; grid-template-columns: 1fr 1fr 90px auto; gap: 12px; align-items: end; }
.run-btn { height: 40px; }
.result-head { display: flex; flex-wrap: wrap; align-items: center; gap: 8px; margin-bottom: 8px; }
.meta-inline { font-size: 12.5px; }
.result-text { white-space: pre-wrap; font-size: 13.5px; line-height: 1.6; }
</style>

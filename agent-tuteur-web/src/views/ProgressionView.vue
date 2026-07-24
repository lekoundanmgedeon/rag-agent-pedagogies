<template>
  <AppShell>
    <header class="page-header">
      <h2>📈 Ma progression</h2>
      <button class="btn btn-sm" @click="load"><span v-if="loading" class="spinner" />Actualiser</button>
    </header>

    <div class="page-scroll">
      <div class="page-inner">
        <div class="stats">
          <div class="card card-pad stat">
            <div class="stat-value">{{ data.history.length }}</div>
            <div class="stat-label muted">Questions posées</div>
          </div>
          <div class="card card-pad stat">
            <div class="stat-value">{{ data.recurrent_difficulties.length }}</div>
            <div class="stat-label muted">Difficultés récurrentes</div>
          </div>
          <div class="card card-pad stat">
            <div class="stat-value">{{ avgHint }}</div>
            <div class="stat-label muted">Niveau d'indice moyen</div>
          </div>
        </div>

        <section v-if="data.recurrent_difficulties.length" class="card card-pad section">
          <h3>Notions à retravailler</h3>
          <div class="diff-badges">
            <span v-for="d in data.recurrent_difficulties" :key="d" class="badge badge-warning">{{ d }}</span>
          </div>
        </section>

        <section class="card section">
          <h3 class="section-title">Historique</h3>
          <p v-if="!data.history.length" class="muted empty-hint">Aucune activité pour l'instant — commence une conversation !</p>
          <ul v-else class="hist">
            <li v-for="h in reversedHistory" :key="h.id" class="hist-item">
              <div class="hist-main">
                <span class="hist-q truncate">{{ h.question }}</span>
                <span v-if="h.competence" class="badge">{{ h.competence }}</span>
              </div>
              <div class="hist-meta muted">
                <span>Indice niveau {{ h.hint_level }}</span>
                <span>·</span>
                <span>{{ formatDate(h.created_at) }}</span>
              </div>
            </li>
          </ul>
        </section>
      </div>
    </div>
  </AppShell>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useAuthStore } from '@/stores/auth.js'
import { progressionApi, apiErrorMessage } from '@/services/api.js'
import AppShell from '@/components/layout/AppShell.vue'

const auth = useAuthStore()
const loading = ref(false)
const data = ref({ student_id: '', history: [], recurrent_difficulties: [] })

const studentId = computed(() => auth.user?.student_id || auth.user?.id)
const reversedHistory = computed(() => [...data.value.history].reverse())
const avgHint = computed(() => {
  const h = data.value.history
  if (!h.length) return '—'
  return (h.reduce((s, e) => s + (e.hint_level || 0), 0) / h.length).toFixed(1)
})

function formatDate(iso) {
  try {
    return new Date(iso).toLocaleString('fr-FR', { dateStyle: 'short', timeStyle: 'short' })
  } catch {
    return iso
  }
}

async function load() {
  if (!studentId.value) return
  loading.value = true
  try {
    const { data: d } = await progressionApi.get(studentId.value)
    data.value = d
  } catch (e) {
    console.error(apiErrorMessage(e))
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>

<style scoped>
.page-header { display: flex; align-items: center; justify-content: space-between; padding: 16px 24px; border-bottom: 1px solid var(--border); background: var(--bg-surface); }
.page-header h2 { font-size: 17px; }
.page-scroll { flex: 1; overflow-y: auto; padding: 24px; }
.page-inner { max-width: 860px; margin: 0 auto; display: flex; flex-direction: column; gap: 20px; }
.stats { display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px; }
.stat { text-align: center; }
.stat-value { font-size: 30px; font-weight: 700; color: var(--accent); }
.stat-label { font-size: 13px; margin-top: 2px; }
.section { padding: 20px; }
.section h3 { font-size: 15px; margin-bottom: 12px; }
.section-title { padding: 20px 20px 0; }
.diff-badges { display: flex; flex-wrap: wrap; gap: 8px; }
.empty-hint { padding: 0 20px 20px; }
.hist { list-style: none; }
.hist-item { padding: 12px 20px; border-top: 1px solid var(--border); }
.hist-main { display: flex; align-items: center; gap: 10px; justify-content: space-between; }
.hist-q { flex: 1; font-weight: 550; }
.hist-meta { display: flex; gap: 6px; font-size: 12.5px; margin-top: 4px; }
</style>

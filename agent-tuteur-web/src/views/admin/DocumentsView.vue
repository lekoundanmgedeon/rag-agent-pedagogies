<template>
  <div class="admin-view">
    <header class="page-header">
      <div><h2>📚 Documents</h2><p class="muted">Corpus curriculaire indexé pour le RAG.</p></div>
      <div class="actions">
        <button class="btn btn-sm" @click="verifyAll" :disabled="verifying"><span v-if="verifying" class="spinner" />Vérifier la cohérence</button>
        <button class="btn btn-sm" @click="load">Actualiser</button>
        <button class="btn btn-primary btn-sm" @click="showUpload = true">＋ Ajouter</button>
      </div>
    </header>

    <div class="page-scroll">
      <div class="page-inner">
        <p v-if="notice" class="badge badge-success notice">{{ notice }}</p>

        <div v-if="loading" class="loading muted"><span class="spinner" /> Chargement…</div>
        <div v-else-if="!documents.length" class="empty card card-pad">
          <p>Aucun document indexé.</p>
          <button class="btn btn-primary" @click="showUpload = true">Ajouter un premier document</button>
        </div>

        <div v-else class="table-wrap card">
          <table class="table">
            <thead>
              <tr><th>Fichier</th><th>Contexte</th><th>Type</th><th>Statut</th><th>Ajouté</th><th></th></tr>
            </thead>
            <tbody>
              <tr v-for="d in documents" :key="d.id">
                <td class="cell-name">{{ d.filename }}</td>
                <td class="muted">{{ contextOf(d) }}</td>
                <td><span class="badge mono">{{ d.doc_type }}</span></td>
                <td><span class="badge" :class="statusClass(d.status)">{{ statusLabel(d.status) }}<span v-if="d.status === 'pending'" class="spinner sm" /></span></td>
                <td class="muted small">{{ formatDate(d.created_at) }}</td>
                <td class="cell-actions">
                  <label class="btn btn-sm btn-ghost" title="Ré-indexer (nouveau fichier)">
                    ↻<input type="file" class="hidden-file" :accept="accept" @change="(e) => reindex(d, e)" />
                  </label>
                  <button class="btn btn-sm btn-danger" title="Supprimer" @click="remove(d)">🗑</button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>

        <p v-for="d in erroredDocs" :key="d.id + '-err'" class="doc-error badge badge-error">
          {{ d.filename }} : {{ d.error }}
        </p>
      </div>
    </div>

    <UploadDialog v-if="showUpload" @close="showUpload = false" @uploaded="onUploaded" />
  </div>
</template>

<script setup>
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { documentsApi, apiErrorMessage } from '@/services/api.js'
import UploadDialog from '@/components/admin/UploadDialog.vue'

const accept = '.md,.txt,.pdf,.docx'
const documents = ref([])
const loading = ref(false)
const verifying = ref(false)
const showUpload = ref(false)
const notice = ref('')
const watchers = new Map() // documentId -> unsubscribe

const erroredDocs = computed(() => documents.value.filter((d) => d.status === 'failed' || d.status === 'orphaned'))

function statusLabel(s) {
  return { pending: 'en cours', indexed: 'indexé', failed: 'échec', orphaned: 'orphelin' }[s] || s
}
function statusClass(s) {
  return { pending: 'badge-warning', indexed: 'badge-success', failed: 'badge-error', orphaned: 'badge-error' }[s] || ''
}
function contextOf(d) {
  const m = d.metadata || {}
  return [m.niveau, m.serie, m.discipline, m.chapitre].filter(Boolean).join(' · ') || '—'
}
function formatDate(iso) {
  try { return new Date(iso).toLocaleDateString('fr-FR', { dateStyle: 'medium' }) } catch { return iso }
}

async function load() {
  loading.value = true
  try {
    const { data } = await documentsApi.list()
    documents.value = data
    data.filter((d) => d.status === 'pending').forEach(watchStatus)
  } catch (e) {
    notice.value = ''
    console.error(apiErrorMessage(e))
  } finally {
    loading.value = false
  }
}

function watchStatus(doc) {
  if (watchers.has(doc.id)) return
  const stop = documentsApi.watchStatus(doc.id, (evt) => {
    const row = documents.value.find((d) => d.id === doc.id)
    if (row && evt.status) {
      row.status = evt.status
      if (evt.error) row.error = evt.error
    }
    if (['indexed', 'failed', 'orphaned', 'not_found'].includes(evt.status)) {
      stop(); watchers.delete(doc.id)
      documentsApi.get(doc.id).then(({ data }) => {
        const idx = documents.value.findIndex((d) => d.id === doc.id)
        if (idx >= 0) documents.value[idx] = data
      }).catch(() => {})
    }
  })
  watchers.set(doc.id, stop)
}

function onUploaded(created) {
  showUpload.value = false
  notice.value = `${created.length} document(s) en cours d'indexation.`
  load()
}

async function reindex(doc, event) {
  const file = event.target.files[0]
  event.target.value = ''
  if (!file) return
  try {
    await documentsApi.reindex(doc.id, file)
    doc.status = 'pending'
    watchStatus(doc)
    notice.value = `Ré-indexation de ${doc.filename} lancée.`
  } catch (e) {
    notice.value = apiErrorMessage(e)
  }
}

async function remove(doc) {
  if (!confirm(`Supprimer « ${doc.filename} » et ses vecteurs ?`)) return
  try {
    await documentsApi.remove(doc.id)
    documents.value = documents.value.filter((d) => d.id !== doc.id)
  } catch (e) {
    notice.value = apiErrorMessage(e)
  }
}

async function verifyAll() {
  verifying.value = true
  try {
    const { data } = await documentsApi.verifyAll()
    notice.value = data.orphaned.length
      ? `${data.orphaned.length} document(s) orphelin(s) détecté(s) sur ${data.checked} vérifié(s).`
      : `${data.checked} document(s) vérifié(s) — tout est cohérent.`
    await load()
  } catch (e) {
    notice.value = apiErrorMessage(e)
  } finally {
    verifying.value = false
  }
}

onMounted(load)
onUnmounted(() => { for (const stop of watchers.values()) stop() })
</script>

<style scoped>
.admin-view { display: flex; flex-direction: column; height: 100%; }
.page-header { display: flex; align-items: center; justify-content: space-between; padding: 16px 24px; border-bottom: 1px solid var(--border); background: var(--bg-surface); gap: 16px; }
.page-header h2 { font-size: 17px; }
.page-header p { font-size: 12.5px; margin-top: 2px; }
.actions { display: flex; gap: 8px; }
.page-scroll { flex: 1; overflow-y: auto; padding: 24px; }
.page-inner { max-width: 1000px; margin: 0 auto; display: flex; flex-direction: column; gap: 16px; }
.notice { justify-content: flex-start; }
.loading { display: flex; align-items: center; gap: 8px; padding: 24px; }
.empty { text-align: center; display: flex; flex-direction: column; gap: 14px; align-items: center; }
.table-wrap { overflow-x: auto; }
.table { width: 100%; border-collapse: collapse; font-size: 13.5px; }
.table th { text-align: left; padding: 12px 14px; border-bottom: 1px solid var(--border-strong); color: var(--text-secondary); font-size: 12px; text-transform: uppercase; letter-spacing: 0.03em; white-space: nowrap; }
.table td { padding: 11px 14px; border-bottom: 1px solid var(--border); vertical-align: middle; }
.table tr:last-child td { border-bottom: none; }
.cell-name { font-weight: 550; }
.cell-actions { display: flex; gap: 6px; justify-content: flex-end; }
.hidden-file { display: none; }
.spinner.sm { width: 11px; height: 11px; border-width: 2px; }
.doc-error { justify-content: flex-start; }
.small { font-size: 12px; }
</style>

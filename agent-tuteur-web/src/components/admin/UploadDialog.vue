<template>
  <div class="overlay" @click.self="$emit('close')">
    <div class="dialog card">
      <header class="dialog-head">
        <h3>📤 Ajouter des documents</h3>
        <button class="btn btn-icon btn-ghost" @click="$emit('close')">✕</button>
      </header>

      <div class="dialog-body">
        <label class="dropzone" :class="{ over: dragover }"
          @dragover.prevent="dragover = true" @dragleave="dragover = false" @drop.prevent="onDrop">
          <input type="file" multiple class="sr-only" @change="onPick" :accept="accept" />
          <div class="dz-inner">
            <div class="dz-icon">📎</div>
            <p><strong>Clique</strong> ou dépose des fichiers ici</p>
            <p class="muted small">Formats : {{ accept }}</p>
          </div>
        </label>

        <ul v-if="files.length" class="file-list">
          <li v-for="(f, i) in files" :key="i">
            <span class="truncate">{{ f.name }}</span>
            <span class="muted small">{{ formatSize(f.size) }}</span>
            <button class="btn btn-icon btn-ghost btn-sm" @click="files.splice(i, 1)">✕</button>
          </li>
        </ul>

        <details class="meta" open>
          <summary>Métadonnées curriculaires (optionnel)</summary>
          <div class="meta-grid">
            <div class="field"><label>Niveau</label>
              <select class="select" v-model="meta.niveau">
                <option value="">—</option>
                <option v-for="n in niveaux" :key="n" :value="n">{{ n }}</option>
              </select>
            </div>
            <div class="field"><label>Classe</label><input class="input" v-model="meta.classe" placeholder="ex. Terminale" /></div>
            <div class="field"><label>Série</label><input class="input" v-model="meta.serie" placeholder="ex. S1, T1…" /></div>
            <div class="field"><label>Discipline</label><input class="input" v-model="meta.discipline" placeholder="ex. Mathématiques" /></div>
            <div class="field"><label>Chapitre</label><input class="input" v-model="meta.chapitre" placeholder="ex. Dérivées" /></div>
            <div class="field"><label>Compétence</label><input class="input" v-model="meta.competence" /></div>
            <div class="field"><label>Examen associé</label><input class="input" v-model="meta.examen_associe" placeholder="ex. Baccalauréat" /></div>
          </div>
        </details>

        <div v-if="progress > 0 && progress < 100" class="progress"><div class="progress-bar" :style="{ width: progress + '%' }" /></div>
        <p v-if="error" class="badge badge-error err-line">{{ error }}</p>
      </div>

      <footer class="dialog-foot">
        <button class="btn" @click="$emit('close')">Annuler</button>
        <button class="btn btn-primary" :disabled="!files.length || uploading" @click="submit">
          <span v-if="uploading" class="spinner" />{{ uploading ? 'Envoi…' : `Envoyer ${files.length || ''}` }}
        </button>
      </footer>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { documentsApi, apiErrorMessage } from '@/services/api.js'

const emit = defineEmits(['close', 'uploaded'])
const accept = '.md,.txt,.pdf,.docx'
const niveaux = ['préscolaire', 'élémentaire', 'moyen', 'secondaire', 'EBJA']

const files = ref([])
const meta = ref({ niveau: '', classe: '', serie: '', discipline: '', chapitre: '', competence: '', examen_associe: '' })
const dragover = ref(false)
const uploading = ref(false)
const progress = ref(0)
const error = ref('')

function onPick(e) { files.value.push(...e.target.files) }
function onDrop(e) { dragover.value = false; files.value.push(...e.dataTransfer.files) }
function formatSize(b) { return b < 1024 * 1024 ? `${(b / 1024).toFixed(0)} Ko` : `${(b / 1024 / 1024).toFixed(1)} Mo` }

async function submit() {
  if (!files.value.length) return
  uploading.value = true
  error.value = ''
  try {
    const { data } = await documentsApi.upload(files.value, meta.value, (p) => (progress.value = p))
    emit('uploaded', data)
    emit('close')
  } catch (e) {
    error.value = apiErrorMessage(e, "Échec de l'upload.")
  } finally {
    uploading.value = false
    progress.value = 0
  }
}
</script>

<style scoped>
.overlay { position: fixed; inset: 0; background: rgba(10, 14, 20, 0.55); display: grid; place-items: center; padding: 24px; z-index: 50; animation: fadeIn 0.2s var(--ease); }
.dialog { width: 100%; max-width: 560px; max-height: 90vh; display: flex; flex-direction: column; box-shadow: var(--shadow-lg); }
.dialog-head { display: flex; align-items: center; justify-content: space-between; padding: 16px 20px; border-bottom: 1px solid var(--border); }
.dialog-head h3 { font-size: 16px; }
.dialog-body { padding: 20px; overflow-y: auto; display: flex; flex-direction: column; gap: 16px; }
.dropzone { display: block; border: 2px dashed var(--border-strong); border-radius: var(--radius-lg); padding: 28px; text-align: center; cursor: pointer; transition: border-color 0.15s, background 0.15s; }
.dropzone:hover, .dropzone.over { border-color: var(--accent); background: var(--accent-soft); }
.dz-icon { font-size: 30px; }
.small { font-size: 12px; }
.file-list { list-style: none; display: flex; flex-direction: column; gap: 6px; }
.file-list li { display: flex; align-items: center; gap: 10px; padding: 7px 10px; background: var(--bg-inset); border-radius: var(--radius-md); }
.file-list li span:first-child { flex: 1; }
.meta summary { cursor: pointer; font-weight: 600; font-size: 13.5px; color: var(--text-secondary); }
.meta-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-top: 12px; }
.progress { height: 6px; background: var(--bg-inset); border-radius: 3px; overflow: hidden; }
.progress-bar { height: 100%; background: var(--accent); transition: width 0.2s; }
.err-line { justify-content: flex-start; }
.dialog-foot { display: flex; justify-content: flex-end; gap: 10px; padding: 14px 20px; border-top: 1px solid var(--border); }
.sr-only { position: absolute; width: 1px; height: 1px; overflow: hidden; clip: rect(0,0,0,0); }
</style>

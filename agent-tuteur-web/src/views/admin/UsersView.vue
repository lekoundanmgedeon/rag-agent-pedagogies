<template>
  <div class="admin-view">
    <header class="page-header">
      <div><h2>👥 Comptes</h2><p class="muted">Élèves et administrateurs de ton établissement.</p></div>
      <button class="btn btn-primary btn-sm" @click="showForm = !showForm">＋ Nouveau compte</button>
    </header>

    <div class="page-scroll">
      <div class="page-inner">
        <form v-if="showForm" class="card card-pad create-form" @submit.prevent="create">
          <h3>Créer un compte</h3>
          <div class="form-grid">
            <div class="field"><label>E-mail *</label><input class="input" type="email" v-model="form.email" required /></div>
            <div class="field"><label>Mot de passe *</label><input class="input" type="text" v-model="form.password" minlength="6" required placeholder="min. 6 caractères" /></div>
            <div class="field"><label>Rôle</label>
              <select class="select" v-model="form.role"><option value="student">Élève</option><option value="admin">Administrateur</option></select>
            </div>
            <div class="field" v-if="form.role === 'student'"><label>Identifiant élève</label><input class="input" v-model="form.student_id" placeholder="ex. eleve1" /></div>
            <div class="field"><label>Nom affiché</label><input class="input" v-model="form.display_name" /></div>
          </div>
          <p v-if="error" class="badge badge-error err-line">{{ error }}</p>
          <div class="form-actions">
            <button type="button" class="btn" @click="showForm = false">Annuler</button>
            <button class="btn btn-primary" type="submit" :disabled="saving"><span v-if="saving" class="spinner" />Créer</button>
          </div>
        </form>

        <p v-if="notice" class="badge badge-success notice">{{ notice }}</p>

        <div class="table-wrap card">
          <table class="table">
            <thead><tr><th>E-mail</th><th>Rôle</th><th>Identifiant élève</th><th>Nom</th></tr></thead>
            <tbody>
              <tr v-for="u in users" :key="u.id">
                <td class="cell-email">{{ u.email }}</td>
                <td><span class="badge" :class="u.role === 'admin' ? 'badge-accent' : ''">{{ u.role === 'admin' ? 'Admin' : 'Élève' }}</span></td>
                <td class="muted mono">{{ u.student_id || '—' }}</td>
                <td class="muted">{{ u.display_name || '—' }}</td>
              </tr>
              <tr v-if="!users.length"><td colspan="4" class="muted empty-row">Aucun compte.</td></tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { authApi, apiErrorMessage } from '@/services/api.js'

const users = ref([])
const showForm = ref(false)
const saving = ref(false)
const error = ref('')
const notice = ref('')
const form = reactive({ email: '', password: '', role: 'student', student_id: '', display_name: '' })

async function load() {
  try {
    const { data } = await authApi.listUsers()
    users.value = data
  } catch (e) {
    console.error(apiErrorMessage(e))
  }
}

async function create() {
  saving.value = true
  error.value = ''
  try {
    const payload = { email: form.email, password: form.password, role: form.role, display_name: form.display_name || null }
    if (form.role === 'student') payload.student_id = form.student_id || null
    await authApi.createUser(payload)
    notice.value = `Compte ${form.email} créé.`
    Object.assign(form, { email: '', password: '', role: 'student', student_id: '', display_name: '' })
    showForm.value = false
    await load()
  } catch (e) {
    error.value = apiErrorMessage(e, 'Échec de la création.')
  } finally {
    saving.value = false
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
.page-inner { max-width: 900px; margin: 0 auto; display: flex; flex-direction: column; gap: 16px; }
.create-form { display: flex; flex-direction: column; gap: 14px; }
.create-form h3 { font-size: 15px; }
.form-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; }
.form-actions { display: flex; justify-content: flex-end; gap: 10px; }
.err-line, .notice { justify-content: flex-start; }
.table-wrap { overflow-x: auto; }
.table { width: 100%; border-collapse: collapse; font-size: 13.5px; }
.table th { text-align: left; padding: 12px 14px; border-bottom: 1px solid var(--border-strong); color: var(--text-secondary); font-size: 12px; text-transform: uppercase; letter-spacing: 0.03em; }
.table td { padding: 11px 14px; border-bottom: 1px solid var(--border); }
.table tr:last-child td { border-bottom: none; }
.cell-email { font-weight: 550; }
.empty-row { text-align: center; padding: 20px; }
</style>

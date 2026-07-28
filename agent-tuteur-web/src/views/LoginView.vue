<template>
  <div class="login-page">
    <div class="login-topbar">
      <ThemeToggle />
    </div>

    <div class="login-card card">
      <div class="login-brand">
        <span class="login-logo">🎓</span>
        <h1>Agent Tuteur Sénégal</h1>
        <p class="muted">Connecte-toi pour accéder à ton espace.</p>
      </div>

      <form class="login-form" @submit.prevent="submit">
        <div class="field">
          <label for="email">Adresse e-mail</label>
          <input id="email" v-model="email" class="input" type="email" autocomplete="email" required placeholder="prenom@ecole.sn" />
        </div>
        <div class="field">
          <label for="password">Mot de passe</label>
          <input id="password" v-model="password" class="input" type="password" autocomplete="current-password" required placeholder="••••••••" />
        </div>

        <p v-if="auth.error" class="login-error badge badge-error">{{ auth.error }}</p>

        <button class="btn btn-primary login-submit" type="submit" :disabled="auth.loading">
          <span v-if="auth.loading" class="spinner" />
          {{ auth.loading ? 'Connexion…' : 'Se connecter' }}
        </button>
      </form>

      <p class="login-hint muted">
        Pas de compte ? Demande à ton administrateur de t'en créer un.
      </p>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth.js'
import ThemeToggle from '@/components/layout/ThemeToggle.vue'

const email = ref('')
const password = ref('')
const auth = useAuthStore()
const route = useRoute()
const router = useRouter()

async function submit() {
  const ok = await auth.login(email.value, password.value)
  if (ok) router.push(route.query.redirect || '/')
}
</script>

<style scoped>
.login-page {
  min-height: 100vh; display: grid; place-items: center; padding: 24px;
  background: radial-gradient(1200px 600px at 50% -10%, var(--accent-soft), transparent 70%), var(--bg-app);
}
.login-topbar { position: fixed; top: 16px; right: 16px; }
.login-card { width: 100%; max-width: 400px; padding: 32px; animation: fadeIn 0.4s var(--ease); }
.login-brand { text-align: center; margin-bottom: 24px; }
.login-logo { font-size: 40px; }
.login-brand h1 { font-size: 21px; margin: 8px 0 4px; }
.login-form { display: flex; flex-direction: column; gap: 16px; }
.login-error { width: 100%; justify-content: flex-start; }
.login-submit { width: 100%; margin-top: 4px; padding: 11px; }
.login-hint { text-align: center; font-size: 12.5px; margin-top: 20px; }
</style>

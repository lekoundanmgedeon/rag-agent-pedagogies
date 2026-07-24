<template>
  <div class="shell">
    <aside class="admin-sidebar">
      <div class="sidebar-head">
        <div class="brand"><span class="brand-logo">🛠️</span><span class="brand-name">Administration</span></div>
        <ThemeToggle />
      </div>

      <nav class="nav">
        <RouterLink to="/admin" class="nav-link" :class="{ active: route.name === 'admin-home' }" active-class="" exact-active-class="">📊 Tableau de bord</RouterLink>
        <RouterLink to="/admin/documents" class="nav-link">📚 Documents</RouterLink>
        <RouterLink to="/admin/search" class="nav-link">🔍 Recherche RAG</RouterLink>
        <RouterLink to="/admin/logs" class="nav-link">🪵 Logs</RouterLink>
        <RouterLink to="/admin/users" class="nav-link">👥 Comptes</RouterLink>
      </nav>

      <div class="nav sep">
        <RouterLink to="/" class="nav-link">← Espace élève</RouterLink>
      </div>

      <div class="sidebar-foot">
        <div class="user">
          <div class="user-avatar">{{ initial }}</div>
          <div class="user-meta">
            <div class="user-name truncate">{{ auth.displayName }}</div>
            <div class="user-role muted">Administrateur</div>
          </div>
          <button class="btn btn-icon btn-ghost" title="Se déconnecter" @click="logout">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4M16 17l5-5-5-5M21 12H9" /></svg>
          </button>
        </div>
      </div>
    </aside>

    <main class="shell-main">
      <router-view />
    </main>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth.js'
import ThemeToggle from '@/components/layout/ThemeToggle.vue'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const initial = computed(() => (auth.displayName || '?').charAt(0).toUpperCase())

function logout() {
  auth.logout()
  router.push('/login')
}
</script>

<style scoped>
.shell { display: flex; height: 100vh; overflow: hidden; }
.shell-main { flex: 1; min-width: 0; display: flex; flex-direction: column; overflow: hidden; }
.admin-sidebar { width: var(--sidebar-w); flex-shrink: 0; background: var(--bg-sidebar); border-right: 1px solid var(--border); display: flex; flex-direction: column; padding: 14px; }
.sidebar-head { display: flex; align-items: center; justify-content: space-between; margin-bottom: 18px; }
.brand { display: flex; align-items: center; gap: 8px; font-weight: 700; font-size: 15px; }
.brand-logo { font-size: 18px; }
.nav { display: flex; flex-direction: column; gap: 2px; }
.nav.sep { margin-top: auto; padding-top: 12px; border-top: 1px solid var(--border); }
.nav-link { display: flex; align-items: center; gap: 8px; padding: 9px 11px; border-radius: var(--radius-md); color: var(--text-secondary); font-weight: 550; text-decoration: none; transition: background 0.15s; }
.nav-link:hover { background: var(--bg-hover); text-decoration: none; }
.nav-link.router-link-active, .nav-link.active { background: var(--accent-soft); color: var(--accent); }
.sidebar-foot { border-top: 1px solid var(--border); padding-top: 12px; margin-top: 12px; }
.user { display: flex; align-items: center; gap: 10px; }
.user-avatar { width: 34px; height: 34px; border-radius: 50%; background: var(--accent); color: #fff; display: grid; place-items: center; font-weight: 700; flex-shrink: 0; }
.user-meta { flex: 1; min-width: 0; }
.user-name { font-weight: 600; font-size: 13.5px; }
.user-role { font-size: 12px; }
</style>

<template>
  <aside class="sidebar">
    <div class="sidebar-head">
      <div class="brand">
        <span class="brand-logo">🎓</span>
        <span class="brand-name">Tuteur Sénégal</span>
      </div>
      <ThemeToggle />
    </div>

    <button class="btn btn-primary new-btn" @click="startNew">
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M12 5v14M5 12h14" /></svg>
      Nouvelle conversation
    </button>

    <nav class="nav">
      <RouterLink to="/" class="nav-link" :class="{ active: route.name === 'chat' || route.name === 'conversation' }">💬 Chat</RouterLink>
      <RouterLink to="/progression" class="nav-link" :class="{ active: route.name === 'progression' }">📈 Ma progression</RouterLink>
      <RouterLink v-if="auth.isAdmin" to="/admin" class="nav-link">🛠️ Administration</RouterLink>
    </nav>

    <div class="conv-head">Conversations</div>
    <div class="conv-list">
      <p v-if="!chat.conversations.length" class="conv-empty muted">Aucune conversation pour l'instant.</p>
      <div
        v-for="c in chat.conversations"
        :key="c.id"
        class="conv-item"
        :class="{ active: c.id === chat.conversationId }"
        @click="open(c.id)"
      >
        <span class="conv-title truncate">{{ c.title || 'Sans titre' }}</span>
        <button class="conv-del" title="Supprimer" @click.stop="remove(c.id)">
          <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M3 6h18M8 6V4h8v2M19 6l-1 14H6L5 6" /></svg>
        </button>
      </div>
    </div>

    <div class="sidebar-foot">
      <div class="user">
        <div class="user-avatar">{{ initial }}</div>
        <div class="user-meta">
          <div class="user-name truncate">{{ auth.displayName }}</div>
          <div class="user-role muted">{{ auth.isAdmin ? 'Administrateur' : 'Élève' }}</div>
        </div>
        <button class="btn btn-icon btn-ghost" title="Se déconnecter" @click="logout">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4M16 17l5-5-5-5M21 12H9" /></svg>
        </button>
      </div>
    </div>
  </aside>
</template>

<script setup>
import { computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth.js'
import { useChatStore } from '@/stores/chat.js'
import ThemeToggle from './ThemeToggle.vue'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const chat = useChatStore()

const initial = computed(() => (auth.displayName || '?').charAt(0).toUpperCase())

onMounted(() => chat.loadConversations())

function startNew() {
  chat.newConversation()
  router.push('/')
}
function open(id) {
  router.push(`/c/${id}`)
}
async function remove(id) {
  if (!confirm('Supprimer cette conversation ?')) return
  await chat.deleteConversation(id)
  if (route.params.id === id) router.push('/')
}
function logout() {
  auth.logout()
  router.push('/login')
}
</script>

<style scoped>
.sidebar {
  width: var(--sidebar-w); flex-shrink: 0; height: 100vh;
  background: var(--bg-sidebar); border-right: 1px solid var(--border);
  display: flex; flex-direction: column; padding: 14px;
}
.sidebar-head { display: flex; align-items: center; justify-content: space-between; margin-bottom: 14px; }
.brand { display: flex; align-items: center; gap: 8px; font-weight: 700; font-size: 15px; }
.brand-logo { font-size: 20px; }
.new-btn { width: 100%; margin-bottom: 14px; }
.nav { display: flex; flex-direction: column; gap: 2px; margin-bottom: 16px; }
.nav-link {
  display: flex; align-items: center; gap: 8px; padding: 8px 10px; border-radius: var(--radius-md);
  color: var(--text-secondary); font-weight: 550; text-decoration: none; transition: background 0.15s;
}
.nav-link:hover { background: var(--bg-hover); text-decoration: none; }
.nav-link.active { background: var(--accent-soft); color: var(--accent); }
.conv-head { font-size: 11.5px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em; color: var(--text-muted); padding: 0 10px 8px; }
.conv-list { flex: 1; overflow-y: auto; display: flex; flex-direction: column; gap: 2px; }
.conv-empty { padding: 8px 10px; font-size: 13px; }
.conv-item {
  display: flex; align-items: center; gap: 6px; padding: 8px 10px; border-radius: var(--radius-md);
  cursor: pointer; color: var(--text-primary); transition: background 0.15s;
}
.conv-item:hover { background: var(--bg-hover); }
.conv-item.active { background: var(--bg-active); }
.conv-title { flex: 1; font-size: 13.5px; }
.conv-del { border: none; background: none; color: var(--text-muted); cursor: pointer; opacity: 0; padding: 2px; display: flex; border-radius: var(--radius-sm); }
.conv-item:hover .conv-del { opacity: 1; }
.conv-del:hover { color: var(--error); background: var(--error-soft); }
.sidebar-foot { border-top: 1px solid var(--border); padding-top: 12px; margin-top: 8px; }
.user { display: flex; align-items: center; gap: 10px; }
.user-avatar {
  width: 34px; height: 34px; border-radius: 50%; background: var(--accent); color: #fff;
  display: grid; place-items: center; font-weight: 700; flex-shrink: 0;
}
.user-meta { flex: 1; min-width: 0; }
.user-name { font-weight: 600; font-size: 13.5px; }
.user-role { font-size: 12px; }
</style>

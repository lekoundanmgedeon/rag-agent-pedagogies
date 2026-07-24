<template>
  <AppShell>
    <header class="chat-header">
      <div class="ch-title">
        <h2>{{ headerTitle }}</h2>
        <p class="muted">Le tuteur guide par indices progressifs ou en cours structuré, selon ta demande.</p>
      </div>
      <button class="btn btn-sm" @click="showCtx = !showCtx">⚙️ Contexte</button>
    </header>

    <div v-if="showCtx" class="ctx-bar card">
      <div class="field">
        <label>Niveau</label>
        <select class="select" :value="chat.curriculum.niveau" @change="setCtx('niveau', $event.target.value)">
          <option v-for="n in niveaux" :key="n" :value="n">{{ n }}</option>
        </select>
      </div>
      <div class="field">
        <label>Série (secondaire)</label>
        <input class="input" :value="chat.curriculum.serie" placeholder="ex. S1, L2, T1…" @change="setCtx('serie', $event.target.value)" />
      </div>
      <div class="field">
        <label>Discipline</label>
        <input class="input" :value="chat.curriculum.discipline" placeholder="ex. Mathématiques" @change="setCtx('discipline', $event.target.value)" />
      </div>
    </div>

    <div ref="scroller" class="chat-scroll">
      <div class="chat-inner">
        <div v-if="!chat.messages.length" class="empty">
          <div class="empty-logo">🎓</div>
          <h3>Bonjour {{ auth.displayName }} 👋</h3>
          <p class="muted">Pose ta première question — sur une notion, un exercice, ou demande un cours complet.</p>
          <div class="suggestions">
            <button v-for="s in suggestions" :key="s" class="btn btn-sm suggestion" @click="send(s)">{{ s }}</button>
          </div>
        </div>

        <ChatMessage
          v-for="(m, i) in chat.messages"
          :key="i"
          :message="m"
          :streaming="chat.streaming && i === chat.messages.length - 1 && m.role === 'assistant'"
          @feedback="(v) => chat.sendFeedback(m, v)"
        />

        <p v-if="chat.error" class="chat-error badge badge-error">{{ chat.error }}</p>
      </div>
    </div>

    <div class="chat-foot">
      <div class="chat-inner">
        <ChatInput :disabled="chat.streaming" @send="send" />
      </div>
    </div>
  </AppShell>
</template>

<script setup>
import { computed, ref, watch, nextTick, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth.js'
import { useChatStore } from '@/stores/chat.js'
import AppShell from '@/components/layout/AppShell.vue'
import ChatMessage from '@/components/chat/ChatMessage.vue'
import ChatInput from '@/components/chat/ChatInput.vue'

const route = useRoute()
const auth = useAuthStore()
const chat = useChatStore()
const scroller = ref(null)
const showCtx = ref(false)

const niveaux = ['préscolaire', 'élémentaire', 'moyen', 'secondaire', 'EBJA']
const suggestions = [
  'Comment dériver un quotient de fonctions ?',
  'Fais-moi un cours sur les suites numériques.',
  'Calcule la dérivée de x^3 - 3x.',
]

const headerTitle = computed(() => {
  const cur = chat.conversations.find((c) => c.id === chat.conversationId)
  return cur?.title || 'Nouvelle conversation'
})

function setCtx(key, value) {
  chat.setCurriculum({ [key]: value })
}

async function send(question) {
  await chat.send(question)
}

async function syncFromRoute() {
  const id = route.params.id
  if (id && id !== chat.conversationId) {
    await chat.openConversation(id)
  } else if (!id) {
    chat.newConversation()
  }
}

function scrollToBottom() {
  nextTick(() => {
    const el = scroller.value
    if (el) el.scrollTop = el.scrollHeight
  })
}

onMounted(syncFromRoute)
watch(() => route.params.id, syncFromRoute)
watch(() => [chat.messages.length, chat.messages.at(-1)?.content], scrollToBottom)
</script>

<style scoped>
.chat-header {
  display: flex; align-items: center; justify-content: space-between; gap: 16px;
  padding: 16px 24px; border-bottom: 1px solid var(--border); background: var(--bg-surface);
}
.ch-title h2 { font-size: 17px; }
.ch-title p { font-size: 12.5px; margin-top: 2px; }
.ctx-bar { margin: 12px 24px 0; padding: 14px; display: grid; grid-template-columns: repeat(3, 1fr); gap: 14px; }
.chat-scroll { flex: 1; overflow-y: auto; }
.chat-inner { max-width: 760px; margin: 0 auto; padding: 0 24px; }
.chat-foot { border-top: 1px solid var(--border); background: var(--bg-app); padding: 16px 0 20px; }
.empty { text-align: center; padding: 64px 0 32px; animation: fadeIn 0.4s var(--ease); }
.empty-logo { font-size: 46px; }
.empty h3 { margin: 10px 0 6px; font-size: 20px; }
.suggestions { display: flex; flex-wrap: wrap; gap: 8px; justify-content: center; margin-top: 22px; }
.suggestion { border-style: dashed; }
.chat-error { margin: 8px 0 20px; }
</style>

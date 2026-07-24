import { defineStore } from 'pinia'
import {
  conversationsApi,
  feedbackApi,
  streamChat,
  apiErrorMessage,
} from '@/services/api.js'

const CURRICULUM_KEY = 'tuteur_curriculum'

function loadCurriculum() {
  try {
    return JSON.parse(localStorage.getItem(CURRICULUM_KEY)) || {}
  } catch {
    return {}
  }
}

/** Convertit l'historique persisté (GET .../messages) au format interne. */
function historyToMessages(rows) {
  return rows.map((row) => {
    if (row.role === 'user') return { role: 'user', content: row.content }
    const trace = row.trace || {}
    return {
      role: 'assistant',
      content: row.content,
      trace,
      messageId: row.id,
      generation: trace.generation || null,
      feedback: 0,
    }
  })
}

export const useChatStore = defineStore('chat', {
  state: () => ({
    conversations: [],
    conversationId: null,
    messages: [],
    streaming: false,
    error: '',
    curriculum: { niveau: 'secondaire', serie: 'S1', discipline: 'Mathématiques', ...loadCurriculum() },
    // Renseigné pour un admin qui dialogue au nom d'un élève ; null pour un élève.
    studentId: null,
  }),
  actions: {
    setCurriculum(patch) {
      this.curriculum = { ...this.curriculum, ...patch }
      localStorage.setItem(CURRICULUM_KEY, JSON.stringify(this.curriculum))
    },

    curriculumContext() {
      const ctx = {}
      for (const key of ['niveau', 'serie', 'discipline']) {
        if (this.curriculum[key]) ctx[key] = this.curriculum[key]
      }
      return ctx
    },

    async loadConversations() {
      try {
        const { data } = await conversationsApi.list(this.studentId)
        this.conversations = data
      } catch (e) {
        this.error = apiErrorMessage(e)
      }
    },

    newConversation() {
      this.conversationId = null
      this.messages = []
      this.error = ''
    },

    async openConversation(id) {
      try {
        const { data } = await conversationsApi.messages(id)
        this.conversationId = id
        this.messages = historyToMessages(data)
        this.error = ''
      } catch (e) {
        this.error = apiErrorMessage(e)
      }
    },

    async deleteConversation(id) {
      await conversationsApi.remove(id)
      if (id === this.conversationId) this.newConversation()
      await this.loadConversations()
    },

    async send(question) {
      if (this.streaming || !question.trim()) return
      this.error = ''
      this.messages.push({ role: 'user', content: question })
      const assistant = { role: 'assistant', content: '', trace: null, messageId: null, generation: null, feedback: 0 }
      this.messages.push(assistant)
      this.streaming = true

      try {
        const gen = streamChat({
          question,
          conversationId: this.conversationId,
          curriculumContext: this.curriculumContext(),
          studentId: this.studentId,
        })
        let isNew = !this.conversationId
        for await (const evt of gen) {
          if (evt.meta) {
            assistant.trace = evt.meta
          } else if (evt.token != null) {
            assistant.content += evt.token
          } else if (evt.done) {
            assistant.messageId = evt.done.message_id
            assistant.generation = evt.done.generation
            this.conversationId = evt.done.conversation_id
          } else if (evt.error) {
            this.error = evt.error
          }
        }
        if (isNew) await this.loadConversations()
      } catch (e) {
        if (e.status === 400) {
          this.error = 'Question rejetée (tentative de détournement d’instructions détectée).'
        } else {
          this.error = apiErrorMessage(e, 'Le tuteur est indisponible.')
        }
        // Retire la bulle assistant vide en cas d'échec avant tout token.
        if (!assistant.content) this.messages.pop()
      } finally {
        this.streaming = false
      }
    },

    async sendFeedback(message, value) {
      if (!message.messageId) return
      try {
        await feedbackApi.submit(message.messageId, value)
        message.feedback = value
      } catch (e) {
        this.error = apiErrorMessage(e)
      }
    },
  },
})

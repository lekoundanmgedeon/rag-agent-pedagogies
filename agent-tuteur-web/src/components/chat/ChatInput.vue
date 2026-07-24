<template>
  <form class="chat-input" @submit.prevent="submit">
    <textarea
      ref="ta"
      v-model="text"
      class="input ci-field"
      rows="1"
      :disabled="disabled"
      placeholder="Pose ta question au tuteur…  (Entrée pour envoyer, Maj+Entrée pour un saut de ligne)"
      @keydown.enter.exact.prevent="submit"
      @input="autogrow"
    />
    <button class="btn btn-primary ci-send" type="submit" :disabled="disabled || !text.trim()">
      <span v-if="disabled" class="spinner" />
      <svg v-else width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 2 11 13M22 2l-7 20-4-9-9-4 20-7z" /></svg>
    </button>
  </form>
</template>

<script setup>
import { ref, nextTick } from 'vue'

const props = defineProps({ disabled: { type: Boolean, default: false } })
const emit = defineEmits(['send'])
const text = ref('')
const ta = ref(null)

function autogrow() {
  const el = ta.value
  if (!el) return
  el.style.height = 'auto'
  el.style.height = Math.min(el.scrollHeight, 200) + 'px'
}
async function submit() {
  const value = text.value.trim()
  if (!value || props.disabled) return
  emit('send', value)
  text.value = ''
  await nextTick()
  autogrow()
}
</script>

<style scoped>
.chat-input { display: flex; gap: 10px; align-items: flex-end; }
.ci-field { resize: none; max-height: 200px; line-height: 1.5; padding: 12px 14px; }
.ci-send { flex-shrink: 0; padding: 12px; height: 46px; width: 46px; }
</style>

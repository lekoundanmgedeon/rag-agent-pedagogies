<template>
  <span v-if="course" class="badge badge-accent">
    📚 Cours — Section {{ (course.section_index ?? 0) + 1 }}/{{ total }}
    <template v-if="course.section_title"> · {{ course.section_title }}</template>
  </span>
  <span v-else-if="trace" class="badge badge-accent">
    💡 Indice niveau {{ trace.hint_level }}<template v-if="trace.hint_label"> · {{ trace.hint_label }}</template>
  </span>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({ trace: { type: Object, default: null } })
const course = computed(() => props.trace?.course || null)
const total = computed(() => (course.value?.plan?.length || 1))
</script>

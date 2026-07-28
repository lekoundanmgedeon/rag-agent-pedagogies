<template>
  <div class="shell">
    <AppSidebar />
    <main class="shell-main">
      <slot />
    </main>
  </div>
</template>

<script setup>
import AppSidebar from './AppSidebar.vue'
</script>

<style scoped>
.shell { display: flex; height: 100vh; overflow: hidden; }
.shell-main { flex: 1; min-width: 0; display: flex; flex-direction: column; overflow: hidden; }
</style>

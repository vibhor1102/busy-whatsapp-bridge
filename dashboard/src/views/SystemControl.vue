<template>
  <div class="page-container">
    <h1>System Control</h1>
    <Card>
      <template #content>
        <p>System control features coming soon... (Phase 4)</p>
        
        <div class="process-status">
          <p>Baileys Server: {{ systemStore.isBaileysRunning ? 'Running' : 'Stopped' }}</p>
          <p>Connected: {{ systemStore.isBaileysConnected ? 'Yes' : 'No' }}</p>
        </div>
      </template>
    </Card>
  </div>
</template>

<script setup lang="ts">
import { useSystemStore } from '@/stores/system'
import Card from 'primevue/card'

const systemStore = useSystemStore()
</script>

<style scoped>
.page-container {
  padding: 1.5rem;
}

.process-status {
  margin-top: 1rem;
}

.process-status p {
  margin: 0.5rem 0;
}
</style>

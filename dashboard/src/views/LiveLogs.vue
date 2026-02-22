<template>
  <div class="page-container">
    <h1>Live Logs</h1>
    <Card>
      <template #content>
        <p>Log viewer coming soon... (Phase 4)</p>
        <div class="log-preview">
          <div v-for="log in dashboardStore.latestLogs.slice(-10)" :key="log.id" class="log-line">
            [{{ log.level }}] {{ log.message }}
          </div>
        </div>
      </template>
    </Card>
  </div>
</template>

<script setup lang="ts">
import { useDashboardStore } from '@/stores/dashboard'
import Card from 'primevue/card'

const dashboardStore = useDashboardStore()
</script>

<style scoped>
.page-container {
  padding: 1.5rem;
}

.log-preview {
  margin-top: 1rem;
  padding: 1rem;
  background: var(--surface-ground);
  border-radius: var(--border-radius);
  font-family: monospace;
  font-size: 0.875rem;
}

.log-line {
  margin: 0.25rem 0;
}
</style>

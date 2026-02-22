<template>
  <div class="page-container">
    <h1>Message Queue</h1>
    <Card>
      <template #content>
        <p>Queue management features coming soon... (Phase 3)</p>
        <div class="stats">
          <p>Pending: {{ queueStore.totalPending }}</p>
          <p>Retrying: {{ queueStore.totalRetrying }}</p>
          <p>Dead Letter: {{ queueStore.totalDeadLetter }}</p>
        </div>
      </template>
    </Card>
  </div>
</template>

<script setup lang="ts">
import { useQueueStore } from '@/stores/queue'
import Card from 'primevue/card'

const queueStore = useQueueStore()
</script>

<style scoped>
.page-container {
  padding: 1.5rem;
}

.stats {
  margin-top: 1rem;
}

.stats p {
  margin: 0.5rem 0;
}
</style>

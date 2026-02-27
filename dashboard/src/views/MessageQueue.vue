<template>
  <div class="bw-page">
    <div class="bw-page-header">
      <div>
        <h1>Message Queue</h1>
        <p class="subtitle">Track message delivery and queue status</p>
      </div>
    </div>

    <!-- Stats -->
    <div class="bw-stats-grid">
      <div class="bw-stat-card">
        <div class="bw-stat-icon" style="background: rgba(245,158,11,0.12); color: #f59e0b"><i class="pi pi-clock"></i></div>
        <div class="bw-stat-value">{{ queueStore.totalPending }}</div>
        <div class="bw-stat-label">Pending</div>
      </div>
      <div class="bw-stat-card">
        <div class="bw-stat-icon" style="background: rgba(14,165,233,0.12); color: #0ea5e9"><i class="pi pi-replay"></i></div>
        <div class="bw-stat-value">{{ queueStore.totalRetrying }}</div>
        <div class="bw-stat-label">Retrying</div>
      </div>
      <div class="bw-stat-card">
        <div class="bw-stat-icon" style="background: rgba(239,68,68,0.12); color: #ef4444"><i class="pi pi-exclamation-triangle"></i></div>
        <div class="bw-stat-value">{{ queueStore.totalDeadLetter }}</div>
        <div class="bw-stat-label">Dead Letter</div>
      </div>
      <div class="bw-stat-card">
        <div class="bw-stat-icon" style="background: rgba(34,197,94,0.12); color: #22c55e"><i class="pi pi-check"></i></div>
        <div class="bw-stat-value">{{ queueStore.stats?.sent_today || 0 }}</div>
        <div class="bw-stat-label">Sent Today</div>
      </div>
    </div>

    <!-- Queue info -->
    <div class="bw-section">
      <div class="bw-section-header">
        <h2><i class="pi pi-info-circle"></i> Queue Status</h2>
        <Tag :value="queueStore.stats?.worker_running ? 'Worker Running' : 'Worker Stopped'" :severity="queueStore.stats?.worker_running ? 'success' : 'warning'" />
      </div>
      <div class="bw-section-body">
        <div class="queue-details">
          <div class="queue-detail-row">
            <span class="detail-label">Total Sent</span>
            <span class="detail-value">{{ queueStore.stats?.total_sent || 0 }}</span>
          </div>
          <div class="queue-detail-row">
            <span class="detail-label">Total Failed</span>
            <span class="detail-value" style="color: #ef4444">{{ queueStore.stats?.total_failed || 0 }}</span>
          </div>
          <div class="queue-detail-row">
            <span class="detail-label">Worker Status</span>
            <span class="detail-value">
              <span class="bw-status-dot" :class="queueStore.stats?.worker_running ? 'bw-status-dot--online' : 'bw-status-dot--warning'" style="margin-right: 6px"></span>
              {{ queueStore.stats?.worker_running ? 'Active' : 'Inactive' }}
            </span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useQueueStore } from '@/stores/queue'
import Tag from 'primevue/tag'

const queueStore = useQueueStore()
</script>

<style scoped>
.queue-details {
  display: flex;
  flex-direction: column;
}

.queue-detail-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.75rem 0;
  border-bottom: 1px solid var(--bw-border-subtle);
}

.queue-detail-row:last-child {
  border-bottom: none;
}

.detail-label {
  font-size: 0.82rem;
  color: var(--bw-text-muted);
  font-weight: 500;
}

.detail-value {
  font-weight: 600;
  font-size: 0.875rem;
  display: flex;
  align-items: center;
}
</style>

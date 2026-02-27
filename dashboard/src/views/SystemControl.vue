<template>
  <div class="bw-page">
    <div class="bw-page-header">
      <div>
        <h1>System Control</h1>
        <p class="subtitle">Monitor and manage services</p>
      </div>
      <Button label="Refresh" icon="pi pi-refresh" class="p-button-outlined p-button-sm" :loading="loading" @click="loadStatus" />
    </div>

    <!-- Status + Resources -->
    <div class="system-grid">
      <div class="bw-section">
        <div class="bw-section-header">
          <h2><i class="pi pi-check-circle"></i> Service Status</h2>
        </div>
        <div class="bw-section-body">
          <div class="status-list">
            <div class="status-row">
              <div class="status-left">
                <span class="bw-status-dot" :class="whatsappConnected ? 'bw-status-dot--online' : 'bw-status-dot--offline'"></span>
                <span>WhatsApp Session</span>
              </div>
              <Tag :value="whatsappConnected ? 'Connected' : 'Disconnected'" :severity="whatsappConnected ? 'success' : 'danger'" />
            </div>
            <div class="status-row">
              <div class="status-left">
                <span class="bw-status-dot" :class="queueRunning ? 'bw-status-dot--online' : 'bw-status-dot--warning'"></span>
                <span>Queue Worker</span>
              </div>
              <Tag :value="queueRunning ? 'Running' : 'Stopped'" :severity="queueRunning ? 'success' : 'warning'" />
            </div>
            <div class="status-row">
              <div class="status-left">
                <span class="bw-status-dot" :class="dbConnected ? 'bw-status-dot--online' : 'bw-status-dot--offline'"></span>
                <span>Database</span>
              </div>
              <Tag :value="dbConnected ? 'Connected' : 'Disconnected'" :severity="dbConnected ? 'success' : 'danger'" />
            </div>
          </div>
        </div>
      </div>

      <div class="bw-section">
        <div class="bw-section-header">
          <h2><i class="pi pi-chart-bar"></i> Resources</h2>
        </div>
        <div class="bw-section-body">
          <div class="resource-list">
            <div class="resource-row">
              <span class="resource-label">CPU</span>
              <div class="resource-bar-wrap">
                <ProgressBar :value="resources?.cpu_percent ?? 0" :showValue="false" class="resource-bar" />
              </div>
              <span class="resource-pct">{{ resources?.cpu_percent ?? 0 }}%</span>
            </div>
            <div class="resource-row">
              <span class="resource-label">Memory</span>
              <div class="resource-bar-wrap">
                <ProgressBar :value="resources?.memory?.percent ?? 0" :showValue="false" class="resource-bar" />
              </div>
              <span class="resource-pct">{{ resources?.memory?.percent ?? 0 }}%</span>
            </div>
            <div class="resource-row">
              <span class="resource-label">Disk</span>
              <div class="resource-bar-wrap">
                <ProgressBar :value="resources?.disk?.percent ?? 0" :showValue="false" class="resource-bar" />
              </div>
              <span class="resource-pct">{{ resources?.disk?.percent ?? 0 }}%</span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Actions -->
    <div class="bw-section">
      <div class="bw-section-header">
        <h2><i class="pi pi-bolt"></i> Actions</h2>
      </div>
      <div class="bw-section-body">
        <div class="actions-grid">
          <Button label="Restart Baileys" icon="pi pi-sync" severity="contrast" class="p-button-sm" :loading="actionLoading === 'restart'" @click="restartBaileys" />
          <Button label="Disconnect WhatsApp" icon="pi pi-sign-out" severity="warning" class="p-button-sm" :loading="actionLoading === 'disconnect'" @click="disconnectWhatsApp" />
          <Button label="Clear Session" icon="pi pi-trash" severity="danger" class="p-button-sm" :loading="actionLoading === 'clear'" @click="clearSession" />
          <Button v-if="!queueRunning" label="Start Queue" icon="pi pi-play" severity="success" class="p-button-sm" :loading="actionLoading === 'queue-start'" @click="startQueueWorker" />
          <Button v-else label="Stop Queue" icon="pi pi-stop" severity="secondary" class="p-button-sm" :loading="actionLoading === 'queue-stop'" @click="stopQueueWorker" />
          <Button label="Process Now" icon="pi pi-send" severity="info" class="p-button-sm" :loading="actionLoading === 'queue-process'" @click="processQueueNow" />
        </div>
        <p v-if="message" class="action-message">{{ message }}</p>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { api } from '@/services/api'
import Button from 'primevue/button'
import Tag from 'primevue/tag'
import ProgressBar from 'primevue/progressbar'
import type { DashboardStats, QueueStats, SystemResources } from '@/types'

const loading = ref(false)
const actionLoading = ref('')
const message = ref('')
const stats = ref<DashboardStats | null>(null)
const queueStats = ref<QueueStats | null>(null)
const resources = ref<SystemResources | null>(null)

const whatsappConnected = computed(() => stats.value?.whatsapp?.state === 'connected')
const queueRunning = computed(() => Boolean(queueStats.value?.worker_running))
const dbConnected = computed(() => Boolean(stats.value?.database_connected))

const loadStatus = async () => {
  loading.value = true
  try {
    const [s, q, r] = await Promise.all([api.getDashboardStats(), api.getQueueStats(), api.getSystemResources()])
    stats.value = s; queueStats.value = q; resources.value = r
  } catch { message.value = 'Failed to refresh.' } finally { loading.value = false }
}

const runAction = async (key: string, action: () => Promise<{ message?: string }>) => {
  actionLoading.value = key; message.value = ''
  try {
    const result = await action()
    message.value = result.message || 'Done.'
    await loadStatus()
  } catch (e: any) {
    message.value = e?.message || 'Action failed.'
  } finally { actionLoading.value = '' }
}

const restartBaileys = () => runAction('restart', () => api.restartBaileys())
const disconnectWhatsApp = () => runAction('disconnect', () => api.disconnectWhatsApp())
const clearSession = () => runAction('clear', () => api.clearWhatsAppSession())
const startQueueWorker = () => runAction('queue-start', () => api.startQueueWorker())
const stopQueueWorker = () => runAction('queue-stop', () => api.stopQueueWorker())
const processQueueNow = () => runAction('queue-process', () => api.processQueueNow(25))

onMounted(loadStatus)
</script>

<style scoped>
.system-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: var(--bw-space-lg);
  margin-bottom: var(--bw-space-lg);
}

@media (max-width: 900px) {
  .system-grid { grid-template-columns: 1fr; }
}

/* Status list */
.status-list {
  display: flex;
  flex-direction: column;
}

.status-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0.75rem 0;
  border-bottom: 1px solid var(--bw-border-subtle);
}

.status-row:last-child { border-bottom: none; }

.status-left {
  display: flex;
  align-items: center;
  gap: var(--bw-space-sm);
  font-size: 0.875rem;
  font-weight: 500;
}

/* Resources */
.resource-list {
  display: flex;
  flex-direction: column;
  gap: var(--bw-space-md);
}

.resource-row {
  display: flex;
  align-items: center;
  gap: var(--bw-space-md);
}

.resource-label {
  font-size: 0.82rem;
  color: var(--bw-text-secondary);
  font-weight: 500;
  min-width: 55px;
}

.resource-bar-wrap {
  flex: 1;
}

.resource-bar {
  height: 6px !important;
}

.resource-pct {
  font-size: 0.82rem;
  font-weight: 600;
  color: var(--bw-text-primary);
  min-width: 36px;
  text-align: right;
}

/* Actions */
.actions-grid {
  display: flex;
  flex-wrap: wrap;
  gap: var(--bw-space-sm);
}

.action-message {
  margin-top: var(--bw-space-md);
  font-size: 0.82rem;
  color: var(--bw-text-secondary);
}
</style>

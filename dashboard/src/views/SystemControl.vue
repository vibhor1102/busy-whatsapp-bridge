<template>
  <div class="page-container">
    <div class="page-head">
      <h1>System Control</h1>
      <div class="nav-links">
        <router-link to="/" class="nav-link">Overview</router-link>
        <router-link to="/logs" class="nav-link">Live Logs</router-link>
        <router-link to="/settings" class="nav-link">Settings</router-link>
      </div>
    </div>

    <div class="grid">
      <Card>
        <template #title>Service Status</template>
        <template #content>
          <div class="status-list">
            <div class="status-item">
              <span>WhatsApp Session</span>
              <Tag :value="whatsappConnected ? 'Connected' : 'Disconnected'" :severity="whatsappConnected ? 'success' : 'danger'" />
            </div>
            <div class="status-item">
              <span>Queue Worker</span>
              <Tag :value="queueRunning ? 'Running' : 'Stopped'" :severity="queueRunning ? 'success' : 'warning'" />
            </div>
            <div class="status-item">
              <span>Database</span>
              <Tag :value="dbConnected ? 'Connected' : 'Disconnected'" :severity="dbConnected ? 'success' : 'danger'" />
            </div>
          </div>
        </template>
      </Card>

      <Card>
        <template #title>System Resources</template>
        <template #content>
          <div class="resource-item">
            <span>CPU</span>
            <strong>{{ resources?.cpu_percent ?? 0 }}%</strong>
          </div>
          <div class="resource-item">
            <span>Memory</span>
            <strong>{{ resources?.memory?.percent ?? 0 }}%</strong>
          </div>
          <div class="resource-item">
            <span>Disk</span>
            <strong>{{ resources?.disk?.percent ?? 0 }}%</strong>
          </div>
        </template>
      </Card>
    </div>

    <Card>
      <template #title>Actions</template>
      <template #content>
        <div class="actions">
          <Button label="Refresh Status" icon="pi pi-refresh" :loading="loading" @click="loadStatus" />
          <Button label="Restart Baileys Session" icon="pi pi-sync" severity="contrast" :loading="actionLoading === 'restart'" @click="restartBaileys" />
          <Button label="Disconnect WhatsApp" icon="pi pi-sign-out" severity="warning" :loading="actionLoading === 'disconnect'" @click="disconnectWhatsApp" />
          <Button label="Clear Session" icon="pi pi-trash" severity="danger" :loading="actionLoading === 'clear'" @click="clearSession" />
          <Button v-if="!queueRunning" label="Start Queue Worker" icon="pi pi-play" severity="success" :loading="actionLoading === 'queue-start'" @click="startQueueWorker" />
          <Button v-else label="Stop Queue Worker" icon="pi pi-stop" severity="secondary" :loading="actionLoading === 'queue-stop'" @click="stopQueueWorker" />
          <Button label="Process Queue Now" icon="pi pi-send" severity="info" :loading="actionLoading === 'queue-process'" @click="processQueueNow" />
        </div>
        <p v-if="message" class="message">{{ message }}</p>
      </template>
    </Card>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { api } from '@/services/api'
import Card from 'primevue/card'
import Button from 'primevue/button'
import Tag from 'primevue/tag'
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
    const [statsRes, queueRes, resourceRes] = await Promise.all([
      api.getDashboardStats(),
      api.getQueueStats(),
      api.getSystemResources(),
    ])
    stats.value = statsRes
    queueStats.value = queueRes
    resources.value = resourceRes
  } catch (error) {
    console.error('Failed to load system status', error)
    message.value = 'Failed to refresh system status.'
  } finally {
    loading.value = false
  }
}

const runAction = async (key: string, action: () => Promise<{ message?: string }>) => {
  actionLoading.value = key
  message.value = ''
  try {
    const result = await action()
    message.value = result.message || 'Action completed.'
    await loadStatus()
  } catch (error: any) {
    console.error(error)
    message.value = error?.message || 'Action failed.'
  } finally {
    actionLoading.value = ''
  }
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
.page-container {
  max-width: 1400px;
  margin: 0 auto;
  display: grid;
  gap: 1rem;
}

.page-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
}

.nav-links {
  display: flex;
  gap: 0.5rem;
  flex-wrap: wrap;
}

.nav-link {
  padding: 0.25rem 0.6rem;
  border: 1px solid var(--surface-border);
  border-radius: 999px;
  text-decoration: none;
  color: var(--text-color-secondary);
  font-size: 0.75rem;
}

.grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: 1rem;
}

.status-list,
.resource-item {
  display: grid;
  gap: 0.75rem;
}

.status-item,
.resource-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.actions {
  display: flex;
  flex-wrap: wrap;
  gap: 0.6rem;
}

.message {
  margin-top: 0.8rem;
  color: var(--text-color-secondary);
}
</style>

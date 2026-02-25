<template>
  <div class="overview-page">
    <h1 class="page-title">Dashboard Overview</h1>
    
    <div class="stats-grid">
      <Card class="stat-card">
        <template #title>
          <div class="stat-header">
            <i class="pi pi-send"></i>
            <span>Messages Sent Today</span>
          </div>
        </template>
        <template #content>
          <div class="stat-value">{{ stats?.messages?.sent_today || 0 }}</div>
        </template>
      </Card>
      
      <Card class="stat-card">
        <template #title>
          <div class="stat-header">
            <i class="pi pi-inbox"></i>
            <span>Pending Messages</span>
          </div>
        </template>
        <template #content>
          <div class="stat-value">{{ queueStore.totalPending }}</div>
        </template>
      </Card>
      
      <Card class="stat-card">
        <template #title>
          <div class="stat-header">
            <i class="pi pi-whatsapp"></i>
            <span>WhatsApp Status</span>
          </div>
        </template>
        <template #content>
          <div class="stat-value" :class="whatsappStatusClass">
            {{ whatsappStatusText }}
          </div>
        </template>
      </Card>
      
      <Card class="stat-card">
        <template #title>
          <div class="stat-header">
            <i class="pi pi-database"></i>
            <span>Database</span>
          </div>
        </template>
        <template #content>
          <div class="stat-value" :class="dbStatusClass">
            {{ dbStatusText }}
          </div>
          <small v-if="stats?.database_error" class="db-error">{{ stats.database_error }}</small>
        </template>
      </Card>
    </div>
    
    <div class="dashboard-sections">
      <Card class="activity-card">
        <template #title>Recent Activity</template>
        <template #content>
          <div v-if="recentMessages.length === 0" class="empty-state">
            <i class="pi pi-info-circle"></i>
            <p>No recent activity</p>
          </div>
          <Timeline v-else :value="recentMessages">
            <template #content="slotProps">
              <div class="activity-item">
                <span class="phone">{{ slotProps.item.phone }}</span>
                <span class="status" :class="slotProps.item.status">
                  {{ slotProps.item.status }}
                </span>
                <span class="time">{{ formatTime(slotProps.item.completed_at) }}</span>
              </div>
            </template>
          </Timeline>
        </template>
      </Card>
      
      <Card class="system-card">
        <template #title>System Health</template>
        <template #content>
          <div class="health-item">
            <span>WhatsApp Connection</span>
            <Tag 
              :value="systemStore.isBaileysConnected ? 'Connected' : 'Disconnected'"
              :severity="systemStore.isBaileysConnected ? 'success' : 'danger'"
            />
          </div>
          <div class="health-item">
            <span>Queue Worker</span>
            <Tag 
              :value="queueStore.stats?.worker_running ? 'Running' : 'Stopped'"
              :severity="queueStore.stats?.worker_running ? 'success' : 'warning'"
            />
          </div>
          <div class="health-item">
            <span>Database</span>
            <Tag 
              :value="dbStatusText"
              :severity="dbTagSeverity"
            />
          </div>
        </template>
      </Card>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useDashboardStore } from '@/stores/dashboard'
import { useQueueStore } from '@/stores/queue'
import { useSystemStore } from '@/stores/system'
import { api } from '@/services/api'
import Card from 'primevue/card'
import Timeline from 'primevue/timeline'
import Tag from 'primevue/tag'

const dashboardStore = useDashboardStore()
const queueStore = useQueueStore()
const systemStore = useSystemStore()

const stats = computed(() => dashboardStore.stats)
const recentMessages = ref([])

const whatsappStatusText = computed(() => {
  if (systemStore.isBaileysConnected) return 'Connected'
  if (systemStore.isBaileysRunning) return 'Connecting'
  return 'Disconnected'
})

const whatsappStatusClass = computed(() => ({
  'status-connected': systemStore.isBaileysConnected,
  'status-connecting': systemStore.isBaileysRunning && !systemStore.isBaileysConnected,
  'status-disconnected': !systemStore.isBaileysRunning
}))

const dbStatusText = computed(() => {
  if (!dashboardStore.stats) return 'Checking'
  return dashboardStore.stats.database_connected ? 'Connected' : 'Disconnected'
})

const dbStatusClass = computed(() => ({
  'status-connected': !!dashboardStore.stats?.database_connected,
  'status-disconnected': !!dashboardStore.stats && !dashboardStore.stats.database_connected,
  'status-connecting': !dashboardStore.stats
}))

const dbTagSeverity = computed(() => {
  if (!dashboardStore.stats) return 'warning'
  return dashboardStore.stats.database_connected ? 'success' : 'danger'
})

const formatTime = (timestamp: string) => {
  if (!timestamp) return ''
  return new Date(timestamp).toLocaleTimeString()
}

const loadData = async () => {
  try {
    dashboardStore.setLoading(true)
    const [statsData, activity] = await Promise.all([
      api.getDashboardStats(),
      api.getQueueHistory(undefined, undefined, 5)
    ])
    
    dashboardStore.setStats(statsData)
    queueStore.setStats(statsData.queue)
    systemStore.setBaileysStatus(statsData.whatsapp)
    recentMessages.value = activity
  } catch (error) {
    console.error('Failed to load dashboard data:', error)
  } finally {
    dashboardStore.setLoading(false)
  }
}

onMounted(() => {
  loadData()
  // Refresh every 30 seconds
  setInterval(loadData, 30000)
})
</script>

<style scoped>
.overview-page {
  max-width: 1400px;
  margin: 0 auto;
}

.page-title {
  margin-bottom: 1.5rem;
  font-size: 1.75rem;
  font-weight: 600;
  color: var(--text-color);
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
  gap: 1rem;
  margin-bottom: 1.5rem;
}

.stat-card {
  transition: transform 0.2s ease;
}

.stat-card:hover {
  transform: translateY(-2px);
}

.stat-header {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.875rem;
  color: var(--text-color-secondary);
}

.stat-header i {
  font-size: 1.25rem;
  color: var(--primary-color);
}

.stat-value {
  font-size: 2.5rem;
  font-weight: 700;
  margin-top: 0.5rem;
}

.status-connected {
  color: var(--green-500);
}

.status-connecting {
  color: var(--orange-500);
}

.status-disconnected {
  color: var(--red-500);
}

.db-error {
  display: block;
  margin-top: 0.4rem;
  font-size: 0.75rem;
  color: var(--text-color-secondary);
  white-space: normal;
  word-break: break-word;
}

.dashboard-sections {
  display: grid;
  grid-template-columns: 2fr 1fr;
  gap: 1.5rem;
}

@media (max-width: 1024px) {
  .dashboard-sections {
    grid-template-columns: 1fr;
  }
}

.activity-card,
.system-card {
  min-height: 300px;
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 3rem;
  color: var(--text-color-secondary);
}

.empty-state i {
  font-size: 2rem;
  margin-bottom: 0.5rem;
}

.activity-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0.5rem 0;
  border-bottom: 1px solid var(--surface-border);
}

.activity-item:last-child {
  border-bottom: none;
}

.phone {
  font-weight: 500;
}

.status {
  padding: 0.25rem 0.5rem;
  border-radius: 4px;
  font-size: 0.75rem;
  text-transform: uppercase;
}

.status.sent {
  background: var(--green-500);
  color: white;
}

.status.failed {
  background: var(--red-500);
  color: white;
}

.time {
  font-size: 0.75rem;
  color: var(--text-color-secondary);
}

.health-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 1rem 0;
  border-bottom: 1px solid var(--surface-border);
}

.health-item:last-child {
  border-bottom: none;
}
</style>

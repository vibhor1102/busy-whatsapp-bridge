<template>
  <div class="bw-page">
    <div class="bw-page-header">
      <div>
        <h1>Dashboard</h1>
        <p class="subtitle">System overview and recent activity</p>
      </div>
      <Button
        icon="pi pi-refresh"
        label="Refresh"
        class="p-button-outlined p-button-sm"
        :loading="dashboardStore.isLoading"
        @click="loadData"
      />
    </div>

    <!-- Stats -->
    <div class="bw-stats-grid">
      <div class="bw-stat-card">
        <div class="bw-stat-icon"><i class="pi pi-send"></i></div>
        <div class="bw-stat-value">{{ stats?.messages?.sent_today || 0 }}</div>
        <div class="bw-stat-label">Sent Today</div>
      </div>
      <div class="bw-stat-card">
        <div class="bw-stat-icon" style="background: rgba(245,158,11,0.12); color: #f59e0b"><i class="pi pi-inbox"></i></div>
        <div class="bw-stat-value">{{ queueStore.totalPending }}</div>
        <div class="bw-stat-label">Pending</div>
      </div>
      <div class="bw-stat-card">
        <div class="bw-stat-icon" :style="whatsappIconStyle"><i class="pi pi-whatsapp"></i></div>
        <div class="bw-stat-value" :class="whatsappValueClass">{{ whatsappStatusText }}</div>
        <div class="bw-stat-label">WhatsApp</div>
      </div>
      <div class="bw-stat-card">
        <div class="bw-stat-icon" :style="dbIconStyle"><i class="pi pi-database"></i></div>
        <div class="bw-stat-value" :class="dbValueClass">{{ dbStatusText }}</div>
        <div class="bw-stat-label">Database</div>
        <small v-if="stats?.database_error" class="db-error-text">{{ stats.database_error }}</small>
      </div>
    </div>

    <!-- Content grid -->
    <div class="content-grid">
      <!-- Recent Activity -->
      <div class="bw-section">
        <div class="bw-section-header">
          <h2><i class="pi pi-history"></i> Recent Activity</h2>
        </div>
        <div class="bw-section-body">
          <div v-if="recentMessages.length === 0" class="bw-empty-state">
            <i class="pi pi-info-circle"></i>
            <p>No recent activity</p>
            <small>Messages will appear here once sent</small>
          </div>
          <div v-else class="activity-list">
            <div v-for="msg in recentMessages" :key="msg.id" class="activity-item">
              <div class="activity-left">
                <span class="activity-status-dot" :class="msg.status === 'sent' ? 'dot-success' : 'dot-danger'"></span>
                <span class="activity-phone">{{ msg.phone }}</span>
              </div>
              <div class="activity-right">
                <Tag :value="msg.status" :severity="msg.status === 'sent' ? 'success' : 'danger'" class="activity-tag" />
                <span class="activity-time">{{ formatTime(msg.completed_at) }}</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- System Health -->
      <div class="bw-section">
        <div class="bw-section-header">
          <h2><i class="pi pi-server"></i> System Health</h2>
        </div>
        <div class="bw-section-body">
          <div class="health-list">
            <div class="health-item">
              <div class="health-left">
                <span class="bw-status-dot" :class="systemStore.isBaileysConnected ? 'bw-status-dot--online' : 'bw-status-dot--offline'"></span>
                <span>WhatsApp</span>
              </div>
              <Tag
                :value="systemStore.isBaileysConnected ? 'Connected' : 'Disconnected'"
                :severity="systemStore.isBaileysConnected ? 'success' : 'danger'"
              />
            </div>
            <div class="health-item">
              <div class="health-left">
                <span class="bw-status-dot" :class="queueStore.stats?.worker_running ? 'bw-status-dot--online' : 'bw-status-dot--warning'"></span>
                <span>Queue Worker</span>
              </div>
              <Tag
                :value="queueStore.stats?.worker_running ? 'Running' : 'Stopped'"
                :severity="queueStore.stats?.worker_running ? 'success' : 'warning'"
              />
            </div>
            <div class="health-item">
              <div class="health-left">
                <span class="bw-status-dot" :class="stats?.database_connected ? 'bw-status-dot--online' : 'bw-status-dot--offline'"></span>
                <span>Database</span>
              </div>
              <Tag :value="dbStatusText" :severity="dbTagSeverity" />
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, onBeforeUnmount, ref } from 'vue'
import { useDashboardStore } from '@/stores/dashboard'
import { useQueueStore } from '@/stores/queue'
import { useSystemStore } from '@/stores/system'
import { api } from '@/services/api'
import Button from 'primevue/button'
import Tag from 'primevue/tag'

const dashboardStore = useDashboardStore()
const queueStore = useQueueStore()
const systemStore = useSystemStore()
const stats = computed(() => dashboardStore.stats)
const recentMessages = ref<any[]>([])
let refreshTimer: number | null = null

const whatsappStatusText = computed(() => {
  if (systemStore.isBaileysConnected) return 'Connected'
  if (systemStore.isBaileysRunning) return 'Connecting'
  return 'Offline'
})

const whatsappValueClass = computed(() => ({
  'val-success': systemStore.isBaileysConnected,
  'val-warning': systemStore.isBaileysRunning && !systemStore.isBaileysConnected,
  'val-danger': !systemStore.isBaileysRunning,
}))

const whatsappIconStyle = computed(() =>
  systemStore.isBaileysConnected
    ? 'background: rgba(34,197,94,0.12); color: #22c55e'
    : 'background: rgba(239,68,68,0.12); color: #ef4444'
)

const dbStatusText = computed(() => {
  if (!dashboardStore.stats) return 'Checking'
  return dashboardStore.stats.database_connected ? 'Connected' : 'Offline'
})

const dbValueClass = computed(() => ({
  'val-success': !!dashboardStore.stats?.database_connected,
  'val-danger': !!dashboardStore.stats && !dashboardStore.stats.database_connected,
  'val-warning': !dashboardStore.stats,
}))

const dbIconStyle = computed(() =>
  dashboardStore.stats?.database_connected
    ? 'background: rgba(34,197,94,0.12); color: #22c55e'
    : 'background: rgba(239,68,68,0.12); color: #ef4444'
)

const dbTagSeverity = computed(() => {
  if (!dashboardStore.stats) return 'warning'
  return dashboardStore.stats.database_connected ? 'success' : 'danger'
})

const formatTime = (timestamp: string) => {
  if (!timestamp) return ''
  return new Date(timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
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
  refreshTimer = window.setInterval(loadData, 30000)
})

onBeforeUnmount(() => {
  if (refreshTimer) clearInterval(refreshTimer)
})
</script>

<style scoped>
/* Value colors */
.val-success { color: #22c55e !important; }
.val-warning { color: #f59e0b !important; }
.val-danger { color: #ef4444 !important; }

.db-error-text {
  display: block;
  margin-top: 0.3rem;
  font-size: 0.7rem;
  color: var(--bw-text-muted);
  word-break: break-word;
}

/* Content grid */
.content-grid {
  display: grid;
  grid-template-columns: 1.5fr 1fr;
  gap: var(--bw-space-lg);
}

@media (max-width: 1024px) {
  .content-grid {
    grid-template-columns: 1fr;
  }
}

/* Activity list */
.activity-list {
  display: flex;
  flex-direction: column;
}

.activity-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0.65rem 0;
  border-bottom: 1px solid var(--bw-border-subtle);
}

.activity-item:last-child {
  border-bottom: none;
}

.activity-left {
  display: flex;
  align-items: center;
  gap: var(--bw-space-sm);
}

.activity-status-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  flex-shrink: 0;
}

.dot-success { background: #22c55e; }
.dot-danger { background: #ef4444; }

.activity-phone {
  font-weight: 500;
  font-size: 0.875rem;
}

.activity-right {
  display: flex;
  align-items: center;
  gap: var(--bw-space-sm);
}

.activity-tag {
  font-size: 0.68rem !important;
}

.activity-time {
  font-size: 0.72rem;
  color: var(--bw-text-muted);
  min-width: 50px;
  text-align: right;
}

/* Health list */
.health-list {
  display: flex;
  flex-direction: column;
}

.health-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0.85rem 0;
  border-bottom: 1px solid var(--bw-border-subtle);
}

.health-item:last-child {
  border-bottom: none;
}

.health-left {
  display: flex;
  align-items: center;
  gap: var(--bw-space-sm);
  font-size: 0.875rem;
  font-weight: 500;
}
</style>

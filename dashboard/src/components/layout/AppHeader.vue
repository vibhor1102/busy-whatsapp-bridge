<template>
  <header class="app-header">
    <div class="header-left">
      <button class="mobile-menu-btn" @click="$emit('toggle-sidebar')">
        <i class="pi pi-bars"></i>
      </button>
      <Breadcrumb :model="breadcrumbs" class="header-breadcrumb" />
    </div>

    <div class="header-right">
      <div class="status-pills">
        <div class="status-pill" :class="baileysClass">
          <span class="bw-status-dot" :class="baileysDotClass"></span>
          <span class="status-pill-text">{{ baileysLabel }}</span>
        </div>

        <div class="status-pill" :class="dbClass">
          <span class="bw-status-dot" :class="dbDotClass"></span>
          <span class="status-pill-text">{{ dbLabel }}</span>
        </div>

        <div class="status-pill" v-if="queueStore.totalPending > 0">
          <i class="pi pi-inbox" style="font-size: 0.7rem; color: var(--bw-text-secondary)"></i>
          <span class="status-pill-text">{{ queueStore.totalPending }}</span>
        </div>
      </div>

      <button class="header-icon-btn" :class="{ spinning: dashboardStore.isLoading }" @click="refreshData" title="Refresh">
        <i class="pi pi-refresh"></i>
      </button>
    </div>
  </header>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { useDashboardStore } from '@/stores/dashboard'
import { useSystemStore } from '@/stores/system'
import { useQueueStore } from '@/stores/queue'
import { api } from '@/services/api'
import Breadcrumb from 'primevue/breadcrumb'

const emit = defineEmits<{
  'toggle-sidebar': []
}>()

const route = useRoute()
const dashboardStore = useDashboardStore()
const systemStore = useSystemStore()
const queueStore = useQueueStore()

const breadcrumbs = computed(() => {
  const crumbs = [{ label: 'Dashboard', to: '/' }]
  if (route.name && route.name !== 'Overview') {
    crumbs.push({ label: route.name as string })
  }
  return crumbs
})

// WhatsApp status
const baileysLabel = computed(() => {
  if (systemStore.isBaileysConnected) return 'WhatsApp'
  if (systemStore.isBaileysRunning) return 'Connecting'
  return 'Offline'
})

const baileysClass = computed(() => ({
  'status-pill--success': systemStore.isBaileysConnected,
  'status-pill--warning': systemStore.isBaileysRunning && !systemStore.isBaileysConnected,
  'status-pill--danger': !systemStore.isBaileysRunning,
}))

const baileysDotClass = computed(() =>
  systemStore.isBaileysConnected ? 'bw-status-dot--online' :
  systemStore.isBaileysRunning ? 'bw-status-dot--warning' : 'bw-status-dot--offline'
)

// DB status
const dbLabel = computed(() => {
  if (!dashboardStore.stats) return 'DB'
  return dashboardStore.stats.database_connected ? 'DB' : 'DB Off'
})

const dbClass = computed(() => ({
  'status-pill--success': !!dashboardStore.stats?.database_connected,
  'status-pill--danger': !!dashboardStore.stats && !dashboardStore.stats.database_connected,
  'status-pill--warning': !dashboardStore.stats,
}))

const dbDotClass = computed(() => {
  if (!dashboardStore.stats) return 'bw-status-dot--warning'
  return dashboardStore.stats.database_connected ? 'bw-status-dot--online' : 'bw-status-dot--offline'
})

const refreshData = async () => {
  dashboardStore.setLoading(true)
  try {
    const stats = await api.getDashboardStats()
    dashboardStore.setStats(stats)
    queueStore.setStats(stats.queue)
    systemStore.setBaileysStatus(stats.whatsapp)
  } finally {
    dashboardStore.setLoading(false)
  }
}
</script>

<style scoped>
.app-header {
  height: 56px;
  background: var(--bw-bg-sidebar);
  backdrop-filter: blur(16px);
  border-bottom: 1px solid var(--bw-border-subtle);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 1.25rem;
  position: sticky;
  top: 0;
  z-index: 100;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  min-width: 0;
}

.mobile-menu-btn {
  display: none;
  width: 36px;
  height: 36px;
  border: none;
  background: transparent;
  color: var(--bw-text-secondary);
  cursor: pointer;
  border-radius: var(--bw-radius-sm);
  align-items: center;
  justify-content: center;
  transition: all var(--bw-transition-fast);
}

.mobile-menu-btn:hover {
  background: var(--bw-brand-primary-alpha);
  color: var(--bw-brand-primary-light);
}

.header-breadcrumb {
  background: transparent !important;
  border: none !important;
  padding: 0 !important;
}

.header-breadcrumb :deep(.p-menuitem-text) {
  font-size: 0.85rem;
  font-weight: 500;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

/* Status pills */
.status-pills {
  display: flex;
  align-items: center;
  gap: 0.4rem;
}

.status-pill {
  display: flex;
  align-items: center;
  gap: 0.35rem;
  padding: 0.25rem 0.6rem;
  border-radius: var(--bw-radius-full);
  background: rgba(148, 163, 184, 0.06);
  border: 1px solid var(--bw-border-subtle);
  font-size: 0.72rem;
  transition: all var(--bw-transition-fast);
}

.status-pill-text {
  color: var(--bw-text-secondary);
  font-weight: 500;
  white-space: nowrap;
}

.status-pill--success {
  border-color: rgba(34, 197, 94, 0.2);
}

.status-pill--warning {
  border-color: rgba(245, 158, 11, 0.2);
}

.status-pill--danger {
  border-color: rgba(239, 68, 68, 0.15);
}

/* Header icon button */
.header-icon-btn {
  width: 34px;
  height: 34px;
  border-radius: var(--bw-radius-sm);
  border: none;
  background: transparent;
  color: var(--bw-text-muted);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all var(--bw-transition-fast);
}

.header-icon-btn:hover {
  background: var(--bw-brand-primary-alpha);
  color: var(--bw-brand-primary-light);
}

.header-icon-btn.spinning i {
  animation: spin 1s linear infinite;
}

@media (max-width: 1024px) {
  .mobile-menu-btn {
    display: flex;
  }

  .status-pills {
    display: none;
  }
}
</style>

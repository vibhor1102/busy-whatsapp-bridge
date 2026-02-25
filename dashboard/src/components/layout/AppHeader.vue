<template>
  <header class="app-header">
    <div class="header-left">
      <Button 
        icon="pi pi-bars" 
        class="p-button-text p-button-rounded"
        @click="$emit('toggle-sidebar')"
      />
      <Breadcrumb :model="breadcrumbs" class="header-breadcrumb" />
      <div class="quick-links">
        <router-link to="/" class="quick-link">Overview</router-link>
        <router-link to="/whatsapp" class="quick-link">WhatsApp</router-link>
        <router-link to="/queue" class="quick-link">Queue</router-link>
        <router-link to="/reminders" class="quick-link">Reminders</router-link>
        <router-link to="/logs" class="quick-link">Logs</router-link>
        <router-link to="/system" class="quick-link">System</router-link>
        <router-link to="/settings" class="quick-link">Settings</router-link>
      </div>
    </div>
    
    <div class="header-right">
      <div class="status-indicators">
        <Tag 
          :value="baileysStatus" 
          :severity="baileysSeverity"
          icon="pi pi-whatsapp"
          class="status-tag"
        />
        
        <Tag 
          :value="dbStatus" 
          :severity="dbSeverity"
          icon="pi pi-database"
          class="status-tag"
        />
        
        <Tag 
          :value="queueStatus" 
          :severity="queueSeverity"
          icon="pi pi-inbox"
          class="status-tag"
        />
      </div>
      
      <Button 
        icon="pi pi-refresh" 
        class="p-button-text p-button-rounded"
        :loading="dashboardStore.isLoading"
        @click="refreshData"
        tooltip="Refresh Data"
      />
      
      <Button 
        icon="pi pi-moon" 
        class="p-button-text p-button-rounded"
        @click="toggleTheme"
      />
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
import Button from 'primevue/button'
import Breadcrumb from 'primevue/breadcrumb'
import Tag from 'primevue/tag'

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

const baileysStatus = computed(() => {
  if (systemStore.isBaileysConnected) return 'WhatsApp Connected'
  if (systemStore.isBaileysRunning) return 'WhatsApp Connecting'
  return 'WhatsApp Disconnected'
})

const baileysSeverity = computed(() => {
  if (systemStore.isBaileysConnected) return 'success'
  if (systemStore.isBaileysRunning) return 'warning'
  return 'danger'
})

const dbStatus = computed(() => {
  if (!dashboardStore.stats) return 'DB Checking'
  return dashboardStore.stats.database_connected ? 'DB Connected' : 'DB Disconnected'
})

const dbSeverity = computed(() => {
  if (!dashboardStore.stats) return 'warning'
  return dashboardStore.stats.database_connected ? 'success' : 'danger'
})

const queueStatus = computed(() => {
  const pending = queueStore.totalPending
  if (pending > 10) return `${pending} Pending`
  if (pending > 0) return `${pending} Pending`
  return 'Queue Empty'
})

const queueSeverity = computed(() => {
  const pending = queueStore.totalPending
  if (pending > 10) return 'danger'
  if (pending > 0) return 'warning'
  return 'success'
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

const toggleTheme = () => {
  const element = document.querySelector('html')
  element?.classList.toggle('dark-theme')
}
</script>

<style scoped>
.app-header {
  height: 60px;
  background-color: var(--surface-card);
  border-bottom: 1px solid var(--surface-border);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 1rem;
  position: sticky;
  top: 0;
  z-index: 100;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 1rem;
  min-width: 0;
}

.header-breadcrumb {
  background: transparent;
  border: none;
  padding: 0;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.quick-links {
  display: flex;
  gap: 0.5rem;
  margin-left: 0.5rem;
  overflow-x: auto;
}

.quick-link {
  padding: 0.25rem 0.6rem;
  border: 1px solid var(--surface-border);
  border-radius: 999px;
  text-decoration: none;
  color: var(--text-color-secondary);
  font-size: 0.75rem;
  white-space: nowrap;
}

.quick-link.router-link-active {
  color: var(--primary-color);
  border-color: var(--primary-color);
  background: color-mix(in srgb, var(--primary-color) 8%, transparent);
}

.status-indicators {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-right: 1rem;
}

.status-tag {
  font-size: 0.75rem;
}

.status-tag :deep(.p-tag-icon) {
  font-size: 0.75rem;
}

@media (max-width: 1024px) {
  .status-indicators {
    display: none;
  }

  .quick-links {
    display: none;
  }
}
</style>

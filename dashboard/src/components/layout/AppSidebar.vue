<template>
  <aside class="sidebar" :class="{ collapsed: collapsed, 'mobile-open': mobileOpen }">
    <div class="sidebar-header">
      <div class="logo">
        <i class="pi pi-whatsapp"></i>
        <span v-if="!collapsed" class="logo-text">Busy Gateway</span>
      </div>
      <Button 
        icon="pi pi-bars" 
        class="p-button-text p-button-rounded toggle-btn"
        @click="$emit('toggle')"
      />
    </div>
    
    <nav class="sidebar-nav">
      <router-link
        v-for="route in routes"
        :key="route.path"
        :to="route.path"
        class="nav-item"
        :class="{ active: isActiveRoute(route.path) }"
        @click="$emit('navigate')"
      >
        <i :class="route.meta?.icon"></i>
        <span v-if="!collapsed" class="nav-text">{{ route.meta?.title }}</span>
        <Badge 
          v-if="route.name === 'Message Queue' && queueStore.totalPending > 0 && !collapsed"
          :value="queueStore.totalPending.toString()"
          severity="danger"
          class="nav-badge"
        />
      </router-link>
    </nav>
    
    <div class="sidebar-footer">
      <div class="connection-status" :class="{ connected: dashboardStore.isConnected }">
        <i class="pi pi-circle-fill"></i>
        <span v-if="!collapsed">{{ dashboardStore.isConnected ? 'Connected' : 'Disconnected' }}</span>
      </div>
      <div v-if="!collapsed" class="version">
        v{{ stats?.system?.version || '0.0.1' }}
      </div>
    </div>
  </aside>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { useDashboardStore } from '@/stores/dashboard'
import { useQueueStore } from '@/stores/queue'
import Button from 'primevue/button'
import Badge from 'primevue/badge'
import { navRoutes } from '@/router'

const props = defineProps<{
  collapsed: boolean
  mobileOpen: boolean
}>()

defineEmits<{
  toggle: []
  navigate: []
}>()

const route = useRoute()
const dashboardStore = useDashboardStore()
const queueStore = useQueueStore()
const routes = navRoutes

const isActiveRoute = (path: string) => route.path === path

const stats = computed(() => dashboardStore.stats)
</script>

<style scoped>
.sidebar {
  width: 260px;
  height: 100vh;
  background-color: var(--surface-card);
  border-right: 1px solid var(--surface-border);
  display: flex;
  flex-direction: column;
  position: fixed;
  left: 0;
  top: 0;
  z-index: 1000;
  transition: width 0.3s ease;
}

.sidebar.collapsed {
  width: 70px;
}

.sidebar-header {
  padding: 1rem;
  display: flex;
  align-items: center;
  justify-content: space-between;
  border-bottom: 1px solid var(--surface-border);
}

.logo {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  color: var(--primary-color);
  font-size: 1.25rem;
  font-weight: 600;
}

.logo i {
  font-size: 1.5rem;
}

.toggle-btn {
  color: var(--text-color-secondary);
}

.sidebar-nav {
  flex: 1;
  padding: 1rem 0.75rem;
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
  overflow-y: auto;
}

.nav-item {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.75rem 1rem;
  color: var(--text-color-secondary);
  text-decoration: none;
  border-radius: var(--border-radius);
  transition: all 0.2s ease;
  position: relative;
}

.nav-item:hover {
  background-color: var(--surface-hover);
  color: var(--text-color);
}

.nav-item.active {
  background-color: var(--primary-color);
  color: var(--primary-color-text);
}

.nav-item i {
  font-size: 1.25rem;
  width: 1.5rem;
  text-align: center;
}

.nav-text {
  flex: 1;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.nav-badge {
  margin-left: auto;
}

.sidebar-footer {
  padding: 1rem;
  border-top: 1px solid var(--surface-border);
  font-size: 0.875rem;
}

.connection-status {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  color: var(--red-500);
  margin-bottom: 0.5rem;
}

.connection-status.connected {
  color: var(--green-500);
}

.connection-status i {
  font-size: 0.5rem;
}

.version {
  color: var(--text-color-secondary);
  font-size: 0.75rem;
}

@media (max-width: 1024px) {
  .sidebar {
    transform: translateX(-100%);
    transition: transform 0.25s ease;
    width: 260px;
  }

  .sidebar.mobile-open {
    transform: translateX(0);
  }

  .sidebar.collapsed {
    width: 260px;
  }
}
</style>

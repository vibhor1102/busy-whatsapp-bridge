<template>
  <aside class="sidebar" :class="{ collapsed: collapsed, 'mobile-open': mobileOpen }">
    <div class="sidebar-header">
      <div class="logo">
        <div class="logo-icon">
          <i class="pi pi-whatsapp"></i>
        </div>
        <transition name="logo-fade">
          <span v-if="!collapsed" class="logo-text">Busy Gateway</span>
        </transition>
      </div>
      <button class="toggle-btn" @click="$emit('toggle')" :title="collapsed ? 'Expand' : 'Collapse'">
        <i :class="collapsed ? 'pi pi-angle-right' : 'pi pi-angle-left'"></i>
      </button>
    </div>

    <nav class="sidebar-nav">
      <router-link
        v-for="route in routes"
        :key="route.path"
        :to="route.path"
        class="nav-item"
        :class="{ active: isActiveRoute(route.path) }"
        @click="$emit('navigate')"
        :title="collapsed ? route.meta?.title : undefined"
      >
        <div class="nav-icon-wrap">
          <i :class="route.meta?.icon"></i>
        </div>
        <transition name="text-fade">
          <span v-if="!collapsed" class="nav-text">{{ route.meta?.title }}</span>
        </transition>
        <Badge
          v-if="route.name === 'Message Queue' && queueStore.totalPending > 0 && !collapsed"
          :value="queueStore.totalPending.toString()"
          severity="danger"
          class="nav-badge"
        />
      </router-link>
    </nav>

    <div class="sidebar-footer">
      <div class="connection-indicator">
        <span class="bw-status-dot" :class="dashboardStore.isConnected ? 'bw-status-dot--online' : 'bw-status-dot--offline'"></span>
        <transition name="text-fade">
          <span v-if="!collapsed" class="connection-text">{{ dashboardStore.isConnected ? 'Live' : 'Offline' }}</span>
        </transition>
      </div>
      <transition name="text-fade">
        <div v-if="!collapsed" class="version-badge">
          v{{ stats?.system?.version || '0.0.1' }}
        </div>
      </transition>
    </div>
  </aside>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { useDashboardStore } from '@/stores/dashboard'
import { useQueueStore } from '@/stores/queue'
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
  background: var(--bw-bg-sidebar);
  backdrop-filter: blur(16px);
  border-right: 1px solid var(--bw-border-subtle);
  display: flex;
  flex-direction: column;
  position: fixed;
  left: 0;
  top: 0;
  z-index: 1000;
  transition: width var(--bw-transition-slow);
}

.sidebar.collapsed {
  width: 72px;
}

/* Header */
.sidebar-header {
  padding: 1rem;
  display: flex;
  align-items: center;
  justify-content: space-between;
  border-bottom: 1px solid var(--bw-border-subtle);
  min-height: 64px;
}

.logo {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  min-width: 0;
  overflow: hidden;
}

.logo-icon {
  width: 36px;
  height: 36px;
  border-radius: var(--bw-radius-md);
  background: var(--bw-gradient-primary);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1.15rem;
  color: white;
  flex-shrink: 0;
  box-shadow: 0 2px 8px rgba(20, 184, 166, 0.3);
}

.logo-text {
  font-size: 1.05rem;
  font-weight: 700;
  color: var(--bw-text-primary);
  white-space: nowrap;
  letter-spacing: -0.01em;
}

.toggle-btn {
  width: 30px;
  height: 30px;
  border-radius: var(--bw-radius-sm);
  border: none;
  background: transparent;
  color: var(--bw-text-muted);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all var(--bw-transition-fast);
  flex-shrink: 0;
}

.toggle-btn:hover {
  background: var(--bw-brand-primary-alpha);
  color: var(--bw-brand-primary-light);
}

/* Navigation */
.sidebar-nav {
  flex: 1;
  padding: 0.75rem;
  display: flex;
  flex-direction: column;
  gap: 2px;
  overflow-y: auto;
  overflow-x: hidden;
}

.nav-item {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.65rem 0.75rem;
  color: var(--bw-text-secondary);
  text-decoration: none;
  border-radius: var(--bw-radius-md);
  transition: all var(--bw-transition-fast);
  position: relative;
  min-height: 42px;
}

.nav-item:hover {
  background: rgba(148, 163, 184, 0.06);
  color: var(--bw-text-primary);
}

.nav-item.active {
  background: var(--bw-brand-primary-alpha);
  color: var(--bw-brand-primary-light);
}

.nav-item.active::before {
  content: '';
  position: absolute;
  left: 0;
  top: 50%;
  transform: translateY(-50%);
  width: 3px;
  height: 60%;
  border-radius: 0 3px 3px 0;
  background: var(--bw-gradient-primary);
  box-shadow: 0 0 8px rgba(20, 184, 166, 0.4);
}

.nav-icon-wrap {
  width: 22px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.nav-icon-wrap i {
  font-size: 1.1rem;
}

.nav-text {
  flex: 1;
  font-size: 0.875rem;
  font-weight: 500;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.nav-badge {
  margin-left: auto;
  flex-shrink: 0;
}

/* Footer */
.sidebar-footer {
  padding: 0.85rem 1rem;
  border-top: 1px solid var(--bw-border-subtle);
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.5rem;
}

.connection-indicator {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.connection-text {
  font-size: 0.75rem;
  font-weight: 500;
  color: var(--bw-text-secondary);
}

.version-badge {
  font-size: 0.68rem;
  font-weight: 500;
  color: var(--bw-text-muted);
  background: rgba(148, 163, 184, 0.08);
  padding: 0.15rem 0.5rem;
  border-radius: var(--bw-radius-full);
}

/* Transitions for text */
.text-fade-enter-active,
.text-fade-leave-active {
  transition: opacity 0.2s ease, transform 0.2s ease;
}
.text-fade-enter-from,
.text-fade-leave-to {
  opacity: 0;
  transform: translateX(-8px);
}

.logo-fade-enter-active,
.logo-fade-leave-active {
  transition: opacity 0.15s ease;
}
.logo-fade-enter-from,
.logo-fade-leave-to {
  opacity: 0;
}

/* Mobile */
@media (max-width: 1024px) {
  .sidebar {
    transform: translateX(-100%);
    transition: transform 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    width: 260px;
  }

  .sidebar.mobile-open {
    transform: translateX(0);
    box-shadow: var(--bw-shadow-lg);
  }

  .sidebar.collapsed {
    width: 260px;
  }
}
</style>

<template>
  <div class="app-container">
    <AppSidebar
      :collapsed="sidebarCollapsed"
      :mobile-open="mobileSidebarOpen"
      @toggle="toggleSidebar"
      @navigate="closeMobileSidebar"
    />
    <div
      v-if="mobileSidebarOpen"
      class="sidebar-overlay"
      @click="closeMobileSidebar"
    />
    <div class="main-content" :class="{ 'sidebar-collapsed': sidebarCollapsed, 'mobile': isMobile }">
      <AppHeader @toggle-sidebar="toggleSidebar" />
      <main class="content-area">
        <router-view v-slot="{ Component }">
          <transition name="page" mode="out-in">
            <component :is="Component" />
          </transition>
        </router-view>
      </main>
    </div>
    <Toast position="bottom-right" />
    <ConfirmDialog />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount } from 'vue'
import { useWebSocket } from '@/composables/useWebSocket'
import AppSidebar from '@/components/layout/AppSidebar.vue'
import AppHeader from '@/components/layout/AppHeader.vue'
import Toast from 'primevue/toast'
import ConfirmDialog from 'primevue/confirmdialog'

const sidebarCollapsed = ref(false)
const mobileSidebarOpen = ref(false)
const isMobile = ref(false)

const toggleSidebar = () => {
  if (isMobile.value) {
    mobileSidebarOpen.value = !mobileSidebarOpen.value
    return
  }
  sidebarCollapsed.value = !sidebarCollapsed.value
  localStorage.setItem('sidebar-collapsed', String(sidebarCollapsed.value))
}

const closeMobileSidebar = () => {
  mobileSidebarOpen.value = false
}

const handleResize = () => {
  isMobile.value = window.innerWidth <= 1024
  if (!isMobile.value) {
    mobileSidebarOpen.value = false
  }
}

// Initialize WebSocket connection
useWebSocket()

onMounted(() => {
  handleResize()
  window.addEventListener('resize', handleResize)

  // Check for saved sidebar state
  const saved = localStorage.getItem('sidebar-collapsed')
  if (saved) {
    sidebarCollapsed.value = saved === 'true'
  }
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', handleResize)
})
</script>

<style scoped>
.app-container {
  display: flex;
  min-height: 100vh;
  background: var(--bw-bg-page);
}

.main-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  margin-left: 260px;
  transition: margin-left var(--bw-transition-slow);
  min-height: 100vh;
}

.main-content.sidebar-collapsed {
  margin-left: 72px;
}

.content-area {
  flex: 1;
  padding: 1.5rem;
  overflow-y: auto;
}

/* Page transitions */
.page-enter-active {
  transition: opacity 0.25s ease, transform 0.25s ease;
}
.page-leave-active {
  transition: opacity 0.15s ease;
}

.page-enter-from {
  opacity: 0;
  transform: translateY(8px);
}
.page-leave-to {
  opacity: 0;
}

.sidebar-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.5);
  backdrop-filter: blur(2px);
  z-index: 900;
  animation: fadeIn 0.2s ease;
}

@media (max-width: 1024px) {
  .main-content {
    margin-left: 0;
  }

  .main-content.sidebar-collapsed {
    margin-left: 0;
  }
}
</style>

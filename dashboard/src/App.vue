<template>
  <div class="app-container">
    <AppSidebar :collapsed="sidebarCollapsed" @toggle="toggleSidebar" />
    <div class="main-content" :class="{ 'sidebar-collapsed': sidebarCollapsed }">
      <AppHeader @toggle-sidebar="toggleSidebar" />
      <main class="content-area">
        <router-view v-slot="{ Component }">
          <transition name="fade" mode="out-in">
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
import { ref, onMounted } from 'vue'
import { useWebSocket } from '@/composables/useWebSocket'
import AppSidebar from '@/components/layout/AppSidebar.vue'
import AppHeader from '@/components/layout/AppHeader.vue'
import Toast from 'primevue/toast'
import ConfirmDialog from 'primevue/confirmdialog'

const sidebarCollapsed = ref(false)

const toggleSidebar = () => {
  sidebarCollapsed.value = !sidebarCollapsed.value
}

// Initialize WebSocket connection
useWebSocket()

onMounted(() => {
  // Check for saved sidebar state
  const saved = localStorage.getItem('sidebar-collapsed')
  if (saved) {
    sidebarCollapsed.value = saved === 'true'
  }
})
</script>

<style scoped>
.app-container {
  display: flex;
  min-height: 100vh;
  background-color: var(--surface-ground);
}

.main-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  margin-left: 260px;
  transition: margin-left 0.3s ease;
}

.main-content.sidebar-collapsed {
  margin-left: 70px;
}

.content-area {
  flex: 1;
  padding: 1.5rem;
  overflow-y: auto;
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>

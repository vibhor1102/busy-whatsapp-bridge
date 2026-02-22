import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { DashboardStats, LogEntry, WebSocketMessage } from '@/types'

export const useDashboardStore = defineStore('dashboard', () => {
  // State
  const stats = ref<DashboardStats | null>(null)
  const logs = ref<LogEntry[]>([])
  const isConnected = ref(false)
  const isLoading = ref(false)
  const error = ref<string | null>(null)

  // Getters
  const hasError = computed(() => error.value !== null)
  const latestLogs = computed(() => logs.value.slice(-100))

  // Actions
  function setStats(newStats: DashboardStats) {
    stats.value = newStats
  }

  function addLog(log: LogEntry) {
    logs.value.push(log)
    // Keep only last 1000 logs
    if (logs.value.length > 1000) {
      logs.value = logs.value.slice(-1000)
    }
  }

  function setConnectionStatus(connected: boolean) {
    isConnected.value = connected
  }

  function setLoading(loading: boolean) {
    isLoading.value = loading
  }

  function setError(err: string | null) {
    error.value = err
  }

  function clearLogs() {
    logs.value = []
  }

  return {
    stats,
    logs,
    isConnected,
    isLoading,
    error,
    hasError,
    latestLogs,
    setStats,
    addLog,
    setConnectionStatus,
    setLoading,
    setError,
    clearLogs
  }
})

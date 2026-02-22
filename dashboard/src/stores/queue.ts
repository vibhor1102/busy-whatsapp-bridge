import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { QueueStats, Message } from '@/types'

export const useQueueStore = defineStore('queue', () => {
  // State
  const stats = ref<QueueStats | null>(null)
  const pending = ref<Message[]>([])
  const retrying = ref<Message[]>([])
  const deadLetter = ref<Message[]>([])
  const history = ref<Message[]>([])
  const selectedTab = ref('pending')
  const isLoading = ref(false)

  // Getters
  const totalPending = computed(() => stats.value?.pending || 0)
  const totalRetrying = computed(() => stats.value?.retrying || 0)
  const totalDeadLetter = computed(() => stats.value?.dead_letter || 0)
  const totalSent = computed(() => stats.value?.total_sent || 0)

  // Actions
  function setStats(newStats: QueueStats) {
    stats.value = newStats
  }

  function setPending(messages: Message[]) {
    pending.value = messages
  }

  function setRetrying(messages: Message[]) {
    retrying.value = messages
  }

  function setDeadLetter(messages: Message[]) {
    deadLetter.value = messages
  }

  function setHistory(messages: Message[]) {
    history.value = messages
  }

  function setSelectedTab(tab: string) {
    selectedTab.value = tab
  }

  function setLoading(loading: boolean) {
    isLoading.value = loading
  }

  function updateMessage(message: Message) {
    // Update in appropriate list based on status
    const lists = {
      pending: pending,
      retrying: retrying,
      dead_letter: deadLetter
    }
    
    Object.entries(lists).forEach(([status, list]) => {
      const index = list.value.findIndex(m => m.id === message.id)
      if (index !== -1) {
        if (message.status === status) {
          list.value[index] = message
        } else {
          list.value.splice(index, 1)
        }
      } else if (message.status === status) {
        list.value.unshift(message)
      }
    })
  }

  return {
    stats,
    pending,
    retrying,
    deadLetter,
    history,
    selectedTab,
    isLoading,
    totalPending,
    totalRetrying,
    totalDeadLetter,
    totalSent,
    setStats,
    setPending,
    setRetrying,
    setDeadLetter,
    setHistory,
    setSelectedTab,
    setLoading,
    updateMessage
  }
})

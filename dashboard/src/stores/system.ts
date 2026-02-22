import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { BaileysStatus, ProcessStatus, SystemResources } from '@/types'

export const useSystemStore = defineStore('system', () => {
  // State
  const baileysStatus = ref<BaileysStatus | null>(null)
  const processes = ref<ProcessStatus[]>([])
  const resources = ref<SystemResources | null>(null)
  const isLoading = ref(false)

  // Getters
  const isBaileysConnected = computed(() => 
    baileysStatus.value?.state === 'connected'
  )
  
  const isBaileysRunning = computed(() =>
    processes.value.some(p => p.name === 'baileys' && p.running)
  )

  // Actions
  function setBaileysStatus(status: BaileysStatus) {
    baileysStatus.value = status
  }

  function setProcesses(procs: ProcessStatus[]) {
    processes.value = procs
  }

  function setResources(res: SystemResources) {
    resources.value = res
  }

  function setLoading(loading: boolean) {
    isLoading.value = loading
  }

  return {
    baileysStatus,
    processes,
    resources,
    isLoading,
    isBaileysConnected,
    isBaileysRunning,
    setBaileysStatus,
    setProcesses,
    setResources,
    setLoading
  }
})

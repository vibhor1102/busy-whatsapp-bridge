import { ref, onMounted, onUnmounted } from 'vue'
import { useDashboardStore } from '@/stores/dashboard'
import { useQueueStore } from '@/stores/queue'
import { useSystemStore } from '@/stores/system'
import type { WebSocketMessage } from '@/types'

export function useWebSocket() {
  const ws = ref<WebSocket | null>(null)
  const isConnected = ref(false)
  const reconnectAttempts = ref(0)
  const maxReconnectAttempts = 5
  
  const dashboardStore = useDashboardStore()
  const queueStore = useQueueStore()
  const systemStore = useSystemStore()

  const connect = () => {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const wsUrl = `${protocol}//${window.location.host}/ws/dashboard`
    
    ws.value = new WebSocket(wsUrl)
    
    ws.value.onopen = () => {
      isConnected.value = true
      reconnectAttempts.value = 0
      dashboardStore.setConnectionStatus(true)
      console.log('WebSocket connected')
    }
    
    ws.value.onmessage = (event) => {
      try {
        const message: WebSocketMessage = JSON.parse(event.data)
        handleMessage(message)
      } catch (error) {
        console.error('Failed to parse WebSocket message:', error)
      }
    }
    
    ws.value.onclose = () => {
      isConnected.value = false
      dashboardStore.setConnectionStatus(false)
      console.log('WebSocket disconnected')
      
      // Attempt to reconnect
      if (reconnectAttempts.value < maxReconnectAttempts) {
        reconnectAttempts.value++
        setTimeout(connect, 3000 * reconnectAttempts.value)
      }
    }
    
    ws.value.onerror = (error) => {
      console.error('WebSocket error:', error)
    }
  }
  
  const handleMessage = (message: WebSocketMessage) => {
    switch (message.type) {
      case 'queue_update':
        queueStore.setStats(message.data)
        break
      case 'baileys_status':
        systemStore.setBaileysStatus(message.data)
        break
      case 'new_log':
        dashboardStore.addLog(message.data)
        break
      case 'message_sent':
      case 'message_failed':
        // Trigger queue refresh
        break
      case 'system_alert':
        // Show toast notification
        break
      default:
        console.log('Unknown message type:', message.type)
    }
  }
  
  const send = (data: any) => {
    if (ws.value?.readyState === WebSocket.OPEN) {
      ws.value.send(JSON.stringify(data))
    }
  }
  
  const disconnect = () => {
    if (ws.value) {
      ws.value.close()
    }
  }
  
  onMounted(() => {
    connect()
  })
  
  onUnmounted(() => {
    disconnect()
  })
  
  return {
    isConnected,
    connect,
    disconnect,
    send
  }
}

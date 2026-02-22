export interface QueueStats {
  pending: number
  retrying: number
  dead_letter: number
  sent_today: number
  total_sent: number
  total_failed: number
  worker_running: boolean
}

export interface Message {
  id: number
  phone: string
  message: string
  pdf_url?: string
  provider: string
  status: 'pending' | 'retrying' | 'sent' | 'failed'
  retry_count: number
  max_retries: number
  next_retry_at?: string
  error_message?: string
  created_at: string
  updated_at: string
  sent_at?: string
  message_id?: string
  source: string
}

export interface BaileysStatus {
  state: 'connected' | 'qr_ready' | 'disconnected' | 'reconnecting' | 'unreachable'
  user?: {
    id: string
    name: string
    phone: string
  }
  qr_image?: string
  error?: string
}

export interface SystemStats {
  uptime: number
  version: string
  start_time: string
}

export interface DashboardStats {
  system: SystemStats
  queue: QueueStats
  whatsapp: BaileysStatus
  messages: {
    sent_today: number
    sent_this_week: number
    failed_today: number
  }
}

export interface LogEntry {
  id: string
  timestamp: string
  level: 'DEBUG' | 'INFO' | 'WARNING' | 'ERROR'
  logger: string
  message: string
  source?: string
}

export interface ProcessStatus {
  name: string
  running: boolean
  pid?: number
  started?: string
  port?: number
}

export interface SystemResources {
  cpu_percent: number
  memory: {
    total: number
    available: number
    percent: number
    used: number
  }
  disk: {
    total: number
    used: number
    free: number
    percent: number
  }
}

export interface WebSocketMessage {
  type: string
  timestamp: string
  data: any
}

export type Theme = 'dark' | 'light'

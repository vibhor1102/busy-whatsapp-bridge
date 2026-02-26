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
  completed_at?: string
  sent_at?: string
  message_id?: string
  delivery_status?: 'accepted' | 'sent' | 'delivered' | 'read' | 'failed' | 'unknown'
  delivery_updated_at?: string
  delivered_at?: string
  read_at?: string
  failed_at?: string
  recipient_waid?: string
  source: string
}

export interface BaileysStatus {
  state: 'connected' | 'qr_ready' | 'disconnected' | 'connecting' | 'reconnecting' | 'logged_out' | 'unreachable'
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
  database_connected: boolean
  database_error?: string | null
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

// Payment Reminder Types
export interface PartyReminderInfo {
  code: string
  name: string
  print_name?: string
  phone?: string
  address?: string
  closing_balance: number
  closing_balance_formatted: string
  amount_due: number
  amount_due_formatted: string
  sales_credit_days: number
  purchase_credit_days?: number
  credit_days_source: string
  permanent_enabled: boolean
  temp_enabled: boolean
  last_reminder_sent?: string
  reminder_count: number
  can_generate_ledger: boolean
}

export interface ScheduleConfig {
  enabled: boolean
  frequency: 'weekly' | 'biweekly'
  day_of_week: number
  time: string
  timezone: string
  batch_size: number
  delay_between_messages: number
}

export interface MessageTemplate {
  id: string
  name: string
  description?: string
  content: string
  variables: string[]
  is_default: boolean
  created_at: string
  updated_at: string
}

export interface PartyConfig {
  enabled: boolean
  credit_days_override?: number
  custom_template_id?: string
  custom_message?: string
  notes?: string
}

export interface ReminderConfig {
  version: string
  last_updated: string
  default_credit_days: number
  default_provider: string
  currency_symbol: string
  company?: {
    name: string
    contact_phone: string
    address?: string
  }
  schedule: ScheduleConfig
  parties: Record<string, PartyConfig>
  templates: MessageTemplate[]
  active_template_id: string
}

export interface ReminderStats {
  total_parties: number
  eligible_parties: number
  enabled_parties: number
  reminders_sent_today: number
  reminders_sent_this_week: number
  reminders_sent_this_month: number
  total_amount_due: number
  average_amount_due: number
  last_scheduler_run?: string
  next_scheduler_run?: string
  scheduler_status: 'running' | 'stopped' | 'paused'
}

export interface ReminderSnapshotStatus {
  has_snapshot: boolean
  last_refreshed_at?: string
  duration_ms: number
  row_count: number
  nonzero_count: number
  error_count: number
  source_db_path_hash?: string
}

export interface MetaWebhookStatusError {
  created_at: string
  source_ip?: string
  stage: string
  error_message: string
}

export interface MetaWebhookStatus {
  verified_config: boolean
  last_verify_at?: string
  last_verify_mode?: string
  last_verify_source_ip?: string
  last_webhook_post_at?: string
  last_webhook_post_source_ip?: string
  last_webhook_delivery_status_seen?: string
  last_webhook_updates: number
  stale_callbacks?: boolean
  callback_staleness_minutes?: number
  recent_errors: MetaWebhookStatusError[]
}

export interface PaginatedPartyReminderResponse {
  items: PartyReminderInfo[]
  total: number
  offset: number
  limit: number
  has_more: boolean
}

export interface SchedulerStatus {
  is_running: boolean
  next_run?: string
  schedule_enabled: boolean
  frequency: string
  day_of_week: number
  time: string
  timezone: string
}

export interface AmountDueCalculation {
  party_code: string
  party_name: string
  closing_balance: number
  credit_days_used: number
  credit_days_source: string
  recent_sales_total: number
  recent_sales_count: number
  recent_sales_date_range: [string, string]
  amount_due: number
  calculation_timestamp: string
}

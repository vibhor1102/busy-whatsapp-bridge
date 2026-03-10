// Dashboard Types
export interface DashboardStats {
  system: SystemStats;
  database_connected: boolean;
  database_error?: string | null;
  queue: QueueStats;
  whatsapp: BaileysStatus;
  messages: {
    sent_today: number;
    sent_this_week: number;
    failed_today: number;
  };
}

export interface SystemStats {
  platform: string;
  hostname: string;
  python_version: string;
  version: string;
}

// Queue Types
export interface QueueStats {
  pending: number;
  retrying: number;
  dead_letter: number;
  sent_today: number;
  total_sent: number;
  total_failed: number;
  worker_running: boolean;
}

export interface Message {
  id: number;
  phone: string;
  message: string;
  pdf_url?: string;
  provider: string;
  status: 'pending' | 'retrying' | 'sent' | 'failed';
  retry_count: number;
  max_retries: number;
  next_retry_at?: string;
  error_message?: string;
  created_at: string;
  updated_at: string;
  completed_at?: string;
  delivery_status?: 'accepted' | 'sent' | 'delivered' | 'read' | 'failed' | 'unknown';
  source: string;
}

// WhatsApp/Baileys Types
export interface BaileysUserInfo {
  id: string;
  name: string;
  phone: string;
}

export interface BaileysStatus {
  state: 'connected' | 'qr_ready' | 'disconnected' | 'connecting' | 'reconnecting' | 'logged_out' | 'unreachable' | 'unknown' | 'degraded';
  qrAvailable?: boolean;
  qrTimestamp?: string;
  user?: BaileysUserInfo;
  qr_image?: string;
  error?: string;
  connectedAt?: string;
  disconnectedAt?: string;
  lastChecked?: string;
  bridgeLibraryVersion?: string;
  waProtocolVersion?: string;
  sessionStartedAt?: string;
  sessionState?: string;
  lastDisconnectReason?: string;
  reconnectAttempts?: number;
  dispatch_mode?: 'automatic_invoice' | 'supervised_batch' | 'paused';
  dispatch_blocked?: boolean;
  incident?: DispatchIncident | null;
}

export interface DispatchIncident {
  kind: string;
  title: string;
  message: string;
  severity: 'medium' | 'high' | 'critical';
  created_at: string;
  updated_at: string;
  acknowledged_at?: string | null;
  ignored_at?: string | null;
  resolved_at?: string | null;
  requires_manual_resolution: boolean;
  blocked: boolean;
  recovery_ready?: boolean;
  bridge_state?: string;
  session_state?: string;
}

export interface DispatchIncidentStatus {
  incident: DispatchIncident | null;
  attention_required: boolean;
  dispatch_blocked: boolean;
  last_bridge_status?: BaileysStatus | null;
  last_updated?: string | null;
}

export interface PlannerSummaryDay {
  day: string;
  planned_count: number;
  released_count: number;
  forfeited_count: number;
  party_codes: string[];
}

export interface PlannerSummary {
  week_key: string;
  snapshot_date?: string;
  days: PlannerSummaryDay[];
  totals: {
    planned: number;
    released: number;
    forfeited: number;
  };
}

export interface DispatchOpsStatus {
  company_id: string;
  bridge: BaileysStatus;
  incident: DispatchIncidentStatus;
  dispatch_mode: 'automatic_invoice' | 'supervised_batch' | 'paused';
  policy: DispatchPolicy & {
    can_dispatch_reminders: boolean;
    blocked_reason?: string | null;
  };
  snapshot: RefreshStats & {
    same_day_ready: boolean;
  };
  planner: {
    current_plan?: {
      week_key: string;
      snapshot_date?: string;
      capacities?: Record<string, number>;
      entries: Array<{
        party_code: string;
        recipient_name?: string;
        phone?: string;
        amount_due: number;
        planned_for?: string | null;
        state: 'planned' | 'released' | 'forfeited' | 'completed';
        released_at?: string | null;
        batch_id?: string | null;
      }>;
    } | null;
    summary: PlannerSummary;
    due_today: string[];
  };
}

// System Types
export interface SystemResources {
  cpu_percent: number;
  memory: {
    total: number;
    available: number;
    percent: number;
    used: number;
  };
  disk: {
    total: number;
    used: number;
    free: number;
    percent: number;
  };
}

export interface ProcessStatus {
  name: string;
  running: boolean;
  pid?: number;
}

// Log Types
export interface LogEntry {
  id: string;
  timestamp: string;
  level: 'DEBUG' | 'INFO' | 'WARNING' | 'ERROR';
  logger: string;
  message: string;
  source?: string;
}

// Settings Types
export interface Settings {
  whatsapp_provider: string;
  baileys_server_url: string;
  baileys_enabled: boolean;
  log_level: string;
  bds_file_path: string;
  companies?: Record<string, any>;
}

// Payment Reminder Types
export interface PartyReminderInfo {
  code: string;
  name: string;
  phone?: string;
  closing_balance: number;
  amount_due: number;
  credit_days_source: string;
  permanent_enabled: boolean;
  temp_enabled: boolean;
  last_reminder_sent?: string;
  reminder_count: number;
  can_generate_ledger: boolean;
}

export interface MessageTemplate {
  id: string;
  name: string;
  description?: string;
  content: string;
  variables: string[];
  is_default: boolean;
  created_at: string;
  updated_at: string;
}

export interface ScheduleConfig {
  enabled: boolean;
  frequency: 'weekly' | 'biweekly';
  day_of_week: number;
  time: string;
  timezone: string;
  batch_size: number;
  delay_between_messages: number;
}

export interface ReminderConfig {
  version: string;
  last_updated: string;
  default_credit_days: number;
  default_provider: string;
  currency_symbol: string;
  company?: {
    name: string;
    contact_phone: string;
    address?: string;
  };
  schedule: ScheduleConfig;
  parties: Record<string, PartyConfig>;
  templates: MessageTemplate[];
  active_template_id: string;
}

export interface PartyConfig {
  permanent_enabled: boolean;
  credit_days_override?: number;
  custom_template_id?: string;
  custom_message?: string;
  notes?: string;
}

export interface ReminderStats {
  total_parties: number;
  eligible_parties: number;
  enabled_parties: number;
  reminders_sent_today: number;
  reminders_sent_this_week: number;
  reminders_sent_this_month: number;
  total_amount_due: number;
  average_amount_due: number;
  last_scheduler_run?: string;
  next_scheduler_run?: string;
  scheduler_status: string;
}

export interface ReminderSnapshotStatus {
  has_snapshot: boolean;
  last_refreshed_at?: string;
  row_count: number;
  nonzero_count: number;
  duration_ms?: number;
}

export interface RefreshStats {
  last_refresh_at: string | null;
  last_5_durations_ms: number[];
  rolling_avg_ms: number;
  last_reminder_sent_at: string | null;
}

export interface SchedulerStatus {
  is_running: boolean;
  next_run?: string;
}

export interface AmountDueCalculation {
  party_code: string;
  party_name: string;
  closing_balance: number;
  credit_days_used: number;
  recent_sales_total: number;
  amount_due: number;
}

export interface PaginatedPartyReminderResponse {
  items: PartyReminderInfo[];
  total: number;
  offset: number;
  limit: number;
  has_more: boolean;
}

export interface ReminderSession {
  session_id: string;
  state: string;
  batch_id?: string;
  progress: {
    current: number;
    total: number;
    sent?: number;
    failed?: number;
    percentage: number;
  };
  failure_breakdown?: Record<string, number>;
  metrics?: {
    duration_seconds: number;
    avg_delay_seconds?: number;
    typing_time_total?: number;
  };
  dispatch_mode?: 'automatic_invoice' | 'supervised_batch' | 'paused';
}

export interface DispatchPolicy {
  paused: boolean;
  require_batch_approval: boolean;
  business_hours_enabled: boolean;
  business_hours_start: string;
  business_hours_end: string;
  timezone: string;
  max_batch_size: number;
  queue_throttle_per_minute: number;
  dispatch_mode: 'automatic_invoice' | 'supervised_batch' | 'paused';
}

export interface PendingApprovalBatch {
  batch_id: string;
  session_id: string;
  company_id: string;
  status: 'pending_approval' | 'approved' | 'rejected';
  created_at: string;
  approved_at?: string;
  rejected_at?: string;
  payload: {
    party_codes: string[];
    template_id: string;
    party_templates?: Record<string, string>;
    company_id: string;
  };
}

export interface ReminderBatchSummary {
  batch_id: string;
  session_id?: string;
  company_id: string;
  template_id?: string;
  sent_by?: string;
  total_parties: number;
  status: string;
  queue_success_count: number;
  queue_failed_count: number;
  skipped_count: number;
  delivery_accepted_count: number;
  delivery_sent_count: number;
  delivery_delivered_count: number;
  delivery_read_count: number;
  delivery_failed_count: number;
  in_flight_count: number;
  created_at?: string;
  started_at?: string;
  completed_at?: string;
}

export interface ReminderBatchRecipient {
  id: number;
  batch_id: string;
  party_code: string;
  recipient_name?: string;
  phone?: string;
  queue_id?: number;
  message_id?: string;
  status: string;
  queue_status: string;
  delivery_status: string;
  failure_stage?: string;
  failure_code?: string;
  failure_message?: string;
  retry_count: number;
  is_dead_letter: number;
  amount_due?: string;
  media_attached: number;
  created_at?: string;
  updated_at?: string;
}

export interface ReminderBatchReport {
  batch: ReminderBatchSummary;
  recipients: ReminderBatchRecipient[];
}

export interface AntiSpamConfig {
  enabled: boolean;
  message_inflation: boolean;
  pdf_inflation: boolean;
  typing_simulation: boolean;
  startup_delay_enabled: boolean;
  reminder_cooldown_enabled: boolean;
  reminder_cooldown_minutes: number;
}

export interface MetaWebhookStatus {
  verified_config: boolean;
  last_verify_at?: string;
  last_webhook_post_at?: string;
  last_webhook_delivery_status_seen?: string;
  callback_staleness_minutes?: number;
  stale_callbacks: boolean;
}

import type { 
  DashboardStats, 
  Message, 
  QueueStats, 
  LogEntry,
  ProcessStatus,
  SystemResources,
  BaileysStatus,
  ReminderConfig,
  ScheduleConfig,
  PartyReminderInfo,
  PartyConfig,
  AmountDueCalculation,
  MessageTemplate,
  ReminderStats,
  SchedulerStatus
} from '@/types'

const API_BASE = '/api/v1'

class ApiService {
  private async fetch<T>(url: string, options?: RequestInit): Promise<T> {
    const response = await fetch(`${API_BASE}${url}`, {
      headers: {
        'Content-Type': 'application/json',
      },
      ...options,
    })
    
    if (!response.ok) {
      throw new Error(`API Error: ${response.status} ${response.statusText}`)
    }
    
    return response.json()
  }

  // Dashboard
  async getDashboardStats(): Promise<DashboardStats> {
    return this.fetch<DashboardStats>('/dashboard/stats')
  }

  // Queue
  async getQueueStats(): Promise<QueueStats> {
    return this.fetch<QueueStats>('/queue/status')
  }

  async getPendingMessages(limit: number = 100): Promise<Message[]> {
    return this.fetch<{ messages: Message[] }>(`/queue/pending?limit=${limit}`)
      .then(res => res.messages)
  }

  async getQueueHistory(
    phone?: string,
    status?: string,
    limit: number = 100
  ): Promise<Message[]> {
    const params = new URLSearchParams()
    if (phone) params.append('phone', phone)
    if (status) params.append('status', status)
    params.append('limit', limit.toString())
    
    return this.fetch<{ messages: Message[] }>(`/queue/history?${params}`)
      .then(res => res.messages)
  }

  async getDeadLetterMessages(limit: number = 100): Promise<Message[]> {
    return this.fetch<{ messages: Message[] }>(`/queue/dead-letter?limit=${limit}`)
      .then(res => res.messages)
  }

  async retryMessage(id: number): Promise<{ success: boolean; message: string }> {
    return this.fetch<{ success: boolean; message: string }>(
      `/queue/retry/${id}`,
      { method: 'POST' }
    )
  }

  // WhatsApp
  async getBaileysStatus(): Promise<BaileysStatus> {
    return this.fetch<{ success?: boolean; data?: BaileysStatus; error?: string }>('/baileys/status')
      .then(res => res.data || { state: 'unreachable', error: res.error || 'Baileys status unavailable' })
  }

  async getBaileysQr(): Promise<{ qrImage?: string; state?: string; user?: Record<string, any> }> {
    return this.fetch<{ data: { qrImage?: string; state?: string; user?: Record<string, any> } }>('/baileys/qr')
      .then(res => res.data || {})
  }

  async restartBaileys(): Promise<{ success: boolean; message: string }> {
    return this.fetch<{ success: boolean; message: string }>(
      '/baileys/restart',
      { method: 'POST' }
    )
  }

  async disconnectWhatsApp(): Promise<{ success: boolean; message: string }> {
    return this.fetch<{ success: boolean; message: string }>(
      '/whatsapp/disconnect',
      { method: 'POST' }
    )
  }

  async clearWhatsAppSession(): Promise<{ success: boolean; message: string }> {
    return this.fetch<{ success: boolean; message: string }>(
      '/whatsapp/session',
      { method: 'DELETE' }
    )
  }

  // Logs
  async getLogs(
    level?: string,
    limit: number = 100
  ): Promise<LogEntry[]> {
    const params = new URLSearchParams()
    if (level) params.append('level', level)
    params.append('limit', limit.toString())
    
    return this.fetch<{ logs: LogEntry[] }>(`/logs?${params}`)
      .then(res => res.logs)
  }

  // System
  async getSystemResources(): Promise<SystemResources> {
    return this.fetch<SystemResources>('/system/resources')
  }

  async startBaileys(): Promise<{ success: boolean }> {
    return this.fetch<{ success: boolean }>(
      '/system/baileys/start',
      { method: 'POST' }
    )
  }

  async stopBaileys(): Promise<{ success: boolean }> {
    return this.fetch<{ success: boolean }>(
      '/system/baileys/stop',
      { method: 'POST' }
    )
  }

  // Settings
  async getSettings(): Promise<Record<string, any>> {
    return this.fetch<Record<string, any>>('/settings')
  }

  async getEnvContents(): Promise<{ content: string }> {
    return this.fetch<{ content: string }>('/settings/env')
  }

  async updateEnv(content: string): Promise<{ success: boolean }> {
    return this.fetch<{ success: boolean }>('/settings/env', {
      method: 'PUT',
      body: JSON.stringify({ content }),
    })
  }

  // Payment Reminders
  async getReminderConfig(): Promise<ReminderConfig> {
    return this.fetch<ReminderConfig>('/reminders/config')
  }

  async updateReminderConfig(config: ReminderConfig): Promise<{ success: boolean; message: string }> {
    return this.fetch<{ success: boolean; message: string }>('/reminders/config', {
      method: 'PUT',
      body: JSON.stringify(config),
    })
  }

  async updateScheduleConfig(schedule: ScheduleConfig): Promise<{ success: boolean; message: string }> {
    return this.fetch<{ success: boolean; message: string }>('/reminders/config/schedule', {
      method: 'PUT',
      body: JSON.stringify(schedule),
    })
  }

  async getEligibleParties(
    search?: string,
    sortBy: string = 'amount_due',
    sortOrder: string = 'desc',
    filterBy: string = 'all'
  ): Promise<PartyReminderInfo[]> {
    const params = new URLSearchParams()
    if (search) params.append('search', search)
    params.append('sort_by', sortBy)
    params.append('sort_order', sortOrder)
    params.append('filter_by', filterBy)
    
    return this.fetch<PartyReminderInfo[]>(`/reminders/parties?${params}`)
  }

  async getPartyDetails(partyCode: string): Promise<PartyReminderInfo> {
    return this.fetch<PartyReminderInfo>(`/reminders/parties/${partyCode}`)
  }

  async updatePartyConfig(
    partyCode: string,
    config: Partial<PartyConfig>
  ): Promise<{ success: boolean; party: PartyReminderInfo; message: string }> {
    return this.fetch<{ success: boolean; party: PartyReminderInfo; message: string }>(
      `/reminders/parties/${partyCode}`,
      {
        method: 'PUT',
        body: JSON.stringify(config),
      }
    )
  }

  async calculateAmountDue(
    partyCode: string,
    creditDaysOverride?: number
  ): Promise<AmountDueCalculation> {
    const params = creditDaysOverride ? `?credit_days_override=${creditDaysOverride}` : ''
    return this.fetch<AmountDueCalculation>(`/reminders/parties/${partyCode}/calculate${params}`, {
      method: 'POST',
    })
  }

  async generateLedgerPdf(partyCode: string): Promise<Blob> {
    const response = await fetch(`${API_BASE}/reminders/parties/${partyCode}/ledger`)
    if (!response.ok) {
      throw new Error(`API Error: ${response.status} ${response.statusText}`)
    }
    return response.blob()
  }

  async sendReminders(
    partyCodes: string[],
    templateId: string
  ): Promise<{ status: string; batch_id: string; message: string }> {
    return this.fetch<{ status: string; batch_id: string; message: string }>('/reminders/batch', {
      method: 'POST',
      body: JSON.stringify({ party_codes: partyCodes, template_id: templateId }),
    })
  }

  async scheduleReminders(
    partyCodes: string[],
    templateId: string,
    scheduleFor?: Date
  ): Promise<{ status: string; batch_id: string; scheduled_for?: Date; message: string }> {
    return this.fetch<{ status: string; batch_id: string; scheduled_for?: Date; message: string }>(
      '/reminders/schedule',
      {
        method: 'POST',
        body: JSON.stringify({
          party_codes: partyCodes,
          template_id: templateId,
          schedule_for: scheduleFor,
        }),
      }
    )
  }

  // Templates
  async getTemplates(): Promise<MessageTemplate[]> {
    return this.fetch<MessageTemplate[]>('/reminders/templates')
  }

  async getTemplate(templateId: string): Promise<MessageTemplate> {
    return this.fetch<MessageTemplate>(`/reminders/templates/${templateId}`)
  }

  async createTemplate(template: MessageTemplate): Promise<{ success: boolean; template: MessageTemplate; message: string }> {
    return this.fetch<{ success: boolean; template: MessageTemplate; message: string }>('/reminders/templates', {
      method: 'POST',
      body: JSON.stringify(template),
    })
  }

  async updateTemplate(
    templateId: string,
    template: MessageTemplate
  ): Promise<{ success: boolean; template: MessageTemplate; message: string }> {
    return this.fetch<{ success: boolean; template: MessageTemplate; message: string }>(
      `/reminders/templates/${templateId}`,
      {
        method: 'PUT',
        body: JSON.stringify(template),
      }
    )
  }

  async deleteTemplate(templateId: string): Promise<{ success: boolean; message: string }> {
    return this.fetch<{ success: boolean; message: string }>(`/reminders/templates/${templateId}`, {
      method: 'DELETE',
    })
  }

  async previewTemplate(
    templateId: string,
    variables?: Record<string, string>
  ): Promise<{ template_id: string; preview: string; variables_used: string[] }> {
    return this.fetch<{ template_id: string; preview: string; variables_used: string[] }>(
      `/reminders/templates/${templateId}/preview`,
      {
        method: 'POST',
        body: JSON.stringify({ variables }),
      }
    )
  }

  async setActiveTemplate(templateId: string): Promise<{ success: boolean; message: string }> {
    return this.fetch<{ success: boolean; message: string }>(`/reminders/templates/${templateId}/active`, {
      method: 'POST',
    })
  }

  // Scheduler
  async getSchedulerStatus(): Promise<SchedulerStatus> {
    return this.fetch<SchedulerStatus>('/reminders/scheduler/status')
  }

  async startScheduler(): Promise<{ success: boolean; message: string }> {
    return this.fetch<{ success: boolean; message: string }>('/reminders/scheduler/start', {
      method: 'POST',
    })
  }

  async stopScheduler(): Promise<{ success: boolean; message: string }> {
    return this.fetch<{ success: boolean; message: string }>('/reminders/scheduler/stop', {
      method: 'POST',
    })
  }

  async pauseScheduler(): Promise<{ success: boolean; message: string }> {
    return this.fetch<{ success: boolean; message: string }>('/reminders/scheduler/pause', {
      method: 'POST',
    })
  }

  async resumeScheduler(): Promise<{ success: boolean; message: string }> {
    return this.fetch<{ success: boolean; message: string }>('/reminders/scheduler/resume', {
      method: 'POST',
    })
  }

  async triggerManualRun(): Promise<{ status: string; batch_id: string; message: string }> {
    return this.fetch<{ status: string; batch_id: string; message: string }>('/reminders/scheduler/trigger', {
      method: 'POST',
    })
  }

  // Stats
  async getReminderStats(): Promise<ReminderStats> {
    return this.fetch<ReminderStats>('/reminders/stats')
  }
}

export const api = new ApiService()

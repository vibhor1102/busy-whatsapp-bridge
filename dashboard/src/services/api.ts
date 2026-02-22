import type { 
  DashboardStats, 
  Message, 
  QueueStats, 
  LogEntry,
  ProcessStatus,
  SystemResources,
  BaileysStatus 
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
    return this.fetch<{ data: BaileysStatus }>('/baileys/status')
      .then(res => res.data)
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
}

export const api = new ApiService()

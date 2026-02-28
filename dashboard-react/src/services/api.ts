import axios from 'axios';
import type { AxiosInstance, AxiosResponse } from 'axios';
import type {
  DashboardStats,
  QueueStats,
  Message,
  BaileysStatus,
  SystemResources,
  LogEntry,
  Settings,
  ReminderConfig,
  ScheduleConfig,
  ReminderStats,
  ReminderSnapshotStatus,
  PartyReminderInfo,
  MessageTemplate,
  AmountDueCalculation,
  PaginatedPartyReminderResponse,
  SchedulerStatus,
  AntiSpamConfig,
  ReminderSession,
  MetaWebhookStatus,
} from '../types';

const API_BASE = '/api/v1';

class ApiService {
  private client: AxiosInstance;

  constructor() {
    this.client = axios.create({
      baseURL: API_BASE,
      headers: {
        'Content-Type': 'application/json',
      },
    });
  }

  private async fetch<T>(endpoint: string, options?: { method?: string; body?: any }): Promise<T> {
    const response: AxiosResponse<T> = await this.client.request({
      url: endpoint,
      method: options?.method || 'GET',
      data: options?.body,
    });
    return response.data;
  }

  // Dashboard
  async getDashboardStats(): Promise<DashboardStats> {
    return this.fetch<DashboardStats>('/dashboard/stats');
  }

  // Queue
  async getQueueStats(): Promise<QueueStats> {
    return this.fetch<QueueStats>('/queue/status');
  }

  async getQueueHistory(params?: {
    phone?: string;
    status?: string;
    delivery_status?: string;
    from_time?: string;
    to_time?: string;
    limit?: number;
    offset?: number;
  }): Promise<{ items: Message[]; total: number; limit: number; offset: number }> {
    const queryParams = new URLSearchParams();
    if (params?.phone) queryParams.append('phone', params.phone);
    if (params?.status) queryParams.append('status', params.status);
    if (params?.delivery_status) queryParams.append('delivery_status', params.delivery_status);
    if (params?.from_time) queryParams.append('from_time', params.from_time);
    if (params?.to_time) queryParams.append('to_time', params.to_time);
    if (params?.limit) queryParams.append('limit', params.limit.toString());
    if (params?.offset) queryParams.append('offset', params.offset.toString());
    
    return this.fetch(`/queue/history?${queryParams.toString()}`);
  }

  async getPendingMessages(limit: number = 50): Promise<{ messages: Message[] }> {
    return this.fetch(`/queue/pending?limit=${limit}`);
  }

  async getDeadLetterMessages(limit: number = 50): Promise<{ messages: Message[] }> {
    return this.fetch(`/queue/dead-letter?limit=${limit}`);
  }

  async retryMessage(id: number): Promise<{ success: boolean; message: string }> {
    return this.fetch(`/queue/retry/${id}`, { method: 'POST' });
  }

  async processQueue(batchSize?: number): Promise<{ success: boolean; processed: number; message: string }> {
    const params = batchSize ? `?batch_size=${batchSize}` : '';
    return this.fetch(`/queue/process${params}`, { method: 'POST' });
  }

  // WhatsApp/Baileys
  async getBaileysStatus(): Promise<{ success?: boolean; data?: BaileysStatus; error?: string }> {
    return this.fetch('/baileys/status');
  }

  async getBaileysQr(): Promise<{ data: { qrImage?: string; state?: string; user?: Record<string, any> } }> {
    return this.fetch('/baileys/qr');
  }

  async restartBaileys(): Promise<{ success: boolean; message: string }> {
    return this.fetch('/baileys/restart', { method: 'POST' });
  }

  async disconnectWhatsApp(): Promise<{ success: boolean; message: string }> {
    return this.fetch('/whatsapp/disconnect', { method: 'POST' });
  }

  async clearWhatsAppSession(): Promise<{ success: boolean; message: string }> {
    return this.fetch('/whatsapp/session', { method: 'DELETE' });
  }

  // Logs
  async getLogs(params?: {
    level?: string;
    limit?: number;
    source?: string;
  }): Promise<{ logs: LogEntry[] }> {
    const queryParams = new URLSearchParams();
    if (params?.level) queryParams.append('level', params.level);
    if (params?.limit) queryParams.append('limit', params.limit.toString());
    if (params?.source) queryParams.append('source', params.source);
    
    return this.fetch(`/logs?${queryParams.toString()}`);
  }

  // System
  async getSystemResources(): Promise<SystemResources> {
    return this.fetch('/system/resources');
  }

  async startBaileys(): Promise<{ success: boolean }> {
    return this.fetch('/system/baileys/start', { method: 'POST' });
  }

  async stopBaileys(): Promise<{ success: boolean }> {
    return this.fetch('/system/baileys/stop', { method: 'POST' });
  }

  async startQueueWorker(): Promise<{ success: boolean; message: string; worker_running: boolean }> {
    return this.fetch('/system/queue/start', { method: 'POST' });
  }

  async stopQueueWorker(): Promise<{ success: boolean; message: string; worker_running: boolean }> {
    return this.fetch('/system/queue/stop', { method: 'POST' });
  }

  // Settings
  async getSettings(): Promise<Settings> {
    return this.fetch('/settings');
  }

  async getSettingsConfig(): Promise<{ content: Record<string, any> }> {
    return this.fetch('/settings/config');
  }

  async updateSettingsConfig(settings: Partial<Settings>): Promise<{ success: boolean; message: string }> {
    return this.fetch('/settings/config', {
      method: 'PUT',
      body: settings,
    });
  }

  // Payment Reminders - Configuration
  async getReminderConfig(): Promise<ReminderConfig> {
    return this.fetch('/reminders/config');
  }

  async updateReminderConfig(config: Partial<ReminderConfig>): Promise<{ status: string; message: string }> {
    return this.fetch('/reminders/config', {
      method: 'PUT',
      body: config,
    });
  }

  async updateScheduleConfig(schedule: ScheduleConfig): Promise<{ success: boolean; message: string }> {
    return this.fetch('/reminders/config/schedule', {
      method: 'PUT',
      body: schedule,
    });
  }

  // Payment Reminders - Parties
  async getEligibleParties(params?: {
    search?: string;
    sort_by?: string;
    sort_order?: string;
    filter_by?: string;
    offset?: number;
    limit?: number;
    include_zero?: boolean;
  }): Promise<PaginatedPartyReminderResponse> {
    const queryParams = new URLSearchParams();
    if (params?.search) queryParams.append('search', params.search);
    if (params?.sort_by) queryParams.append('sort_by', params.sort_by);
    if (params?.sort_order) queryParams.append('sort_order', params.sort_order);
    if (params?.filter_by) queryParams.append('filter_by', params.filter_by);
    if (params?.offset !== undefined) queryParams.append('offset', params.offset.toString());
    if (params?.limit) queryParams.append('limit', params.limit.toString());
    if (params?.include_zero) queryParams.append('include_zero', 'true');
    
    return this.fetch(`/reminders/parties?${queryParams.toString()}`);
  }

  async getParty(partyCode: string): Promise<PartyReminderInfo> {
    return this.fetch(`/reminders/parties/${partyCode}`);
  }

  async updateParty(
    partyCode: string,
    data: {
      permanent_enabled?: boolean;
      credit_days_override?: number;
      custom_template_id?: string;
      notes?: string;
    }
  ): Promise<{ success: boolean; party: PartyReminderInfo; message: string }> {
    return this.fetch(`/reminders/parties/${partyCode}`, {
      method: 'PUT',
      body: data,
    });
  }

  async calculateAmountDue(
    partyCode: string,
    creditDaysOverride?: number
  ): Promise<AmountDueCalculation> {
    const params = creditDaysOverride ? `?credit_days_override=${creditDaysOverride}` : '';
    return this.fetch(`/reminders/parties/${partyCode}/calculate${params}`, {
      method: 'POST',
    });
  }

  async generateLedgerPdf(partyCode: string): Promise<Blob> {
    const response = await this.client.get(`/reminders/parties/${partyCode}/ledger`, {
      responseType: 'blob',
    });
    return response.data;
  }

  async getReminderSnapshotStatus(): Promise<ReminderSnapshotStatus> {
    return this.fetch('/reminders/snapshot/status');
  }

  async refreshReminderSnapshot(): Promise<ReminderSnapshotStatus> {
    return this.fetch('/reminders/snapshot/refresh', { method: 'POST' });
  }

  // Payment Reminders - Batch/Session
  async sendReminders(
    partyCodes: string[],
    templateId: string,
    partyTemplateMap?: Record<string, string>
  ): Promise<{ status: string; batch_id: string; session_id: string; message: string }> {
    return this.fetch('/reminders/batch', {
      method: 'POST',
      body: {
        party_codes: partyCodes,
        template_id: templateId,
        party_templates: partyTemplateMap,
      },
    });
  }

  async getSessionStatus(sessionId: string): Promise<ReminderSession | null> {
    return this.fetch(`/reminders/sessions/${sessionId}/status`);
  }

  async pauseSession(sessionId: string): Promise<void> {
    return this.fetch(`/reminders/sessions/${sessionId}/pause`, { method: 'POST' });
  }

  async resumeSession(sessionId: string): Promise<void> {
    return this.fetch(`/reminders/sessions/${sessionId}/resume`, { method: 'POST' });
  }

  async stopSession(sessionId: string): Promise<void> {
    return this.fetch(`/reminders/sessions/${sessionId}/stop`, { method: 'POST' });
  }

  // Payment Reminders - Templates
  async getTemplates(): Promise<MessageTemplate[]> {
    return this.fetch('/reminders/templates');
  }

  async getTemplate(templateId: string): Promise<MessageTemplate> {
    return this.fetch(`/reminders/templates/${templateId}`);
  }

  async createTemplate(template: Partial<MessageTemplate>): Promise<{
    success: boolean;
    template: MessageTemplate;
    message: string;
  }> {
    return this.fetch('/reminders/templates', {
      method: 'POST',
      body: template,
    });
  }

  async updateTemplate(
    templateId: string,
    template: Partial<MessageTemplate>
  ): Promise<{ success: boolean; template: MessageTemplate; message: string }> {
    return this.fetch(`/reminders/templates/${templateId}`, {
      method: 'PUT',
      body: template,
    });
  }

  async deleteTemplate(templateId: string): Promise<{ success: boolean; message: string }> {
    return this.fetch(`/reminders/templates/${templateId}`, { method: 'DELETE' });
  }

  async setDefaultTemplate(templateId: string): Promise<{ success: boolean; message: string }> {
    return this.fetch(`/reminders/templates/${templateId}/default`, { method: 'POST' });
  }

  async previewTemplate(
    templateId: string,
    variables?: Record<string, string>
  ): Promise<{ template_id: string; preview: string; variables_used: string[] }> {
    return this.fetch(`/reminders/templates/${templateId}/preview`, {
      method: 'POST',
      body: { variables },
    });
  }

  // Payment Reminders - Scheduler
  async getSchedulerStatus(): Promise<SchedulerStatus> {
    return this.fetch('/reminders/scheduler/status');
  }

  async startScheduler(): Promise<{ success: boolean; message: string }> {
    return this.fetch('/reminders/scheduler/start', { method: 'POST' });
  }

  async stopScheduler(): Promise<{ success: boolean; message: string }> {
    return this.fetch('/reminders/scheduler/stop', { method: 'POST' });
  }

  async pauseScheduler(): Promise<{ success: boolean; message: string }> {
    return this.fetch('/reminders/scheduler/pause', { method: 'POST' });
  }

  async resumeScheduler(): Promise<{ success: boolean; message: string }> {
    return this.fetch('/reminders/scheduler/resume', { method: 'POST' });
  }

  async triggerManualRun(): Promise<{ status: string; batch_id: string; message: string }> {
    return this.fetch('/reminders/scheduler/trigger', { method: 'POST' });
  }

  // Payment Reminders - Stats
  async getReminderStats(): Promise<ReminderStats> {
    return this.fetch('/reminders/stats');
  }

  async getReminderHistory(params?: {
    status?: string;
    delivery_status?: string;
    from_time?: string;
    to_time?: string;
    limit?: number;
    offset?: number;
  }): Promise<{ items: Message[]; total: number; limit: number; offset: number; counts: any }> {
    const queryParams = new URLSearchParams();
    if (params?.status) queryParams.append('status', params.status);
    if (params?.delivery_status) queryParams.append('delivery_status', params.delivery_status);
    if (params?.from_time) queryParams.append('from_time', params.from_time);
    if (params?.to_time) queryParams.append('to_time', params.to_time);
    if (params?.limit) queryParams.append('limit', params.limit.toString());
    if (params?.offset) queryParams.append('offset', params.offset.toString());
    
    return this.fetch(`/reminders/history?${queryParams.toString()}`);
  }

  // Anti-Spam
  async getAntiSpamConfig(): Promise<AntiSpamConfig> {
    return this.fetch('/reminders/antispam/config');
  }

  async updateAntiSpamConfig(config: AntiSpamConfig): Promise<{ status: string; message: string }> {
    return this.fetch('/reminders/antispam/config', {
      method: 'PUT',
      body: config,
    });
  }

  // Meta Webhook
  async getMetaWebhookStatus(): Promise<MetaWebhookStatus> {
    return this.fetch('/whatsapp/meta/webhook/status');
  }
}

export const api = new ApiService();
export default api;

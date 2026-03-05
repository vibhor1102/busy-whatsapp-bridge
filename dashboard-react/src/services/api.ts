import axios from 'axios';
import type { AxiosInstance, AxiosResponse, AxiosError, InternalAxiosRequestConfig } from 'axios';
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
  RefreshStats,
  PartyReminderInfo,
  MessageTemplate,
  AmountDueCalculation,
  PaginatedPartyReminderResponse,
  SchedulerStatus,
  AntiSpamConfig,
  ReminderSession,
  ReminderBatchReport,
  ReminderBatchSummary,
  MetaWebhookStatus,
  BaileysUserInfo,
} from '../types';

// Type for reminder history counts
export interface ReminderHistoryCounts {
  sent?: number;
  failed?: number;
  pending?: number;
  retrying?: number;
  total?: number;
}

const API_BASE = '/api/v1';
const DEFAULT_TIMEOUT = 30000; // 30 seconds

export interface ApiError {
  message: string;
  status?: number;
  code?: string;
}

export class ApiErrorException extends Error {
  status?: number;
  code?: string;

  constructor(message: string, status?: number, code?: string) {
    super(message);
    this.name = 'ApiErrorException';
    this.status = status;
    this.code = code;
  }
}

export interface CompanyInfo {
  id: string;
  name: string;
  path: string;
}

class ApiService {
  private client: AxiosInstance;
  private companyId: string;
  private companyBootstrapPromise: Promise<void> | null;
  private companyValidationTtlMs: number;
  private lastCompanyValidationAt: number;

  constructor() {
    this.companyId = localStorage.getItem('busy_whatsapp_bridge_company_id') || '';
    this.companyBootstrapPromise = null;
    this.companyValidationTtlMs = 60000;
    this.lastCompanyValidationAt = 0;

    this.client = axios.create({
      baseURL: API_BASE,
      headers: {
        'Content-Type': 'application/json',
      },
      timeout: DEFAULT_TIMEOUT,
    });

    // Request interceptor for error logging
    this.client.interceptors.request.use(
      async (config: InternalAxiosRequestConfig) => {
        if (this.isCompanyScopedEndpoint(config.url)) {
          await this.ensureCompanyContext();
          config.headers['X-Company-Id'] = this.companyId;
        } else if (this.companyId) {
          config.headers['X-Company-Id'] = this.companyId;
        }
        console.log(`[API Request] ${config.method?.toUpperCase()} ${config.url}`);
        return config;
      },
      (error: AxiosError) => {
        console.error('[API Request Error]', error);
        return Promise.reject(error);
      }
    );

    // Response interceptor for error transformation
    this.client.interceptors.response.use(
      (response: AxiosResponse) => response,
      (error: AxiosError) => {
        const apiError = this.transformError(error);
        console.error('[API Response Error]', apiError);
        return Promise.reject(apiError);
      }
    );
  }

  private async ensureCompanyContext(): Promise<void> {
    if (this.companyId) {
      await this.ensurePersistedCompanyStillValid();
      return;
    }
    if (!this.companyBootstrapPromise) {
      this.companyBootstrapPromise = this.bootstrapCompanyContext();
    }
    await this.companyBootstrapPromise;
  }

  private isCompanyScopedEndpoint(url?: string): boolean {
    if (!url) return false;
    return url.startsWith('/reminders') || url.startsWith('/dashboard/stats');
  }

  private async bootstrapCompanyContext(): Promise<void> {
    try {
      const response = await axios.get<{ companies: CompanyInfo[] }>(`${API_BASE}/companies`, {
        timeout: DEFAULT_TIMEOUT,
      });
      const companies = response.data?.companies || [];
      if (companies.length === 0) {
        throw new ApiErrorException('No database companies are configured. Add one in Settings.', 412);
      }

      const persisted = localStorage.getItem('busy_whatsapp_bridge_company_id') || '';
      const chosen = companies.find((c) => c.id === persisted) ? persisted : companies[0].id;
      this.setCompanyId(chosen);
    } finally {
      this.companyBootstrapPromise = null;
    }
  }

  private async ensurePersistedCompanyStillValid(): Promise<void> {
    const now = Date.now();
    if (now - this.lastCompanyValidationAt < this.companyValidationTtlMs) {
      return;
    }

    try {
      const response = await axios.get<{ companies: CompanyInfo[] }>(`${API_BASE}/companies`, {
        timeout: DEFAULT_TIMEOUT,
      });
      const companies = response.data?.companies || [];
      if (companies.length === 0) {
        this.setCompanyId('');
        return;
      }
      const exists = companies.some((c) => c.id === this.companyId);
      if (!exists) {
        this.setCompanyId(companies[0].id);
      }
      this.lastCompanyValidationAt = Date.now();
    } catch {
      this.lastCompanyValidationAt = Date.now();
      // Best-effort validation; request-level errors are handled downstream.
    }
  }

  private transformError(error: AxiosError): ApiErrorException {
    if (error.response) {
      const status = error.response.status;
      const data = error.response.data as { message?: string; error?: string };
      let message = data?.message || data?.error || 'An error occurred';

      // Handle specific HTTP status codes
      switch (status) {
        case 401:
          message = 'Authentication required. Please log in again.';
          break;
        case 403:
          message = 'You do not have permission to perform this action.';
          break;
        case 404:
          message = 'The requested resource was not found.';
          break;
        case 408:
          message = data?.message || 'Request timed out while waiting for the server.';
          break;
        case 412:
          message = data?.message || 'A required application precondition is not met.';
          break;
        case 422:
          message = data?.message || 'Invalid request data. Please check your input.';
          break;
        case 500:
          message = 'Server error. Please try again later.';
          break;
        case 502:
        case 503:
        case 504:
          message = 'Service unavailable. Please try again later.';
          break;
        default:
          message = data?.message || `HTTP Error ${status}`;
      }

      return new ApiErrorException(message, status, error.code);
    }

    if (error.request) {
      if (error.code === 'ECONNABORTED') {
        return new ApiErrorException('Request timed out. Please try again.', 408, error.code);
      }
      if (error.code === 'ERR_NETWORK') {
        return new ApiErrorException('Network error. Please check your connection.', 0, error.code);
      }
      return new ApiErrorException('No response received from server.', 0, error.code);
    }

    return new ApiErrorException(error.message || 'An unexpected error occurred');
  }

  private async fetch<T>(endpoint: string, options?: { method?: string; body?: unknown; signal?: AbortSignal }): Promise<T> {
    try {
      const response: AxiosResponse<T> = await this.client.request({
        url: endpoint,
        method: options?.method || 'GET',
        data: options?.body,
        signal: options?.signal,
      });
      return response.data;
    } catch (error) {
      if (error instanceof ApiErrorException) {
        throw error;
      }
      throw new ApiErrorException('An unexpected error occurred');
    }
  }

  // System/Company
  public setCompanyId(id: string) {
    this.companyId = (id || '').trim();
    this.lastCompanyValidationAt = 0;
    if (this.companyId) {
      localStorage.setItem('busy_whatsapp_bridge_company_id', this.companyId);
    } else {
      localStorage.removeItem('busy_whatsapp_bridge_company_id');
    }
  }

  public getCompanyId(): string {
    return this.companyId;
  }

  async getCompanies(): Promise<{ companies: CompanyInfo[] }> {
    return this.fetch('/companies');
  }

  async getNextCompanyId(): Promise<{ company_id: string }> {
    return this.fetch('/system/next-company-id');
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
  async getBaileysStatus(): Promise<BaileysStatus> {
    const response = await this.fetch<BaileysStatus | { success: boolean; data: BaileysStatus }>('/baileys/status');
    if (response && typeof response === 'object' && 'success' in response && 'data' in response) {
      const data = (response as { data: BaileysStatus }).data;
      return {
        state: data?.state ?? 'unknown',
        qrAvailable: data?.qrAvailable ?? false,
        qrTimestamp: data?.qrTimestamp,
        user: data?.user,
        connectedAt: data?.connectedAt,
        disconnectedAt: data?.disconnectedAt,
        lastChecked: data?.lastChecked,
      } as BaileysStatus;
    }
    const status = response as BaileysStatus;
    return {
      state: status?.state ?? 'unknown',
      qrAvailable: status?.qrAvailable ?? false,
      qrTimestamp: status?.qrTimestamp,
      user: status?.user,
      connectedAt: status?.connectedAt,
      disconnectedAt: status?.disconnectedAt,
      lastChecked: status?.lastChecked,
    } as BaileysStatus;
  }

  async getBaileysQr(): Promise<{ data: { qrImage?: string; state?: string; user?: BaileysUserInfo } }> {
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

  async browseSystemFile(): Promise<{ path: string | null; success: boolean; message?: string }> {
    return this.fetch('/system/browse-file');
  }

  async identifyDatabase(bds_file_path: string, bds_password?: string): Promise<{
    success: boolean;
    company_id?: string;
    company_name?: string;
    financial_year?: string;
    message?: string;
  }> {
    return this.fetch('/system/identify-database', {
      method: 'POST',
      body: { bds_file_path, bds_password: bds_password || 'ILoveMyINDIA' },
    });
  }

  // Settings
  async getSettings(): Promise<Settings> {
    return this.fetch('/settings');
  }

  async getSettingsConfig(): Promise<{ content: Record<string, unknown> }> {
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
    // Snapshot refresh involves heavy ODBC queries that can take several minutes
    const response: AxiosResponse<ReminderSnapshotStatus> = await this.client.request({
      url: '/reminders/snapshot/refresh',
      method: 'POST',
      timeout: 1800000, // 30 minutes — this is a heavy DB operation
    });
    return response.data;
  }

  async refreshReminderSnapshotWithSignal(signal: AbortSignal): Promise<ReminderSnapshotStatus> {
    // Same as refreshReminderSnapshot but with a cancellable AbortSignal
    const response: AxiosResponse<ReminderSnapshotStatus> = await this.client.request({
      url: '/reminders/snapshot/refresh',
      method: 'POST',
      timeout: 1800000, // 30 minutes with signal for manual cancel
      signal,
    });
    return response.data;
  }

  async getRefreshStats(): Promise<RefreshStats> {
    return this.fetch('/reminders/refresh-stats');
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

  async getSessionStatus(sessionId: string, signal?: AbortSignal): Promise<ReminderSession> {
    return this.fetch(`/reminders/sessions/${sessionId}/status`, { signal });
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

  async getBatchReport(batchId: string): Promise<ReminderBatchReport> {
    return this.fetch(`/reminders/batches/${batchId}/report`);
  }

  async getBatchFailures(
    batchId: string,
    params?: { failure_stage?: string; failure_code?: string }
  ): Promise<{ items: any[]; total: number }> {
    const queryParams = new URLSearchParams();
    if (params?.failure_stage) queryParams.append('failure_stage', params.failure_stage);
    if (params?.failure_code) queryParams.append('failure_code', params.failure_code);
    const query = queryParams.toString();
    return this.fetch(`/reminders/batches/${batchId}/failures${query ? `?${query}` : ''}`);
  }

  async listRecentBatches(limit: number = 20): Promise<{ items: ReminderBatchSummary[]; total: number; limit: number }> {
    return this.fetch(`/reminders/batches/recent?limit=${limit}`);
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
  }): Promise<{ items: Message[]; total: number; limit: number; offset: number; counts: ReminderHistoryCounts }> {
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

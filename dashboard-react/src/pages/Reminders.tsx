import { useState, useEffect, useMemo, useCallback, useRef } from 'react';
import axios from 'axios';
import { useQuery, useMutation, useQueryClient, keepPreviousData } from '@tanstack/react-query';
import { useVirtualizer } from '@tanstack/react-virtual';
import { motion, AnimatePresence } from 'framer-motion';
import {
  RefreshCw,
  Send,
  Pause,
  Play,
  Square,
  ChevronDown,
  ChevronUp,
  Users,
  Shield,
  FileText,
  Download,
  CheckCircle,
  Search,
  X,
  Loader2,
  ExternalLink,
} from 'lucide-react';
import { api, type CompanyInfo } from '../services/api';
import { useRemindersStore } from '../stores/remindersStore';
import { LoadingState } from '../components/ui/LoadingState';
import { TemplateEditor } from '../components/reminders/TemplateEditor';
import RefreshGate from '../components/reminders/RefreshGate';
import { getStatusDotColor } from '../utils/statusColors';
import { formatCurrency, formatDateTime, formatDuration } from '../utils/formatters';
import { REFETCH_INTERVALS, LIMITS, RETRY_DELAYS, POLLING } from '../constants';
import { toast } from 'sonner';
import type {
  MessageTemplate,
  ReminderSession,
  PartyReminderInfo,
  AntiSpamConfig,
  RefreshStats,
  ReminderBatchReport,
  ReminderBatchRecipient
} from '../types';

// ─── Sub-Components ────────────────────────────────────

function StatCard({ title, value, subtitle, accent }: {
  title: string;
  value: string | number;
  subtitle?: string;
  accent?: boolean;
}) {
  return (
    <div
      className="card p-4"
      style={accent ? { borderColor: 'var(--brand-accent)', borderWidth: '1px' } : {}}
    >
      <p className="text-xs font-medium uppercase tracking-wider" style={{ color: 'var(--text-tertiary)' }}>
        {title}
      </p>
      <p className="text-xl font-bold mt-1" style={{ color: 'var(--text-primary)' }}>
        {value}
      </p>
      {subtitle && (
        <p className="text-xs mt-0.5" style={{ color: 'var(--text-tertiary)' }}>
          {subtitle}
        </p>
      )}
    </div>
  );
}

function SessionPanel({ session, onPause, onResume, onStop }: {
  session: ReminderSession;
  onPause: () => void;
  onResume: () => void;
  onStop: () => void;
}) {
  const dotColor = getStatusDotColor(session.state);

  return (
    <motion.div
      initial={{ opacity: 0, height: 0 }}
      animate={{ opacity: 1, height: 'auto' }}
      exit={{ opacity: 0, height: 0 }}
      className="card p-5 overflow-hidden"
      style={{ borderLeft: `3px solid var(--brand-accent)` }}
    >
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-3">
          <div
            className="w-2.5 h-2.5 rounded-full animate-pulse"
            style={{ backgroundColor: dotColor }}
          />
          <div>
            <p className="text-sm font-semibold" style={{ color: 'var(--text-primary)' }}>
              Session: {session.session_id}
            </p>
            <p className="text-xs capitalize" style={{ color: 'var(--text-tertiary)' }}>
              {session.state}
            </p>
          </div>
        </div>

        <div className="flex gap-2">
          {session.state === 'paused' ? (
            <button onClick={onResume} className="btn-primary text-xs py-1.5 px-3" style={{ background: 'var(--success)' }}>
              <Play className="w-3.5 h-3.5" />
              Resume
            </button>
          ) : (
            <button
              onClick={onPause}
              className="text-xs py-1.5 px-3 rounded-lg flex items-center gap-1.5 font-medium transition-colors"
              style={{
                background: 'var(--warning-soft)',
                color: 'var(--warning)',
                border: '1px solid var(--warning-soft-border)',
              }}
            >
              <Pause className="w-3.5 h-3.5" />
              Pause
            </button>
          )}

          <button onClick={onStop} className="btn-danger text-xs py-1.5 px-3">
            <Square className="w-3.5 h-3.5" />
            Stop
          </button>
        </div>
      </div>

      {/* Progress */}
      <div className="space-y-2">
        <div className="flex justify-between text-xs">
          <span style={{ color: 'var(--text-tertiary)' }}>Progress</span>
          <span style={{ color: 'var(--text-primary)' }}>
            {session.progress.current} / {session.progress.total} ({session.progress.percentage}%)
          </span>
        </div>
        <div className="h-2 rounded-full overflow-hidden" style={{ background: 'var(--bg-input)' }}>
          <div
            className="h-full rounded-full transition-all duration-500"
            style={{
              width: `${session.progress.percentage}%`,
              background: 'linear-gradient(90deg, var(--brand-accent), #818cf8)',
            }}
          />
        </div>
      </div>

      {session.metrics && (
        <div className="flex gap-4 mt-3 text-xs" style={{ color: 'var(--text-tertiary)' }}>
          <span>
            Duration: <strong style={{ color: 'var(--text-secondary)' }}>
              {formatDuration(session.metrics.duration_seconds)}
            </strong>
          </span>
          {session.metrics.avg_delay_seconds && (
            <span>
              Avg Delay: <strong style={{ color: 'var(--text-secondary)' }}>
                {session.metrics.avg_delay_seconds.toFixed(1)}s
              </strong>
            </span>
          )}
          {session.metrics.typing_time_total && (
            <span>
              Typing: <strong style={{ color: 'var(--text-secondary)' }}>
                {session.metrics.typing_time_total.toFixed(0)}s
              </strong>
            </span>
          )}
        </div>
      )}
    </motion.div>
  );
}

function BatchReportPanel({
  report,
  failedOnly,
  onToggleFailedOnly,
  failureStage,
  onFailureStageChange,
}: {
  report: ReminderBatchReport;
  failedOnly: boolean;
  onToggleFailedOnly: (value: boolean) => void;
  failureStage: string;
  onFailureStageChange: (value: string) => void;
}) {
  const summary = report.batch;
  const rows = report.recipients.filter((row: ReminderBatchRecipient) => {
    if (failedOnly && row.status !== 'failed') return false;
    if (failureStage && row.failure_stage !== failureStage) return false;
    return true;
  });

  return (
    <div className="card p-5">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-sm font-semibold" style={{ color: 'var(--text-primary)' }}>
          Batch Report {summary.batch_id}
        </h3>
        <div className="flex items-center gap-2">
          <label className="text-xs flex items-center gap-1">
            <input type="checkbox" checked={failedOnly} onChange={(e) => onToggleFailedOnly(e.target.checked)} />
            Failed only
          </label>
          <select className="input text-xs max-w-[180px]" value={failureStage} onChange={(e) => onFailureStageChange(e.target.value)}>
            <option value="">All stages</option>
            <option value="validation">validation</option>
            <option value="ledger_pdf">ledger_pdf</option>
            <option value="render">render</option>
            <option value="enqueue">enqueue</option>
            <option value="provider_send">provider_send</option>
            <option value="delivery_webhook">delivery_webhook</option>
            <option value="dead_letter">dead_letter</option>
          </select>
        </div>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-5 gap-2 mb-3">
        <StatCard title="Queued" value={summary.queue_success_count} />
        <StatCard title="Queue Failed" value={summary.queue_failed_count} />
        <StatCard title="Delivered" value={summary.delivery_delivered_count} />
        <StatCard title="Read" value={summary.delivery_read_count} />
        <StatCard title="In Flight" value={summary.in_flight_count} />
      </div>

      <div className="max-h-72 overflow-auto rounded-lg border" style={{ borderColor: 'var(--border-default)' }}>
        <table className="w-full text-xs">
          <thead>
            <tr>
              <th className="p-2 text-left">Party</th>
              <th className="p-2 text-left">Phone</th>
              <th className="p-2 text-left">Status</th>
              <th className="p-2 text-left">Failure Stage</th>
              <th className="p-2 text-left">Reason</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row: ReminderBatchRecipient) => (
              <tr key={`${row.batch_id}-${row.party_code}`} className="border-t" style={{ borderColor: 'var(--border-default)' }}>
                <td className="p-2">{row.party_code}</td>
                <td className="p-2">{row.phone || '-'}</td>
                <td className="p-2">{row.status}/{row.delivery_status}</td>
                <td className="p-2">{row.failure_stage || '-'}</td>
                <td className="p-2">{row.failure_code || row.failure_message || '-'}</td>
              </tr>
            ))}
            {rows.length === 0 && (
              <tr>
                <td className="p-3 text-center" colSpan={5}>No records for selected filters.</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

// Toggle switch component
function Toggle({ checked, onChange, label, description }: {
  checked: boolean;
  onChange: (val: boolean) => void;
  label: string;
  description?: string;
}) {
  return (
    <div
      className="flex items-center justify-between p-3 rounded-lg"
      style={{ background: 'var(--bg-input)' }}
    >
      <div className="min-w-0">
        <p className="text-sm font-medium" style={{ color: 'var(--text-primary)' }}>{label}</p>
        {description && (
          <p className="text-xs mt-0.5" style={{ color: 'var(--text-tertiary)' }}>{description}</p>
        )}
      </div>
      <button
        onClick={() => onChange(!checked)}
        className={`toggle ${checked ? 'active' : ''}`}
        role="switch"
        aria-checked={checked}
        aria-label={label}
      />
    </div>
  );
}

// ─── Main Component ────────────────────────────────────

export function Reminders() {
  const queryClient = useQueryClient();
  const [showAntiSpam, setShowAntiSpam] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [filterBy, setFilterBy] = useState('all');
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null);
  const [sessionData, setSessionData] = useState<ReminderSession | null>(null);
  const [activeBatchId, setActiveBatchId] = useState<string | null>(null);
  const [failedOnly, setFailedOnly] = useState(false);
  const [failureStage, setFailureStage] = useState('');
  const [isTemplateEditorOpen, setIsTemplateEditorOpen] = useState(false);
  const [companies, setCompanies] = useState<CompanyInfo[]>([]);
  const activeCompanyId = api.getCompanyId();

  // --- Refresh Gate State ---
  // 'select' = only company selector visible
  // 'gate' = refresh gate overlay (data stale)
  // 'ready' = normal page
  const [pagePhase, setPagePhase] = useState<'select' | 'gate' | 'ready'>('select');
  const [refreshStats, setRefreshStats] = useState<RefreshStats | null>(null);

  // Load available companies
  useEffect(() => {
    api.getCompanies().then(res => setCompanies(res.companies)).catch(console.error);
  }, []);

  // Check refresh stats after companies are loaded to decide phase
  useEffect(() => {
    if (companies.length === 0) return;
    api.getRefreshStats()
      .then((stats) => {
        setRefreshStats(stats);
        const lastRefresh = stats.last_refresh_at;
        if (!lastRefresh) {
          // Never refreshed — go to gate
          setPagePhase('gate');
          return;
        }
        const ageMs = Date.now() - new Date(lastRefresh).getTime();
        const ONE_HOUR = 60 * 60 * 1000;
        if (ageMs > ONE_HOUR) {
          setPagePhase('gate');
        } else {
          setPagePhase('ready');
        }
      })
      .catch(() => {
        // If we can't fetch stats, go straight to ready (graceful degradation)
        setPagePhase('ready');
      });
  }, [companies, activeCompanyId]);

  // Store - use individual selectors to prevent infinite re-renders
  const setConfig = useRemindersStore((state) => state.setConfig);
  const setTemplates = useRemindersStore((state) => state.setTemplates);
  const setStats = useRemindersStore((state) => state.setStats);
  const setSnapshotStatus = useRemindersStore((state) => state.setSnapshotStatus);
  const setParties = useRemindersStore((state) => state.setParties);
  const setDefaultTemplateId = useRemindersStore((state) => state.setDefaultTemplateId);
  const setPersistedSelection = useRemindersStore((state) => state.setPersistedSelection);
  const selectParties = useRemindersStore((state) => state.selectParties);
  const setPartyTemplate = useRemindersStore((state) => state.setPartyTemplate);
  const clearPartyTemplate = useRemindersStore((state) => state.clearPartyTemplate);
  const defaultTemplateId = useRemindersStore((state) => state.defaultTemplateId);
  const selectedPartyCodes = useRemindersStore((state) => state.selectedPartyCodes);
  const togglePartySelection = useRemindersStore((state) => state.togglePartySelection);
  const setAntiSpamConfig = useRemindersStore((state) => state.setAntiSpamConfig);
  const antiSpamConfig = useRemindersStore((state) => state.antiSpamConfig);
  const parties = useRemindersStore((state) => state.parties);
  const partyTemplates = useRemindersStore((state) => state.partyTemplates);

  // Queries
  const { data: config, isLoading: configLoading } = useQuery({
    queryKey: ['reminder-config'],
    queryFn: () => api.getReminderConfig(),
  });

  const { data: templates, isLoading: templatesLoading } = useQuery({
    queryKey: ['reminder-templates'],
    queryFn: () => api.getTemplates(),
  });

  const { data: stats, isLoading: statsLoading } = useQuery({
    queryKey: ['reminder-stats'],
    queryFn: () => api.getReminderStats(),
    refetchInterval: REFETCH_INTERVALS.REMINDER_STATS,
  });

  const { data: snapshotStatus, isLoading: snapshotLoading } = useQuery({
    queryKey: ['reminder-snapshot'],
    queryFn: () => api.getReminderSnapshotStatus(),
  });

  const { data: partiesData, isLoading: partiesLoading, isFetching: partiesFetching } = useQuery({
    queryKey: ['reminder-parties', filterBy, searchQuery],
    queryFn: () => api.getEligibleParties({
      filter_by: filterBy,
      search: searchQuery,
      limit: LIMITS.MAX_PAGE_SIZE,
    }),
    placeholderData: keepPreviousData,
  });

  const { data: batchReport } = useQuery({
    queryKey: ['reminder-batch-report', activeBatchId],
    queryFn: () => api.getBatchReport(activeBatchId!),
    enabled: !!activeBatchId,
    refetchInterval: POLLING.SESSION_INTERVAL,
  });

  useEffect(() => {
    if (config) setConfig(config);
    if (templates) {
      setTemplates(templates);
      const activeTemplate = templates.find((t: MessageTemplate) => t.is_default);
      if (activeTemplate && !defaultTemplateId) {
        setDefaultTemplateId(activeTemplate.id);
      }
    }
    if (stats) setStats(stats);
    if (snapshotStatus) setSnapshotStatus(snapshotStatus);
    if (partiesData) {
      setParties(partiesData.items);
      const persisted: Record<string, boolean> = {};
      partiesData.items.forEach((p: PartyReminderInfo) => {
        if (p.permanent_enabled) {
          persisted[p.code] = true;
        }
      });
      if (Object.keys(persisted).length > 0) {
        setPersistedSelection(persisted);
        const enabledCodes = Object.keys(persisted).filter(code => persisted[code]);
        if (enabledCodes.length > 0) {
          selectParties(enabledCodes);
        }
      }
    }
  }, [config, templates, stats, snapshotStatus, partiesData, setConfig, setTemplates, setStats, setSnapshotStatus, setParties, setDefaultTemplateId, defaultTemplateId, setPersistedSelection, selectParties]);

  // Session polling
  const sessionTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    if (!activeSessionId) return;

    const abortController = new AbortController();
    let isActive = true;

    const pollSession = async () => {
      try {
        const status = await api.getSessionStatus(activeSessionId, abortController.signal);
        if (!isActive) return;

        if (status) {
          setSessionData(status);
          if (status.batch_id) {
            setActiveBatchId(status.batch_id);
          }
          if (['completed', 'stopped', 'error'].includes(status.state)) {
            sessionTimeoutRef.current = setTimeout(() => {
              if (isActive) {
                setActiveSessionId(null);
                setSessionData(null);
              }
            }, RETRY_DELAYS.SESSION_CLEANUP);
          }
        }
      } catch (error) {
        if (!isActive) return;
        const isCanceled = axios.isCancel?.(error) ||
          (error instanceof Error && error.name === 'AbortError');
        if (!isCanceled) {
          console.error('Session polling error:', error);
        }
        setActiveSessionId(null);
        setSessionData(null);
      }
    };

    const interval = setInterval(pollSession, POLLING.SESSION_INTERVAL);
    pollSession();

    return () => {
      isActive = false;
      abortController.abort();
      clearInterval(interval);
      if (sessionTimeoutRef.current) {
        clearTimeout(sessionTimeoutRef.current);
        sessionTimeoutRef.current = null;
      }
    };
  }, [activeSessionId]);

  // Mutations
  const refreshSnapshotMutation = useMutation({
    mutationFn: () => api.refreshReminderSnapshot(),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['reminder-snapshot'] });
      queryClient.invalidateQueries({ queryKey: ['reminder-stats'] });
      queryClient.invalidateQueries({ queryKey: ['reminder-parties'] });
      toast.success('Data refreshed successfully');
    },
    onError: (error: Error) => {
      toast.error(`Failed to refresh data: ${error.message}`);
    },
  });

  const sendRemindersMutation = useMutation({
    mutationFn: (data: { partyCodes: string[]; templateId: string; partyTemplates?: Record<string, string> }) =>
      api.sendReminders(data.partyCodes, data.templateId, data.partyTemplates),
    onSuccess: (data) => {
      if (data.session_id) {
        setActiveSessionId(data.session_id);
      }
      if (data.batch_id) {
        setActiveBatchId(data.batch_id);
      }
      toast.success('Reminders queued successfully');
    },
    onError: (error: Error) => {
      toast.error(`Failed to send reminders: ${error.message}`);
    },
  });

  const updateAntiSpamMutation = useMutation({
    mutationFn: (config: AntiSpamConfig) => api.updateAntiSpamConfig(config),
    onSuccess: () => {
      toast.success('Anti-spam settings updated');
    },
    onError: (error: Error) => {
      toast.error(`Failed to update anti-spam settings: ${error.message}`);
    },
  });

  const handleToggleSelection = useCallback((code: string) => {
    togglePartySelection(code);
  }, [togglePartySelection]);

  const handleOpenLedger = useCallback(async (partyCode: string) => {
    try {
      const blob = await api.generateLedgerPdf(partyCode);
      const objectUrl = URL.createObjectURL(blob);
      window.open(objectUrl, '_blank', 'noopener,noreferrer');
      window.setTimeout(() => URL.revokeObjectURL(objectUrl), 30_000);
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Unable to open ledger PDF';
      toast.error(message);
    }
  }, []);

  const getEffectivePartyTemplate = useCallback((partyCode: string) => {
    if (Object.prototype.hasOwnProperty.call(partyTemplates, partyCode)) {
      return partyTemplates[partyCode];
    }
    return config?.parties?.[partyCode]?.custom_template_id || '';
  }, [partyTemplates, config]);

  const handleTemplateOverrideChange = useCallback((partyCode: string, templateId: string) => {
    if (templateId === '__inherit__') {
      clearPartyTemplate(partyCode);
      return;
    }
    setPartyTemplate(partyCode, templateId);
  }, [clearPartyTemplate, setPartyTemplate]);

  const selectedParties = useMemo(() =>
    parties.filter((p) => selectedPartyCodes.has(p.code)),
    [parties, selectedPartyCodes]
  );

  const availableParties = useMemo(() =>
    parties.filter((p) => !selectedPartyCodes.has(p.code)),
    [parties, selectedPartyCodes]
  );

  const handleSendReminders = useCallback(async () => {
    const selectedCodes = Array.from(selectedPartyCodes);
    if (selectedCodes.length === 0 || !defaultTemplateId) return;

    // --- Send-time validation: data freshness ---
    try {
      const stats = await api.getRefreshStats();
      if (!stats.last_refresh_at) {
        toast.error('Data has never been refreshed. Please refresh before sending.');
        return;
      }
      const ageMs = Date.now() - new Date(stats.last_refresh_at).getTime();
      const TWO_HOURS = 2 * 60 * 60 * 1000;
      if (ageMs > TWO_HOURS) {
        const hoursAgo = (ageMs / 3_600_000).toFixed(1);
        toast.error(`Data is ${hoursAgo} hours old. Please refresh before sending.`);
        return;
      }

      // --- Send-time validation: cooldown ---
      if (antiSpamConfig.reminder_cooldown_enabled && stats.last_reminder_sent_at) {
        const sinceMs = Date.now() - new Date(stats.last_reminder_sent_at).getTime();
        const cooldownMs = (antiSpamConfig.reminder_cooldown_minutes || 60) * 60 * 1000;
        if (sinceMs < cooldownMs) {
          const remainingMin = Math.ceil((cooldownMs - sinceMs) / 60_000);
          toast.error(`Cooldown active. Please wait ${remainingMin} more minute${remainingMin !== 1 ? 's' : ''} before sending again.`);
          return;
        }
      }
    } catch {
      // If stats fetch fails, let the backend validate
    }

    const explicitTemplateMap: Record<string, string> = {};
    for (const code of selectedCodes) {
      if (Object.prototype.hasOwnProperty.call(partyTemplates, code)) {
        explicitTemplateMap[code] = partyTemplates[code];
      }
    }

    sendRemindersMutation.mutate({
      partyCodes: selectedCodes,
      templateId: defaultTemplateId,
      partyTemplates: explicitTemplateMap,
    });
  }, [selectedPartyCodes, defaultTemplateId, partyTemplates, sendRemindersMutation, antiSpamConfig]);

  const selectedTotalAmount = useMemo(() =>
    selectedParties.reduce((sum, p) => sum + (Number(p.amount_due) || 0), 0),
    [selectedParties]
  );

  const availableTotalAmount = useMemo(() =>
    availableParties.reduce((sum, p) => sum + (Number(p.amount_due) || 0), 0),
    [availableParties]
  );

  const isLoading = configLoading || templatesLoading || statsLoading || snapshotLoading || partiesLoading;

  // Virtualizer for Selected Parties
  const selectedParentRef = useRef<HTMLDivElement>(null);
  const selectedVirtualizer = useVirtualizer({
    count: selectedParties.length,
    getScrollElement: () => selectedParentRef.current,
    estimateSize: () => 60, // approximate height of each item
    overscan: 5,
  });

  // Virtualizer for Available Parties
  const availableParentRef = useRef<HTMLDivElement>(null);
  const availableVirtualizer = useVirtualizer({
    count: availableParties.length,
    getScrollElement: () => availableParentRef.current,
    estimateSize: () => 60, // approximate height of each item
    overscan: 5,
  });

  if (isLoading && pagePhase === 'ready') {
    return <LoadingState size="lg" fullPage />;
  }

  return (
    <div className="space-y-5">
      {/* Header */}
      {/* Massive Company Context Selector */}
      <div className="bg-white dark:bg-black w-full rounded-2xl border-2 shadow-sm overflow-hidden mb-8" style={{ borderColor: 'var(--brand-accent)' }}>
        <div className="p-4 sm:p-6 text-center" style={{ background: 'var(--brand-soft)' }}>
          <h2 className="text-xs sm:text-sm font-bold uppercase tracking-widest mb-3 sm:mb-4" style={{ color: 'var(--brand-accent)' }}>
            Selected Company Database
          </h2>

          {companies.length > 0 ? (
            <div className="relative max-w-2xl mx-auto">
              <select
                value={activeCompanyId}
                onChange={(e) => { api.setCompanyId(e.target.value); window.location.reload(); }}
                className="w-full appearance-none bg-white dark:bg-black text-xl sm:text-2xl md:text-3xl font-black py-4 sm:py-6 pl-6 sm:pl-8 pr-12 rounded-xl shadow-inner cursor-pointer hover:ring-2 hover:ring-opacity-50 transition-all focus:outline-none focus:ring-4 text-center"
                style={{
                  color: 'var(--text-primary)',
                  border: '2px solid var(--border-default)',
                  '--tw-ring-color': 'var(--brand-accent)'
                } as any}
                title="Switch Active Company"
              >
                {companies.map(c => (
                  <option key={c.id} value={c.id} className="text-lg py-2 font-medium">{c.name}</option>
                ))}
              </select>
              <div className="absolute right-4 sm:right-6 top-1/2 -translate-y-1/2 pointer-events-none">
                <svg className="w-6 h-6 sm:w-8 sm:h-8 opacity-50" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M19 9l-7 7-7-7" />
                </svg>
              </div>
            </div>
          ) : (
            <div className="py-6 px-6 bg-white dark:bg-black w-full max-w-2xl mx-auto rounded-xl border-2 border-dashed" style={{ borderColor: 'var(--border-default)' }}>
              <span className="text-lg sm:text-xl font-bold" style={{ color: 'var(--text-tertiary)' }}>No Companies Configured</span>
              <p className="text-sm mt-2" style={{ color: 'var(--text-tertiary)' }}>Please add a company database in Settings.</p>
            </div>
          )}

          <p className="text-xs sm:text-sm max-w-xl mx-auto mt-4 sm:mt-5 font-medium opacity-80" style={{ color: 'var(--text-secondary)' }}>
            All templates, customers, and reminders below are securely isolated to the selected company. Switching will reload the configuration context.
          </p>
        </div>
      </div>

      {/* Refresh Gate (Phase 2) */}
      {pagePhase === 'gate' && (
        <RefreshGate
          refreshStats={refreshStats}
          onRefreshComplete={() => {
            setPagePhase('ready');
            // Refetch all data now that snapshot is fresh
            api.getRefreshStats().then(setRefreshStats).catch(() => { });
            queryClient.invalidateQueries({ queryKey: ['reminder-snapshot'] });
            queryClient.invalidateQueries({ queryKey: ['reminder-stats'] });
            queryClient.invalidateQueries({ queryKey: ['reminder-parties'] });
            toast.success('Data refreshed successfully');
          }}
          onCancel={() => {
            // Go back to just the company selector
            setPagePhase('select');
          }}
        />
      )}

      {/* Main Content (Phase 3) */}
      {pagePhase === 'ready' && (<>
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <h2 className="text-xl sm:text-2xl font-bold" style={{ color: 'var(--text-primary)' }}>
              Payment Reminders
            </h2>
            <p className="text-xs sm:text-sm mt-0.5" style={{ color: 'var(--text-tertiary)' }}>
              Send reminders with attached ledgers
              {snapshotStatus?.has_snapshot && (
                <span className="hidden sm:inline"> · Last refreshed {formatDateTime(snapshotStatus.last_refreshed_at || null)}</span>
              )}
            </p>
          </div>
          <div className="text-right flex items-center gap-6">
            <div>
              <p className="text-xs" style={{ color: 'var(--text-tertiary)' }}>Selected Total</p>
              <p className="text-lg font-bold" style={{ color: 'var(--success)' }}>{formatCurrency(selectedTotalAmount)}</p>
            </div>
            <div>
              <p className="text-xs" style={{ color: 'var(--text-tertiary)' }}>Remaining Total</p>
              <p className="text-lg font-bold" style={{ color: 'var(--text-primary)' }}>{formatCurrency(availableTotalAmount)}</p>
            </div>

            <button
              onClick={() => refreshSnapshotMutation.mutate()}
              disabled={refreshSnapshotMutation.isPending}
              className="btn-secondary"
            >
              <RefreshCw className={`w-4 h-4 ${refreshSnapshotMutation.isPending && 'animate-spin'}`} />
              Refresh Data
            </button>
          </div>
        </div>

        {/* Stats */}
        < div className="grid grid-cols-2 md:grid-cols-4 gap-3" >
          <StatCard title="Eligible" value={stats?.eligible_parties || 0} />
          <StatCard title="Enabled" value={stats?.enabled_parties || 0} />
          <StatCard
            title="Total Due"
            value={formatCurrency(stats?.total_amount_due || 0)}
          />
          <StatCard
            title="Session"
            value={sessionData ? `${sessionData.progress.percentage}%` : 'Ready'}
            accent={!!sessionData}
          />
        </div >

        {/* Active Session */}
        <AnimatePresence>
          {
            sessionData && (
              <SessionPanel
                session={sessionData}
                onPause={() => activeSessionId && api.pauseSession(activeSessionId)}
                onResume={() => activeSessionId && api.resumeSession(activeSessionId)}
                onStop={() => activeSessionId && api.stopSession(activeSessionId)}
              />
            )
          }
        </AnimatePresence >

        {batchReport && (
          <BatchReportPanel
            report={batchReport}
            failedOnly={failedOnly}
            onToggleFailedOnly={setFailedOnly}
            failureStage={failureStage}
            onFailureStageChange={setFailureStage}
          />
        )}

        {/* Template Selection */}
        < div className="card p-5" >
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2">
              <FileText className="w-4 h-4" style={{ color: 'var(--brand-accent)' }} />
              <h3 className="text-sm font-semibold" style={{ color: 'var(--text-primary)' }}>
                Message Template
              </h3>
            </div>
            <button
              onClick={() => setIsTemplateEditorOpen(true)}
              className="text-xs font-medium px-3 py-1.5 rounded-md transition-colors hover:bg-black/5 dark:hover:bg-white/5"
              style={{ color: 'var(--brand-accent)' }}
            >
              Manage Templates
            </button>
          </div>

          <select
            value={defaultTemplateId}
            onChange={(e) => setDefaultTemplateId(e.target.value)}
            className="input max-w-md"
            aria-label="Select message template"
          >
            <option value="">Select a template...</option>
            {templates?.map((t: MessageTemplate) => (
              <option key={t.id} value={t.id}>{t.name} {t.is_default && '(Default)'}</option>
            ))}
          </select>

          {
            defaultTemplateId && (
              <div
                className="mt-3 p-3 rounded-lg"
                style={{ background: 'var(--bg-input)' }}
              >
                <p className="text-xs mb-1" style={{ color: 'var(--text-tertiary)' }}>Preview:</p>
                <pre
                  className="text-xs whitespace-pre-wrap font-mono"
                  style={{ color: 'var(--text-secondary)' }}
                >
                  {templates?.find((t: MessageTemplate) => t.id === defaultTemplateId)?.content}
                </pre>
              </div>
            )
          }
        </div >

        {/* Anti-Spam Panel */}
        < div className="card overflow-hidden" >
          <button
            onClick={() => setShowAntiSpam(!showAntiSpam)}
            className="w-full flex items-center justify-between p-4 transition-colors"
            style={{ color: 'var(--text-primary)' }}
            onMouseEnter={(e) => (e.currentTarget.style.background = 'var(--bg-input)')}
            onMouseLeave={(e) => (e.currentTarget.style.background = 'transparent')}
          >
            <div className="flex items-center gap-2.5">
              <Shield className="w-4 h-4" style={{ color: 'var(--brand-accent)' }} />
              <div className="text-left">
                <h3 className="text-sm font-semibold">Anti-Spam Protection</h3>
                <p className="text-xs" style={{ color: 'var(--text-tertiary)' }}>
                  {antiSpamConfig.enabled ? 'Enabled' : 'Disabled'}
                </p>
              </div>
            </div>
            {showAntiSpam
              ? <ChevronUp className="w-4 h-4" style={{ color: 'var(--text-tertiary)' }} />
              : <ChevronDown className="w-4 h-4" style={{ color: 'var(--text-tertiary)' }} />
            }
          </button>

          <AnimatePresence>
            {showAntiSpam && (
              <motion.div
                initial={{ height: 0 }}
                animate={{ height: 'auto' }}
                exit={{ height: 0 }}
                className="overflow-hidden border-t"
                style={{ borderColor: 'var(--border-default)' }}
              >
                <div className="p-4 space-y-2">
                  <Toggle
                    checked={antiSpamConfig.enabled}
                    onChange={(val) => {
                      const newConfig = { ...antiSpamConfig, enabled: val };
                      setAntiSpamConfig(newConfig);
                      updateAntiSpamMutation.mutate(newConfig);
                    }}
                    label="Enable Anti-Spam"
                    description="Protect against WhatsApp bulk detection"
                  />

                  {antiSpamConfig.enabled && (
                    <>
                      <Toggle
                        checked={antiSpamConfig.message_inflation}
                        onChange={(val) => {
                          const newConfig = { ...antiSpamConfig, message_inflation: val };
                          setAntiSpamConfig(newConfig);
                          updateAntiSpamMutation.mutate(newConfig);
                        }}
                        label="Message Size Inflation"
                      />
                      <Toggle
                        checked={antiSpamConfig.pdf_inflation}
                        onChange={(val) => {
                          const newConfig = { ...antiSpamConfig, pdf_inflation: val };
                          setAntiSpamConfig(newConfig);
                          updateAntiSpamMutation.mutate(newConfig);
                        }}
                        label="PDF Size Inflation"
                      />
                      <Toggle
                        checked={antiSpamConfig.typing_simulation}
                        onChange={(val) => {
                          const newConfig = { ...antiSpamConfig, typing_simulation: val };
                          setAntiSpamConfig(newConfig);
                          updateAntiSpamMutation.mutate(newConfig);
                        }}
                        label="Human Typing Simulation"
                      />
                      <Toggle
                        checked={antiSpamConfig.startup_delay_enabled}
                        onChange={(val) => {
                          const newConfig = { ...antiSpamConfig, startup_delay_enabled: val };
                          setAntiSpamConfig(newConfig);
                          updateAntiSpamMutation.mutate(newConfig);
                        }}
                        label="Session Startup Delay"
                      />
                      <Toggle
                        checked={antiSpamConfig.reminder_cooldown_enabled}
                        onChange={(val) => {
                          const newConfig = { ...antiSpamConfig, reminder_cooldown_enabled: val };
                          setAntiSpamConfig(newConfig);
                          updateAntiSpamMutation.mutate(newConfig);
                        }}
                        label="Send Cooldown"
                        description={`Prevent re-sending within ${antiSpamConfig.reminder_cooldown_minutes || 60} minutes`}
                      />
                    </>
                  )}
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </div >

        {/* Party Selection */}
        < div className="grid grid-cols-1 lg:grid-cols-2 gap-5" >
          {/* Selected Parties */}
          < div className="card overflow-hidden" >
            <div
              className="p-4 border-b flex items-center justify-between"
              style={{ borderColor: 'var(--border-default)' }}
            >
              <div className="flex items-center gap-2">
                <CheckCircle className="w-4 h-4" style={{ color: 'var(--success)' }} />
                <h3 className="text-sm font-semibold" style={{ color: 'var(--text-primary)' }}>
                  Selected
                </h3>
                <span
                  className="text-xs font-semibold px-2 py-0.5 rounded-full"
                  style={{ background: 'var(--brand-accent)', color: 'white' }}
                >
                  {selectedParties.length}
                </span>
              </div>
            </div>

            <div className="p-4">
              {selectedParties.length === 0 ? (
                <div className="text-center py-10" style={{ color: 'var(--text-tertiary)' }}>
                  <Users className="w-10 h-10 mx-auto mb-2 opacity-40" />
                  <p className="text-sm">No parties selected</p>
                </div>
              ) : (
                <>
                  <div ref={selectedParentRef} className="max-h-80 overflow-y-auto w-full">
                    <div
                      style={{
                        height: `${selectedVirtualizer.getTotalSize()}px`,
                        width: '100%',
                        position: 'relative',
                      }}
                    >
                      {selectedVirtualizer.getVirtualItems().map((virtualItem: any) => {
                        const party = selectedParties[virtualItem.index];
                        return (
                          <div
                            key={party.code}
                            className="flex items-center justify-between p-2.5 rounded-lg group absolute top-0 left-0 w-full"
                            style={{
                              height: `${virtualItem.size - 6}px`, // -6px for gap accounting
                              transform: `translateY(${virtualItem.start}px)`,
                              background: 'var(--bg-input)'
                            }}
                          >
                            <div className="flex items-center gap-3 min-w-0 pr-4">
                              <button
                                onClick={() => handleToggleSelection(party.code)}
                                className="p-1.5 rounded-md transition-colors opacity-60 hover:opacity-100 flex-shrink-0"
                                style={{ color: 'var(--danger)' }}
                                onMouseEnter={(e) => (e.currentTarget.style.background = 'var(--danger-soft)')}
                                onMouseLeave={(e) => (e.currentTarget.style.background = 'transparent')}
                                aria-label={`Remove ${party.name}`}
                              >
                                <X className="w-3.5 h-3.5" />
                              </button>
                              <button
                                type="button"
                                onClick={() => handleOpenLedger(party.code)}
                                className="text-sm font-medium truncate text-left hover:underline"
                                style={{ color: 'var(--text-primary)' }}
                                title="Open ledger PDF in new tab"
                              >
                                {party.name}
                              </button>
                            </div>

                            <div className="flex items-center gap-2 flex-shrink-0">
                              <select
                                value={getEffectivePartyTemplate(party.code)}
                                onChange={(e) => handleTemplateOverrideChange(party.code, e.target.value)}
                                className="input text-xs py-1 px-2 w-40"
                                aria-label={`Template override for ${party.name}`}
                              >
                                <option value="__inherit__">Use saved/default</option>
                                <option value="">Use batch default</option>
                                {templates?.map((t: MessageTemplate) => (
                                  <option key={t.id} value={t.id}>{t.name}</option>
                                ))}
                              </select>
                              <button
                                type="button"
                                onClick={() => handleOpenLedger(party.code)}
                                className="p-1.5 rounded-md hover:bg-black/5 dark:hover:bg-white/5"
                                aria-label={`Open ledger for ${party.name}`}
                                title="Open ledger PDF"
                              >
                                <ExternalLink className="w-3.5 h-3.5" />
                              </button>
                              <p className="text-sm font-medium text-right min-w-20" style={{ color: 'var(--text-primary)' }}>
                                {formatCurrency(party.amount_due)}
                              </p>
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                </>
              )}
            </div>
          </div >

          {/* Available Parties */}
          < div className="card overflow-hidden" >
            <div
              className="p-4 border-b space-y-3"
              style={{ borderColor: 'var(--border-default)' }}
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Users className="w-4 h-4" style={{ color: 'var(--text-tertiary)' }} />
                  <h3 className="text-sm font-semibold" style={{ color: 'var(--text-primary)' }}>
                    Available
                  </h3>
                  <span
                    className="text-xs font-medium px-2 py-0.5 rounded-full"
                    style={{
                      background: 'var(--bg-input)',
                      color: 'var(--text-secondary)',
                    }}
                  >
                    {availableParties.length}
                  </span>
                </div>
              </div>

              <div className="flex gap-2">
                <div className="relative flex-1">
                  <label htmlFor="party-search" className="sr-only">
                    Search parties
                  </label>
                  <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4" style={{ color: 'var(--text-tertiary)' }} aria-hidden="true" />
                  <input
                    id="party-search"
                    type="text"
                    placeholder="Search parties..."
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    className="input pl-9 pr-9"
                    aria-label="Search for parties by name or code"
                  />
                  <AnimatePresence>
                    {partiesFetching && (
                      <motion.div
                        initial={{ opacity: 0, scale: 0.8 }}
                        animate={{ opacity: 1, scale: 1 }}
                        exit={{ opacity: 0, scale: 0.8 }}
                        className="absolute right-3 top-1/2 -translate-y-1/2"
                      >
                        <Loader2 className="w-4 h-4 animate-spin" style={{ color: 'var(--brand-accent)' }} />
                      </motion.div>
                    )}
                  </AnimatePresence>
                </div>

                <select
                  value={filterBy}
                  onChange={(e) => setFilterBy(e.target.value)}
                  className="input w-auto"
                  aria-label="Filter parties by status"
                >
                  <option value="all">All</option>
                  <option value="enabled">Enabled</option>
                  <option value="recent">Not Recent</option>
                </select>
              </div>
            </div>

            <div className="p-4">
              <div ref={availableParentRef} className="max-h-80 overflow-y-auto w-full">
                {availableParties.length > 0 && (
                  <div
                    style={{
                      height: `${availableVirtualizer.getTotalSize()}px`,
                      width: '100%',
                      position: 'relative',
                    }}
                  >
                    {availableVirtualizer.getVirtualItems().map((virtualItem: any) => {
                      const party = availableParties[virtualItem.index];
                      return (
                        <div
                          key={party.code}
                          onClick={() => handleToggleSelection(party.code)}
                          role="button"
                          tabIndex={0}
                          onKeyDown={(e) => {
                            if (e.key === 'Enter' || e.key === ' ') {
                              e.preventDefault();
                              handleToggleSelection(party.code);
                            }
                          }}
                          className="w-full flex items-center justify-between p-2.5 rounded-lg transition-colors text-left absolute top-0 left-0 cursor-pointer"
                          style={{
                            height: `${virtualItem.size - 6}px`, // gap accounting
                            transform: `translateY(${virtualItem.start}px)`,
                            background: 'var(--bg-input)'
                          }}
                          onMouseEnter={(e) => {
                            e.currentTarget.style.background = 'var(--bg-input-hover)';
                            const checkbox = e.currentTarget.querySelector('.party-checkbox') as HTMLDivElement;
                            if (checkbox) checkbox.style.borderColor = 'var(--text-primary)';
                          }}
                          onMouseLeave={(e) => {
                            e.currentTarget.style.background = 'var(--bg-input)';
                            const checkbox = e.currentTarget.querySelector('.party-checkbox') as HTMLDivElement;
                            if (checkbox) checkbox.style.borderColor = 'var(--border-strong)';
                          }}
                          aria-label={`Select ${party.name} with amount due ${formatCurrency(party.amount_due)}`}
                        >
                          <div className="flex items-center gap-3 min-w-0 pr-4">
                            <div
                              className="party-checkbox w-4 h-4 border-2 rounded flex items-center justify-center flex-shrink-0 transition-colors"
                              style={{ borderColor: 'var(--border-strong)' }}
                              aria-hidden="true"
                            />
                            <button
                              type="button"
                              onClick={(e) => {
                                e.stopPropagation();
                                handleOpenLedger(party.code);
                              }}
                              className="text-sm font-medium truncate text-left hover:underline"
                              style={{ color: 'var(--text-primary)' }}
                              title="Open ledger PDF in new tab"
                            >
                              {party.name}
                            </button>
                          </div>

                          <div className="flex items-center gap-2 flex-shrink-0">
                            <select
                              value={getEffectivePartyTemplate(party.code)}
                              onClick={(e) => e.stopPropagation()}
                              onChange={(e) => handleTemplateOverrideChange(party.code, e.target.value)}
                              className="input text-xs py-1 px-2 w-40"
                              aria-label={`Template override for ${party.name}`}
                            >
                              <option value="__inherit__">Use saved/default</option>
                              <option value="">Use batch default</option>
                              {templates?.map((t: MessageTemplate) => (
                                <option key={t.id} value={t.id}>{t.name}</option>
                              ))}
                            </select>
                            <button
                              type="button"
                              onClick={(e) => {
                                e.stopPropagation();
                                handleOpenLedger(party.code);
                              }}
                              className="p-1.5 rounded-md hover:bg-black/5 dark:hover:bg-white/5"
                              aria-label={`Open ledger for ${party.name}`}
                              title="Open ledger PDF"
                            >
                              <ExternalLink className="w-3.5 h-3.5" />
                            </button>
                            <p className="text-sm font-medium text-right min-w-20" style={{ color: 'var(--text-primary)' }}>
                              {formatCurrency(party.amount_due)}
                            </p>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                )}

                {availableParties.length === 0 && (
                  <div className="text-center py-10" style={{ color: 'var(--text-tertiary)' }}>
                    <p className="text-sm">No parties available</p>
                  </div>
                )}
              </div>
            </div>
          </div >
        </div >

        {/* Sticky Action Bar */}
        < div
          className="sticky bottom-4 rounded-xl p-4 backdrop-blur-xl"
          style={{
            background: 'var(--bg-sidebar)',
            border: '1px solid var(--border-default)',
            boxShadow: '0 -4px 20px rgba(0, 0, 0, 0.08)',
          }
          }
        >
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-5">
              <div>
                <span className="text-xs" style={{ color: 'var(--text-tertiary)' }}>Selected: </span>
                <span className="text-sm font-bold" style={{ color: 'var(--text-primary)' }}>
                  {selectedParties.length}
                </span>
              </div>

              <div>
                <span className="text-xs" style={{ color: 'var(--text-tertiary)' }}>Total: </span>
                <span className="text-sm font-bold" style={{ color: 'var(--brand-accent)' }}>
                  {formatCurrency(selectedTotalAmount)}
                </span>
              </div>
            </div>

            <div className="flex items-center gap-2">
              <button
                onClick={() => {
                  const csv = [
                    ['Name', 'Phone', 'Amount Due'].join(','),
                    ...selectedParties.map(p => [p.name, p.phone || '', p.amount_due].join(',')),
                  ].join('\n');
                  const blob = new Blob([csv], { type: 'text/csv' });
                  const url = URL.createObjectURL(blob);
                  const a = document.createElement('a');
                  a.href = url;
                  a.download = 'selected-parties.csv';
                  a.click();
                }}
                disabled={selectedParties.length === 0}
                className="btn-secondary text-xs"
              >
                <Download className="w-3.5 h-3.5" />
                Export
              </button>

              <button
                onClick={handleSendReminders}
                disabled={selectedParties.length === 0 || !defaultTemplateId || sendRemindersMutation.isPending || activeSessionId !== null}
                className="btn-primary"
              >
                {sendRemindersMutation.isPending ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    Sending...
                  </>
                ) : (
                  <>
                    <Send className="w-4 h-4" />
                    Send Reminders
                  </>
                )}
              </button>
            </div>
          </div>
        </div>

        <TemplateEditor
          isOpen={isTemplateEditorOpen}
          onClose={() => setIsTemplateEditorOpen(false)}
          activeCompanyId={activeCompanyId}
        />
      </>)}
    </div>
  );
}

import { useState, useEffect, useMemo, useCallback, useRef } from 'react';
import axios from 'axios';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
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
  CheckSquare,
} from 'lucide-react';
import { api } from '../services/api';
import { useRemindersStore } from '../stores/remindersStore';
import { LoadingState } from '../components/ui/LoadingState';
import { getStatusDotColor } from '../utils/statusColors';
import { formatCurrency, formatDateTime, formatDuration } from '../utils/formatters';
import { REFETCH_INTERVALS, LIMITS, RETRY_DELAYS, POLLING } from '../constants';
import { toast } from 'sonner';
import type { MessageTemplate, ReminderSession, PartyReminderInfo } from '../types';

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

  // Store
  const store = useRemindersStore();
  const { setConfig, setTemplates, setStats, setSnapshotStatus, setParties } = store;

  // Queries
  const { data: config, isLoading: configLoading } = useQuery({
    queryKey: ['reminder-config'],
    queryFn: api.getReminderConfig,
  });

  const { data: templates, isLoading: templatesLoading } = useQuery({
    queryKey: ['reminder-templates'],
    queryFn: api.getTemplates,
  });

  const { data: stats, isLoading: statsLoading } = useQuery({
    queryKey: ['reminder-stats'],
    queryFn: api.getReminderStats,
    refetchInterval: REFETCH_INTERVALS.REMINDER_STATS,
  });

  const { data: snapshotStatus, isLoading: snapshotLoading } = useQuery({
    queryKey: ['reminder-snapshot'],
    queryFn: api.getReminderSnapshotStatus,
  });

  const { data: partiesData, isLoading: partiesLoading } = useQuery({
    queryKey: ['reminder-parties', filterBy, searchQuery],
    queryFn: () => api.getEligibleParties({
      filter_by: filterBy,
      search: searchQuery,
      limit: LIMITS.MAX_PAGE_SIZE,
    }),
  });

  useEffect(() => {
    if (config) setConfig(config);
    if (templates) {
      setTemplates(templates);
      const activeTemplate = templates.find((t: MessageTemplate) => t.is_default);
      if (activeTemplate && !store.defaultTemplateId) {
        store.setDefaultTemplateId(activeTemplate.id);
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
        store.setPersistedSelection(persisted);
        const enabledCodes = Object.keys(persisted).filter(code => persisted[code]);
        if (enabledCodes.length > 0) {
          store.selectParties(enabledCodes);
        }
      }
    }
  }, [config, templates, stats, snapshotStatus, partiesData, setConfig, setTemplates, setStats, setSnapshotStatus, setParties, store]);

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
    mutationFn: api.refreshReminderSnapshot,
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
      toast.success('Reminders queued successfully');
    },
    onError: (error: Error) => {
      toast.error(`Failed to send reminders: ${error.message}`);
    },
  });

  const updateAntiSpamMutation = useMutation({
    mutationFn: api.updateAntiSpamConfig,
    onSuccess: () => {
      toast.success('Anti-spam settings updated');
    },
    onError: (error: Error) => {
      toast.error(`Failed to update anti-spam settings: ${error.message}`);
    },
  });

  const handleToggleSelection = useCallback((code: string) => {
    store.togglePartySelection(code);
  }, [store]);

  const handleSelectAll = useCallback(() => {
    const allAvailableCodes = availableParties.map(p => p.code);
    allAvailableCodes.forEach(code => {
      if (!store.selectedPartyCodes.has(code)) {
        store.togglePartySelection(code);
      }
    });
  }, [store]);

  const handleSendReminders = useCallback(() => {
    const selectedCodes = Array.from(store.selectedPartyCodes);
    if (selectedCodes.length === 0 || !store.defaultTemplateId) return;

    sendRemindersMutation.mutate({
      partyCodes: selectedCodes,
      templateId: store.defaultTemplateId,
      partyTemplates: store.partyTemplates,
    });
  }, [store, sendRemindersMutation]);

  const selectedParties = useMemo(() =>
    store.parties.filter((p) => store.selectedPartyCodes.has(p.code)),
    [store.parties, store.selectedPartyCodes]
  );

  const availableParties = useMemo(() =>
    store.parties.filter((p) => !store.selectedPartyCodes.has(p.code)),
    [store.parties, store.selectedPartyCodes]
  );

  const selectedTotalAmount = useMemo(() =>
    selectedParties.reduce((sum, p) => sum + (p.amount_due || 0), 0),
    [selectedParties]
  );

  const isLoading = configLoading || templatesLoading || statsLoading || snapshotLoading || partiesLoading;

  if (isLoading) {
    return <LoadingState size="lg" fullPage />;
  }

  return (
    <div className="space-y-5">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold" style={{ color: 'var(--text-primary)' }}>
            Payment Reminders
          </h2>
          <p className="text-sm mt-0.5" style={{ color: 'var(--text-tertiary)' }}>
            Send reminders with attached ledgers
            {snapshotStatus?.has_snapshot && (
              <> · Last refreshed {formatDateTime(snapshotStatus.last_refreshed_at || null)}</>
            )}
          </p>
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

      {/* Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
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
      </div>

      {/* Active Session */}
      <AnimatePresence>
        {sessionData && (
          <SessionPanel
            session={sessionData}
            onPause={() => activeSessionId && api.pauseSession(activeSessionId)}
            onResume={() => activeSessionId && api.resumeSession(activeSessionId)}
            onStop={() => activeSessionId && api.stopSession(activeSessionId)}
          />
        )}
      </AnimatePresence>

      {/* Template Selection */}
      <div className="card p-5">
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            <FileText className="w-4 h-4" style={{ color: 'var(--brand-accent)' }} />
            <h3 className="text-sm font-semibold" style={{ color: 'var(--text-primary)' }}>
              Message Template
            </h3>
          </div>
          <button
            onClick={() => window.open('/api/v1/reminders/templates', '_blank')}
            className="text-xs font-medium"
            style={{ color: 'var(--brand-accent)' }}
          >
            Manage Templates
          </button>
        </div>

        <select
          value={store.defaultTemplateId}
          onChange={(e) => store.setDefaultTemplateId(e.target.value)}
          className="input max-w-md"
          aria-label="Select message template"
        >
          <option value="">Select a template...</option>
          {templates?.map((t: MessageTemplate) => (
            <option key={t.id} value={t.id}>{t.name} {t.is_default && '(Default)'}</option>
          ))}
        </select>

        {store.defaultTemplateId && (
          <div
            className="mt-3 p-3 rounded-lg"
            style={{ background: 'var(--bg-input)' }}
          >
            <p className="text-xs mb-1" style={{ color: 'var(--text-tertiary)' }}>Preview:</p>
            <pre
              className="text-xs whitespace-pre-wrap font-mono"
              style={{ color: 'var(--text-secondary)' }}
            >
              {templates?.find((t: MessageTemplate) => t.id === store.defaultTemplateId)?.content}
            </pre>
          </div>
        )}
      </div>

      {/* Anti-Spam Panel */}
      <div className="card overflow-hidden">
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
                {store.antiSpamConfig.enabled ? 'Enabled' : 'Disabled'}
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
                  checked={store.antiSpamConfig.enabled}
                  onChange={(val) => {
                    const newConfig = { ...store.antiSpamConfig, enabled: val };
                    store.setAntiSpamConfig(newConfig);
                    updateAntiSpamMutation.mutate(newConfig);
                  }}
                  label="Enable Anti-Spam"
                  description="Protect against WhatsApp bulk detection"
                />

                {store.antiSpamConfig.enabled && (
                  <>
                    <Toggle
                      checked={store.antiSpamConfig.message_inflation}
                      onChange={(val) => {
                        const newConfig = { ...store.antiSpamConfig, message_inflation: val };
                        store.setAntiSpamConfig(newConfig);
                        updateAntiSpamMutation.mutate(newConfig);
                      }}
                      label="Message Size Inflation"
                    />
                    <Toggle
                      checked={store.antiSpamConfig.pdf_inflation}
                      onChange={(val) => {
                        const newConfig = { ...store.antiSpamConfig, pdf_inflation: val };
                        store.setAntiSpamConfig(newConfig);
                        updateAntiSpamMutation.mutate(newConfig);
                      }}
                      label="PDF Size Inflation"
                    />
                    <Toggle
                      checked={store.antiSpamConfig.typing_simulation}
                      onChange={(val) => {
                        const newConfig = { ...store.antiSpamConfig, typing_simulation: val };
                        store.setAntiSpamConfig(newConfig);
                        updateAntiSpamMutation.mutate(newConfig);
                      }}
                      label="Human Typing Simulation"
                    />
                    <Toggle
                      checked={store.antiSpamConfig.startup_delay_enabled}
                      onChange={(val) => {
                        const newConfig = { ...store.antiSpamConfig, startup_delay_enabled: val };
                        store.setAntiSpamConfig(newConfig);
                        updateAntiSpamMutation.mutate(newConfig);
                      }}
                      label="Session Startup Delay"
                    />
                  </>
                )}
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      {/* Party Selection */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
        {/* Selected Parties */}
        <div className="card overflow-hidden">
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
            <span className="text-sm font-semibold" style={{ color: 'var(--brand-accent)' }}>
              {formatCurrency(selectedTotalAmount)}
            </span>
          </div>

          <div className="p-4">
            {selectedParties.length === 0 ? (
              <div className="text-center py-10" style={{ color: 'var(--text-tertiary)' }}>
                <Users className="w-10 h-10 mx-auto mb-2 opacity-40" />
                <p className="text-sm">No parties selected</p>
              </div>
            ) : (
              <>
                <div className="space-y-1.5 max-h-80 overflow-y-auto">
                  {selectedParties.map((party) => (
                    <div
                      key={party.code}
                      className="flex items-center justify-between p-2.5 rounded-lg group"
                      style={{ background: 'var(--bg-input)' }}
                    >
                      <div className="min-w-0">
                        <p className="text-sm font-medium truncate" style={{ color: 'var(--text-primary)' }}>
                          {party.name}
                        </p>
                        <p className="text-xs" style={{ color: 'var(--text-tertiary)' }}>
                          {party.code} · {formatCurrency(party.amount_due)}
                        </p>
                      </div>

                      <button
                        onClick={() => handleToggleSelection(party.code)}
                        className="p-1.5 rounded-md transition-colors opacity-60 hover:opacity-100"
                        style={{ color: 'var(--danger)' }}
                        onMouseEnter={(e) => (e.currentTarget.style.background = 'var(--danger-soft)')}
                        onMouseLeave={(e) => (e.currentTarget.style.background = 'transparent')}
                      >
                        <X className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  ))}
                </div>

                <button
                  onClick={() => store.clearSelection()}
                  className="mt-3 w-full py-2 text-xs font-medium rounded-lg transition-colors"
                  style={{ color: 'var(--danger)' }}
                  onMouseEnter={(e) => (e.currentTarget.style.background = 'var(--danger-soft)')}
                  onMouseLeave={(e) => (e.currentTarget.style.background = 'transparent')}
                >
                  Clear All
                </button>
              </>
            )}
          </div>
        </div>

        {/* Available Parties */}
        <div className="card overflow-hidden">
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
              {availableParties.length > 0 && (
                <button
                  onClick={handleSelectAll}
                  className="flex items-center gap-1 text-xs font-medium"
                  style={{ color: 'var(--brand-accent)' }}
                >
                  <CheckSquare className="w-3.5 h-3.5" />
                  Select All
                </button>
              )}
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
                  className="input pl-9"
                  aria-label="Search for parties by name or code"
                />
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
            <div className="space-y-1.5 max-h-80 overflow-y-auto">
              {availableParties.map((party) => (
                <button
                  key={party.code}
                  onClick={() => handleToggleSelection(party.code)}
                  className="w-full flex items-center justify-between p-2.5 rounded-lg transition-colors text-left"
                  style={{ background: 'var(--bg-input)' }}
                  onMouseEnter={(e) => (e.currentTarget.style.background = 'var(--bg-input-hover)')}
                  onMouseLeave={(e) => (e.currentTarget.style.background = 'var(--bg-input)')}
                  aria-label={`Select ${party.name} (${party.code}) with amount due ${formatCurrency(party.amount_due)}`}
                >
                  <div className="min-w-0">
                    <p className="text-sm font-medium truncate" style={{ color: 'var(--text-primary)' }}>
                      {party.name}
                    </p>
                    <p className="text-xs" style={{ color: 'var(--text-tertiary)' }}>
                      {party.code} · {formatCurrency(party.amount_due)}
                    </p>
                  </div>

                  <div
                    className="w-4 h-4 border-2 rounded flex items-center justify-center flex-shrink-0"
                    style={{ borderColor: 'var(--border-strong)' }}
                    aria-hidden="true"
                  />
                </button>
              ))}

              {availableParties.length === 0 && (
                <div className="text-center py-10" style={{ color: 'var(--text-tertiary)' }}>
                  <p className="text-sm">No parties available</p>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Sticky Action Bar */}
      <div
        className="sticky bottom-4 rounded-xl p-4 backdrop-blur-xl"
        style={{
          background: 'var(--bg-sidebar)',
          border: '1px solid var(--border-default)',
          boxShadow: '0 -4px 20px rgba(0, 0, 0, 0.08)',
        }}
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
                  ['Code', 'Name', 'Phone', 'Amount Due'].join(','),
                  ...selectedParties.map(p => [p.code, p.name, p.phone || '', p.amount_due].join(',')),
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
              disabled={selectedParties.length === 0 || !store.defaultTemplateId || sendRemindersMutation.isPending || activeSessionId !== null}
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
    </div>
  );
}

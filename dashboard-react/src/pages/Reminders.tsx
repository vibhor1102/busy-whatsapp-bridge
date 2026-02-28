import { useState, useEffect, useMemo } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  RefreshCw, 
  Send, 
  Pause, 
  Play, 
  Square,
  Loader2,
  ChevronDown,
  ChevronUp,
  Users,
  Shield,
  FileText,
  Download,
  CheckCircle,
  Search,
  X
} from 'lucide-react';
import { api } from '../services/api';
import { useRemindersStore } from '../stores/remindersStore';
import type { MessageTemplate } from '../types';

// Utility functions
const formatCurrency = (amount: number, symbol = '₹') => {
  return `${symbol}${new Intl.NumberFormat('en-IN', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(amount)}`;
};

const formatDateTime = (dt: string | null) => {
  if (!dt) return 'Never';
  return new Date(dt).toLocaleString('en-IN', {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
};

const formatDuration = (seconds: number) => {
  if (seconds < 60) return `${seconds}s`;
  const mins = Math.floor(seconds / 60);
  const secs = seconds % 60;
  if (mins < 60) return `${mins}m ${secs}s`;
  const hours = Math.floor(mins / 60);
  const remainingMins = mins % 60;
  return `${hours}h ${remainingMins}m`;
};

// Components
function StatCard({ title, value, subtitle }: { title: string; value: string | number; subtitle?: string }) {
  return (
    <div className="bg-dark-800 border border-slate-700 rounded-xl p-4">
      <p className="text-sm text-slate-400">{title}</p>
      <p className="text-2xl font-bold text-slate-100 mt-1">{value}</p>
      {subtitle && <p className="text-sm text-slate-500 mt-1">{subtitle}</p>}
    </div>
  );
}

function SessionPanel({ session, onPause, onResume, onStop }: { 
  session: any; 
  onPause: () => void; 
  onResume: () => void; 
  onStop: () => void;
}) {
  const getStateColor = (state: string) => {
    switch (state) {
      case 'online':
      case 'sending':
        return 'bg-green-500';
      case 'paused':
        return 'bg-yellow-500';
      case 'stopped':
      case 'error':
        return 'bg-red-500';
      default:
        return 'bg-brand-500';
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0, height: 0 }}
      animate={{ opacity: 1, height: 'auto' }}
      exit={{ opacity: 0, height: 0 }}
      className="bg-dark-800 border-l-4 border-brand-500 rounded-xl p-6 mb-6"
    >
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-3">
          <div className={`w-3 h-3 rounded-full ${getStateColor(session.state)} animate-pulse`} />
          <div>
            <p className="font-semibold text-slate-100">Active Session: {session.session_id}</p>
            <p className="text-sm text-slate-400 capitalize">{session.state}</p>
          </div>
        </div>
        
        <div className="flex gap-2">
          {session.state === 'paused' ? (
            <button
              onClick={onResume}
              className="flex items-center gap-2 px-3 py-1.5 bg-green-500/20 text-green-400 rounded-lg hover:bg-green-500/30 transition-colors"
            >
              <Play className="w-4 h-4" />
              Resume
            </button>
          ) : (
            <button
              onClick={onPause}
              className="flex items-center gap-2 px-3 py-1.5 bg-yellow-500/20 text-yellow-400 rounded-lg hover:bg-yellow-500/30 transition-colors"
            >
              <Pause className="w-4 h-4" />
              Pause
            </button>
          )}
          
          <button
            onClick={onStop}
            className="flex items-center gap-2 px-3 py-1.5 bg-red-500/20 text-red-400 rounded-lg hover:bg-red-500/30 transition-colors"
          >
            <Square className="w-4 h-4" />
            Stop
          </button>
        </div>
      </div>
      
      <div className="space-y-3">
        <div>
          <div className="flex justify-between text-sm mb-1">
            <span className="text-slate-400">Progress</span>
            <span className="text-slate-200">{session.progress.current} / {session.progress.total} ({session.progress.percentage}%)</span>
          </div>
          <div className="h-2 bg-slate-700 rounded-full overflow-hidden">
            <div
              className="h-full bg-brand-500 transition-all duration-500"
              style={{ width: `${session.progress.percentage}%` }}
            />
          </div>
        </div>
        
        {session.metrics && (
          <div className="flex gap-6 text-sm">
            <span className="text-slate-400">
              Duration: <span className="text-slate-200">{formatDuration(session.metrics.duration_seconds)}</span>
            </span>
            {session.metrics.avg_delay_seconds && (
              <span className="text-slate-400">
                Avg Delay: <span className="text-slate-200">{session.metrics.avg_delay_seconds.toFixed(1)}s</span>
              </span>
            )}
            {session.metrics.typing_time_total && (
              <span className="text-slate-400">
                Typing: <span className="text-slate-200">{session.metrics.typing_time_total.toFixed(0)}s</span>
              </span>
            )}
          </div>
        )}
      </div>
    </motion.div>
  );
}

export function Reminders() {
  const queryClient = useQueryClient();
  const [showAntiSpam, setShowAntiSpam] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [filterBy, setFilterBy] = useState('all');
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null);
  const [sessionData, setSessionData] = useState<any>(null);

  // Store
  const store = useRemindersStore();

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
    refetchInterval: 30000,
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
      limit: 100,
    }),
  });

  // Update store when data loads
  useEffect(() => {
    if (config) store.setConfig(config);
    if (templates) store.setTemplates(templates);
    if (stats) store.setStats(stats);
    if (snapshotStatus) store.setSnapshotStatus(snapshotStatus);
    if (partiesData) store.setParties(partiesData.items);
  }, [config, templates, stats, snapshotStatus, partiesData]);

  // Session polling
  useEffect(() => {
    if (!activeSessionId) return;

    const interval = setInterval(async () => {
      try {
        const status = await api.getSessionStatus(activeSessionId);
        if (status) {
          setSessionData(status);
          if (['completed', 'stopped', 'error'].includes(status.state)) {
            setTimeout(() => {
              setActiveSessionId(null);
              setSessionData(null);
            }, 5000);
          }
        }
      } catch {
        setActiveSessionId(null);
        setSessionData(null);
      }
    }, 2000);

    return () => clearInterval(interval);
  }, [activeSessionId]);

  // Mutations
  const refreshSnapshotMutation = useMutation({
    mutationFn: api.refreshReminderSnapshot,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['reminder-snapshot'] }),
  });

  const sendRemindersMutation = useMutation({
    mutationFn: (data: { partyCodes: string[]; templateId: string; partyTemplates?: Record<string, string> }) =>
      api.sendReminders(data.partyCodes, data.templateId, data.partyTemplates),
    onSuccess: (data) => {
      if (data.session_id) {
        setActiveSessionId(data.session_id);
        store.clearSelection();
      }
    },
  });

  const updateAntiSpamMutation = useMutation({
    mutationFn: api.updateAntiSpamConfig,
  });

  const handleToggleSelection = (code: string) => {
    store.togglePartySelection(code);
  };

  const handleSendReminders = () => {
    const selectedCodes = Array.from(store.selectedPartyCodes);
    if (selectedCodes.length === 0 || !store.defaultTemplateId) return;

    sendRemindersMutation.mutate({
      partyCodes: selectedCodes,
      templateId: store.defaultTemplateId,
      partyTemplates: store.partyTemplates,
    });
  };

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
    return (
      <div className="flex items-center justify-center h-96">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-brand-500"></div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-slate-100">Payment Reminders</h2>
          <p className="text-slate-400 mt-1">Send payment reminders with attached ledgers</p>
          {snapshotStatus?.has_snapshot && (
            <p className="text-sm text-slate-500 mt-1">
              Last refreshed: {formatDateTime(snapshotStatus.last_refreshed_at || null)}
            </p>
          )}
        </div>
        <button
          onClick={() => refreshSnapshotMutation.mutate()}
          disabled={refreshSnapshotMutation.isPending}
          className="flex items-center gap-2 px-4 py-2 bg-slate-700 hover:bg-slate-600 text-slate-200 rounded-lg transition-colors disabled:opacity-50"
        >
          <RefreshCw className={`w-4 h-4 ${refreshSnapshotMutation.isPending && 'animate-spin'}`} />
          Refresh Data
        </button>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <StatCard title="Eligible Parties" value={stats?.eligible_parties || 0} />
        <StatCard title="Enabled" value={stats?.enabled_parties || 0} />
        <StatCard 
          title="Total Due" 
          value={formatCurrency(stats?.total_amount_due || 0)} 
        />
        <div className={`bg-dark-800 border rounded-xl p-4 ${sessionData ? 'border-brand-500' : 'border-slate-700'}`}>
          <p className="text-sm text-slate-400">Session Status</p>
          <p className="text-2xl font-bold text-slate-100 mt-1">
            {sessionData ? `${sessionData.progress.percentage}%` : 'Ready'}
          </p>
        </div>
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
      <div className="bg-dark-800 border border-slate-700 rounded-xl p-6">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-3">
            <FileText className="w-5 h-5 text-brand-400" />
            <h3 className="font-semibold text-slate-100">Message Template</h3>
          </div>
          
          <button
            onClick={() => window.open('/api/v1/reminders/templates', '_blank')}
            className="text-sm text-brand-400 hover:text-brand-300"
          >
            Manage Templates
          </button>
        </div>
        
        <select
          value={store.defaultTemplateId}
          onChange={(e) => store.setDefaultTemplateId(e.target.value)}
          className="w-full md:w-96 px-4 py-2 bg-slate-700 border border-slate-600 rounded-lg text-slate-200 focus:outline-none focus:ring-2 focus:ring-brand-500"
        >
          <option value="">Select a template...</option>
          {templates?.map((t: MessageTemplate) => (
            <option key={t.id} value={t.id}>{t.name} {t.is_default && '(Default)'}</option>
          ))}
        </select>
        
        {store.defaultTemplateId && (
          <div className="mt-4 p-4 bg-slate-700/30 rounded-lg">
            <p className="text-sm text-slate-400 mb-1">Preview:</p>
            <pre className="text-sm text-slate-300 whitespace-pre-wrap">
              {templates?.find((t: MessageTemplate) => t.id === store.defaultTemplateId)?.content}
            </pre>
          </div>
        )}
      </div>

      {/* Anti-Spam Panel */}
      <div className="bg-dark-800 border border-slate-700 rounded-xl overflow-hidden">
        <button
          onClick={() => setShowAntiSpam(!showAntiSpam)}
          className="w-full flex items-center justify-between p-4 hover:bg-slate-700/30 transition-colors"
        >
          <div className="flex items-center gap-3">
            <Shield className="w-5 h-5 text-brand-400" />
            <div className="text-left">
              <h3 className="font-semibold text-slate-100">Anti-Spam Protection</h3>
              <p className="text-sm text-slate-400">{store.antiSpamConfig.enabled ? 'Enabled' : 'Disabled'}</p>
            </div>
          </div>
          {showAntiSpam ? <ChevronUp className="w-5 h-5 text-slate-400" /> : <ChevronDown className="w-5 h-5 text-slate-400" />}
        </button>
        
        <AnimatePresence>
          {showAntiSpam && (
            <motion.div
              initial={{ height: 0 }}
              animate={{ height: 'auto' }}
              exit={{ height: 0 }}
              className="border-t border-slate-700 overflow-hidden"
            >
              <div className="p-4 space-y-4">
                <label className="flex items-center justify-between p-3 bg-slate-700/30 rounded-lg">
                  <div>
                    <p className="font-medium text-slate-200">Enable Anti-Spam</p>
                    <p className="text-sm text-slate-400">Protect against WhatsApp bulk detection</p>
                  </div>
                  <input
                    type="checkbox"
                    checked={store.antiSpamConfig.enabled}
                    onChange={(e) => {
                      const newConfig = { ...store.antiSpamConfig, enabled: e.target.checked };
                      store.setAntiSpamConfig(newConfig);
                      updateAntiSpamMutation.mutate(newConfig);
                    }}
                    className="w-5 h-5 rounded border-slate-600 text-brand-500"
                  />
                </label>

                {store.antiSpamConfig.enabled && (
                  <>
                    <label className="flex items-center justify-between p-3 bg-slate-700/30 rounded-lg">
                      <span className="text-slate-200">Message Size Inflation</span>
                      <input
                        type="checkbox"
                        checked={store.antiSpamConfig.message_inflation}
                        onChange={(e) => {
                          const newConfig = { ...store.antiSpamConfig, message_inflation: e.target.checked };
                          store.setAntiSpamConfig(newConfig);
                          updateAntiSpamMutation.mutate(newConfig);
                        }}
                        className="w-5 h-5 rounded border-slate-600 text-brand-500"
                      />
                    </label>

                    <label className="flex items-center justify-between p-3 bg-slate-700/30 rounded-lg">
                      <span className="text-slate-200">PDF Size Inflation</span>
                      <input
                        type="checkbox"
                        checked={store.antiSpamConfig.pdf_inflation}
                        onChange={(e) => {
                          const newConfig = { ...store.antiSpamConfig, pdf_inflation: e.target.checked };
                          store.setAntiSpamConfig(newConfig);
                          updateAntiSpamMutation.mutate(newConfig);
                        }}
                        className="w-5 h-5 rounded border-slate-600 text-brand-500"
                      />
                    </label>

                    <label className="flex items-center justify-between p-3 bg-slate-700/30 rounded-lg">
                      <span className="text-slate-200">Human Typing Simulation</span>
                      <input
                        type="checkbox"
                        checked={store.antiSpamConfig.typing_simulation}
                        onChange={(e) => {
                          const newConfig = { ...store.antiSpamConfig, typing_simulation: e.target.checked };
                          store.setAntiSpamConfig(newConfig);
                          updateAntiSpamMutation.mutate(newConfig);
                        }}
                        className="w-5 h-5 rounded border-slate-600 text-brand-500"
                      />
                    </label>

                    <label className="flex items-center justify-between p-3 bg-slate-700/30 rounded-lg">
                      <span className="text-slate-200">Session Startup Delay</span>
                      <input
                        type="checkbox"
                        checked={store.antiSpamConfig.startup_delay_enabled}
                        onChange={(e) => {
                          const newConfig = { ...store.antiSpamConfig, startup_delay_enabled: e.target.checked };
                          store.setAntiSpamConfig(newConfig);
                          updateAntiSpamMutation.mutate(newConfig);
                        }}
                        className="w-5 h-5 rounded border-slate-600 text-brand-500"
                      />
                    </label>
                  </>
                )}
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      {/* Party Selection */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Selected Parties */}
        <div className="bg-dark-800 border border-slate-700 rounded-xl overflow-hidden">
          <div className="p-4 border-b border-slate-700 flex items-center justify-between">
            <div className="flex items-center gap-3">
              <CheckCircle className="w-5 h-5 text-green-400" />
              <h3 className="font-semibold text-slate-100">Selected Parties</h3>
              <span className="px-2 py-0.5 bg-brand-500 text-white text-xs rounded-full">{selectedParties.length}</span>
            </div>
            <span className="font-semibold text-brand-400">{formatCurrency(selectedTotalAmount)}</span>
          </div>
          
          <div className="p-4">
            {selectedParties.length === 0 ? (
              <div className="text-center py-8 text-slate-500">
                <Users className="w-12 h-12 mx-auto mb-2 opacity-50" />
                <p>No parties selected</p>
              </div>
            ) : (
              <>
                <div className="space-y-2 max-h-96 overflow-y-auto">
                  {selectedParties.map((party) => (
                    <div key={party.code} className="flex items-center justify-between p-3 bg-slate-700/30 rounded-lg">
                      <div>
                        <p className="font-medium text-slate-200">{party.name}</p>
                        <p className="text-sm text-slate-400">{party.code} • {formatCurrency(party.amount_due)}</p>
                      </div>
                      
                      <button
                        onClick={() => handleToggleSelection(party.code)}
                        className="p-2 text-red-400 hover:bg-red-500/20 rounded-lg transition-colors"
                      >
                        <X className="w-4 h-4" />
                      </button>
                    </div>
                  ))}
                </div>
                
                <button
                  onClick={() => store.clearSelection()}
                  className="mt-4 w-full py-2 text-red-400 hover:bg-red-500/20 rounded-lg transition-colors"
                >
                  Clear All
                </button>
              </>
            )}
          </div>
        </div>

        {/* Available Parties */}
        <div className="bg-dark-800 border border-slate-700 rounded-xl overflow-hidden">
          <div className="p-4 border-b border-slate-700 space-y-3">
            <div className="flex items-center gap-3">
              <Users className="w-5 h-5 text-slate-400" />
              <h3 className="font-semibold text-slate-100">Available Parties</h3>
              <span className="px-2 py-0.5 bg-slate-600 text-slate-200 text-xs rounded-full">{availableParties.length}</span>
            </div>
            
            <div className="flex gap-2">
              <div className="relative flex-1">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
                <input
                  type="text"
                  placeholder="Search parties..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="w-full pl-10 pr-4 py-2 bg-slate-700 border border-slate-600 rounded-lg text-slate-200 focus:outline-none focus:ring-2 focus:ring-brand-500"
                />
              </div>
              
              <select
                value={filterBy}
                onChange={(e) => setFilterBy(e.target.value)}
                className="px-3 py-2 bg-slate-700 border border-slate-600 rounded-lg text-slate-200 focus:outline-none focus:ring-2 focus:ring-brand-500"
              >
                <option value="all">All</option>
                <option value="enabled">Enabled</option>
                <option value="recent">Not Recent</option>
              </select>
            </div>
          </div>
          
          <div className="p-4">
            <div className="space-y-2 max-h-96 overflow-y-auto">
              {availableParties.map((party) => (
                <div
                  key={party.code}
                  onClick={() => handleToggleSelection(party.code)}
                  className="flex items-center justify-between p-3 bg-slate-700/30 rounded-lg cursor-pointer hover:bg-slate-700/50 transition-colors"
                >
                  <div>
                    <p className="font-medium text-slate-200">{party.name}</p>
                    <p className="text-sm text-slate-400">{party.code} • {formatCurrency(party.amount_due)}</p>
                  </div>
                  
                  <div className="w-5 h-5 border-2 border-slate-500 rounded flex items-center justify-center">
                    <div className="w-3 h-3 bg-brand-500 rounded-sm opacity-0 group-hover:opacity-100" />
                  </div>
                </div>
              ))}
              
              {availableParties.length === 0 && (
                <div className="text-center py-8 text-slate-500">
                  <p>No parties available</p>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Action Bar */}
      <div className="sticky bottom-4 bg-dark-800 border border-slate-700 rounded-xl p-4 shadow-xl">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-6">
            <div>
              <span className="text-slate-400">Selected: </span>
              <span className="font-bold text-slate-100">{selectedParties.length}</span>
            </div>
            
            <div>
              <span className="text-slate-400">Total: </span>
              <span className="font-bold text-brand-400">{formatCurrency(selectedTotalAmount)}</span>
            </div>
          </div>
          
          <div className="flex items-center gap-3">
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
              className="flex items-center gap-2 px-4 py-2 bg-slate-700 hover:bg-slate-600 text-slate-200 rounded-lg transition-colors disabled:opacity-50"
            >
              <Download className="w-4 h-4" />
              Export
            </button>
            
            <button
              onClick={handleSendReminders}
              disabled={selectedParties.length === 0 || !store.defaultTemplateId || sendRemindersMutation.isPending || activeSessionId !== null}
              className="flex items-center gap-2 px-6 py-2 bg-brand-500 hover:bg-brand-600 text-white rounded-lg transition-colors disabled:opacity-50 font-medium"
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

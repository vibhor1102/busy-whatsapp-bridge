import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { motion } from 'framer-motion';
import {
  Inbox,
  RefreshCw,
  Clock,
  AlertTriangle,
  CheckCircle,
  XCircle,
} from 'lucide-react';
import { api } from '../services/api';
import { useQueueStore } from '../stores/queueStore';
import { LoadingState } from '../components/ui/LoadingState';
import { getStatusStyle } from '../utils/statusColors';
import { REFETCH_INTERVALS, LIMITS } from '../constants';
import type { Message } from '../types';

const tabs = [
  { id: 'pending', label: 'Pending', icon: Clock },
  { id: 'retrying', label: 'Retrying', icon: RefreshCw },
  { id: 'deadLetter', label: 'Dead Letter', icon: AlertTriangle },
  { id: 'history', label: 'History', icon: CheckCircle },
] as const;

export function MessageQueue() {
  const [activeTab, setActiveTab] = useState<typeof tabs[number]['id']>('pending');
  const setQueueStats = useQueueStore((state) => state.setStats);

  const { data: stats, isLoading: statsLoading } = useQuery({
    queryKey: ['queue-stats'],
    queryFn: () => api.getQueueStats(),
    refetchInterval: REFETCH_INTERVALS.QUEUE_STATS,
  });

  const { data: messages, isLoading: messagesLoading } = useQuery<{ messages: Message[] }>({
    queryKey: ['queue-messages', activeTab],
    queryFn: async () => {
      switch (activeTab) {
        case 'pending':
          return api.getPendingMessages(LIMITS.DEFAULT_PAGE_SIZE);
        case 'retrying':
          return api.getPendingMessages(LIMITS.DEFAULT_PAGE_SIZE);
        case 'deadLetter':
          return api.getDeadLetterMessages(LIMITS.DEFAULT_PAGE_SIZE);
        case 'history': {
          const result = await api.getQueueHistory({ limit: LIMITS.DEFAULT_PAGE_SIZE });
          return { messages: result.items };
        }
        default:
          return api.getPendingMessages(LIMITS.DEFAULT_PAGE_SIZE);
      }
    },
    refetchInterval: REFETCH_INTERVALS.QUEUE_STATS,
  });

  if (stats) {
    setQueueStats(stats);
  }

  const isLoading = statsLoading || messagesLoading;

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'sent':
        return <CheckCircle className="w-3.5 h-3.5" />;
      case 'failed':
        return <XCircle className="w-3.5 h-3.5" />;
      case 'retrying':
        return <RefreshCw className="w-3.5 h-3.5" />;
      default:
        return <Clock className="w-3.5 h-3.5" />;
    }
  };

  const statCards = [
    { label: 'Pending', value: stats?.pending || 0, variant: 'warning' as const },
    { label: 'Retrying', value: stats?.retrying || 0, variant: 'info' as const },
    { label: 'Dead Letter', value: stats?.dead_letter || 0, variant: 'danger' as const },
    { label: 'Sent Today', value: stats?.sent_today || 0, variant: 'success' as const },
  ];

  const variantStyles = {
    warning: { bg: 'var(--warning-soft)', border: 'var(--warning-soft-border)' },
    info: { bg: 'var(--info-soft)', border: 'var(--info-soft-border)' },
    danger: { bg: 'var(--danger-soft)', border: 'var(--danger-soft-border)' },
    success: { bg: 'var(--success-soft)', border: 'var(--success-soft-border)' },
  };

  return (
    <div className="space-y-5">
      {/* Header */}
      <div>
        <h2 className="text-2xl font-bold" style={{ color: 'var(--text-primary)' }}>
          Message Queue
        </h2>
        <p className="text-sm mt-0.5" style={{ color: 'var(--text-tertiary)' }}>
          Monitor and manage message queue status
        </p>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        {statCards.map((stat, i) => {
          const s = variantStyles[stat.variant];
          return (
            <motion.div
              key={stat.label}
              initial={{ opacity: 0, y: 16 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.05 }}
              className="p-4 rounded-xl"
              style={{ background: s.bg, border: `1px solid ${s.border}` }}
            >
              <p className="text-xs font-medium uppercase tracking-wider" style={{ color: 'var(--text-tertiary)' }}>
                {stat.label}
              </p>
              <p className="text-xl font-bold mt-1" style={{ color: 'var(--text-primary)' }}>
                {stat.value}
              </p>
            </motion.div>
          );
        })}
      </div>

      {/* Tabs */}
      <div className="card overflow-hidden">
        <div
          className="flex border-b"
          role="tablist"
          aria-label="Message queue tabs"
          style={{ borderColor: 'var(--border-default)' }}
        >
          {tabs.map((tab) => {
            const Icon = tab.icon;
            const isActive = activeTab === tab.id;
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                role="tab"
                aria-selected={isActive}
                aria-controls={`tabpanel-${tab.id}`}
                id={`tab-${tab.id}`}
                className="flex items-center gap-2 px-5 py-3 text-sm font-medium transition-colors"
                style={{
                  color: isActive ? 'var(--brand-accent)' : 'var(--text-tertiary)',
                  borderBottom: isActive ? '2px solid var(--brand-accent)' : '2px solid transparent',
                  background: isActive ? 'var(--brand-soft)' : 'transparent',
                }}
                onMouseEnter={(e) => { if (!isActive) e.currentTarget.style.background = 'var(--bg-input)'; }}
                onMouseLeave={(e) => { if (!isActive) e.currentTarget.style.background = 'transparent'; }}
              >
                <Icon className="w-3.5 h-3.5" aria-hidden="true" />
                {tab.label}
              </button>
            );
          })}
        </div>

        {/* Table */}
        <div
          role="tabpanel"
          id={`tabpanel-${activeTab}`}
          aria-labelledby={`tab-${activeTab}`}
          className="p-4"
        >
          {isLoading ? (
            <div className="py-12">
              <LoadingState size="md" />
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr style={{ borderBottom: '1px solid var(--border-default)' }}>
                    {['Phone', 'Message', 'Status', 'Retries', 'Created'].map(h => (
                      <th
                        key={h}
                        className="text-left py-2.5 px-3 text-xs font-medium uppercase tracking-wider"
                        style={{ color: 'var(--text-tertiary)' }}
                      >
                        {h}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {messages?.messages?.map((message: Message) => {
                    const ms = getStatusStyle(message.status);
                    return (
                      <tr
                        key={message.id}
                        className="transition-colors"
                        style={{ borderBottom: '1px solid var(--border-subtle)' }}
                        onMouseEnter={(e) => (e.currentTarget.style.background = 'var(--bg-input)')}
                        onMouseLeave={(e) => (e.currentTarget.style.background = 'transparent')}
                      >
                        <td className="py-2.5 px-3 text-sm" style={{ color: 'var(--text-secondary)' }}>
                          {message.phone}
                        </td>
                        <td className="py-2.5 px-3 text-sm truncate max-w-xs" style={{ color: 'var(--text-secondary)' }}>
                          {message.message.substring(0, 50)}...
                        </td>
                        <td className="py-2.5 px-3">
                          <span
                            className="inline-flex items-center gap-1.5 text-xs font-medium"
                            style={{ color: ms.color }}
                          >
                            {getStatusIcon(message.status)}
                            <span className="capitalize">{message.status}</span>
                          </span>
                        </td>
                        <td className="py-2.5 px-3 text-sm" style={{ color: 'var(--text-secondary)' }}>
                          {message.retry_count} / {message.max_retries}
                        </td>
                        <td className="py-2.5 px-3 text-xs" style={{ color: 'var(--text-tertiary)' }}>
                          {new Date(message.created_at).toLocaleString()}
                        </td>
                      </tr>
                    );
                  })}

                  {messages?.messages?.length === 0 && (
                    <tr>
                      <td colSpan={5} className="py-12 text-center" style={{ color: 'var(--text-tertiary)' }}>
                        <div className="flex flex-col items-center gap-2">
                          <Inbox className="w-10 h-10 opacity-40" />
                          <p className="text-sm">No messages found</p>
                        </div>
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { motion } from 'framer-motion';
import { 
  Inbox, 
  RefreshCw, 
  Clock, 
  AlertTriangle, 
  CheckCircle,
  XCircle
} from 'lucide-react';
import { api } from '../services/api';
import { useQueueStore } from '../stores/queueStore';
import { LoadingState } from '../components/ui/LoadingState';
import { getStatusColor } from '../utils/statusColors';
import { REFETCH_INTERVALS, LIMITS } from '../constants';
import type { Message } from '../types';

const tabs = [
  { id: 'pending', label: 'Pending', icon: Clock },
  { id: 'retrying', label: 'Retrying', icon: RefreshCw },
  { id: 'deadLetter', label: 'Dead Letter', icon: AlertTriangle },
  { id: 'history', label: 'History', icon: CheckCircle },
] as const;

const colorStyles: Record<string, { bg: string; border: string }> = {
  yellow: { bg: 'bg-yellow-500/10', border: 'border-yellow-500/30' },
  blue: { bg: 'bg-blue-500/10', border: 'border-blue-500/30' },
  red: { bg: 'bg-red-500/10', border: 'border-red-500/30' },
  green: { bg: 'bg-green-500/10', border: 'border-green-500/30' },
};

export function MessageQueue() {
  const [activeTab, setActiveTab] = useState<typeof tabs[number]['id']>('pending');
  const setQueueStats = useQueueStore((state) => state.setStats);

  const { data: stats, isLoading: statsLoading } = useQuery({
    queryKey: ['queue-stats'],
    queryFn: api.getQueueStats,
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

  // Using getStatusColor from utils/statusColors.ts

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'sent':
        return <CheckCircle className="w-4 h-4" />;
      case 'failed':
        return <XCircle className="w-4 h-4" />;
      case 'retrying':
        return <RefreshCw className="w-4 h-4" />;
      default:
        return <Clock className="w-4 h-4" />;
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-slate-100">Message Queue</h2>
          <p className="text-slate-400 mt-1">Monitor and manage message queue status</p>
        </div>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {[
          { label: 'Pending', value: stats?.pending || 0, color: 'yellow' },
          { label: 'Retrying', value: stats?.retrying || 0, color: 'blue' },
          { label: 'Dead Letter', value: stats?.dead_letter || 0, color: 'red' },
          { label: 'Sent Today', value: stats?.sent_today || 0, color: 'green' },
        ].map((stat) => (
          <motion.div
            key={stat.label}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className={`p-4 rounded-xl ${colorStyles[stat.color].bg} ${colorStyles[stat.color].border}`}
          >
            <p className="text-sm text-slate-400">{stat.label}</p>
            <p className="text-2xl font-bold text-slate-100 mt-1">{stat.value}</p>
          </motion.div>
        ))}
      </div>

      {/* Tabs */}
      <div className="bg-dark-800 border border-slate-700 rounded-xl overflow-hidden">
        <div
          className="flex border-b border-slate-700"
          role="tablist"
          aria-label="Message queue tabs"
        >
          {tabs.map((tab) => {
            const Icon = tab.icon;
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                role="tab"
                aria-selected={activeTab === tab.id}
                aria-controls={`tabpanel-${tab.id}`}
                id={`tab-${tab.id}`}
                className={`flex items-center gap-2 px-6 py-4 font-medium transition-colors ${
                  activeTab === tab.id
                    ? 'text-brand-400 border-b-2 border-brand-400 bg-brand-500/10'
                    : 'text-slate-400 hover:text-slate-200 hover:bg-slate-700/30'
                }`}
              >
                <Icon className="w-4 h-4" aria-hidden="true" />
                {tab.label}
              </button>
            );
          })}
        </div>

        {/* Table - Tab Panel */}
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
                  <tr className="border-b border-slate-700">
                    <th className="text-left py-3 px-4 text-sm font-medium text-slate-400">Phone</th>
                    <th className="text-left py-3 px-4 text-sm font-medium text-slate-400">Message</th>
                    <th className="text-left py-3 px-4 text-sm font-medium text-slate-400">Status</th>
                    <th className="text-left py-3 px-4 text-sm font-medium text-slate-400">Retries</th>
                    <th className="text-left py-3 px-4 text-sm font-medium text-slate-400">Created</th>
                  </tr>
                </thead>
                <tbody>
                  {messages?.messages?.map((message: Message) => (
                    <tr key={message.id} className="border-b border-slate-700/50 hover:bg-slate-700/20">
                      <td className="py-3 px-4 text-slate-300">{message.phone}</td>
                      <td className="py-3 px-4 text-slate-300 truncate max-w-xs">
                        {message.message.substring(0, 50)}...
                      </td>
                      <td className="py-3 px-4">
                        <span className={`flex items-center gap-2 ${getStatusColor(message.status)}`}>
                          {getStatusIcon(message.status)}
                          <span className="capitalize">{message.status}</span>
                        </span>
                      </td>
                      <td className="py-3 px-4 text-slate-300">
                        {message.retry_count} / {message.max_retries}
                      </td>
                      <td className="py-3 px-4 text-slate-400 text-sm">
                        {new Date(message.created_at).toLocaleString()}
                      </td>
                    </tr>
                  ))}
                  
                  {messages?.messages?.length === 0 && (
                    <tr>
                      <td colSpan={5} className="py-12 text-center text-slate-400">
                        <div className="flex flex-col items-center gap-2">
                          <Inbox className="w-12 h-12 opacity-50" />
                          <p>No messages found</p>
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

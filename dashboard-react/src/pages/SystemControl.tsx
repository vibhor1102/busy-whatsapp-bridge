import { useState, useCallback } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { motion } from 'framer-motion';
import { toast } from 'sonner';
import {
  Cpu,
  HardDrive,
  MemoryStick,
  RefreshCw,
  Play,
  Square,
  Loader2,
  Server,
  Activity,
} from 'lucide-react';
import { api } from '../services/api';
import { LoadingState } from '../components/ui/LoadingState';
import { formatBytes } from '../utils/formatters';
import { REFETCH_INTERVALS } from '../constants';

function ProgressBar({ value, color }: { value: number; color: string }) {
  return (
    <div className="h-2 rounded-full overflow-hidden" style={{ background: 'var(--bg-input)' }}>
      <div
        className="h-full rounded-full transition-all duration-500"
        style={{ width: `${Math.min(value, 100)}%`, background: color }}
      />
    </div>
  );
}

function getBarColor(percent: number): string {
  if (percent > 80) return 'var(--danger)';
  if (percent > 60) return 'var(--warning)';
  return 'var(--success)';
}

export function SystemControl() {
  const queryClient = useQueryClient();
  const [actionLoading, setActionLoading] = useState<string | null>(null);

  const { data: resources, isLoading } = useQuery({
    queryKey: ['system-resources'],
    queryFn: api.getSystemResources,
    refetchInterval: REFETCH_INTERVALS.QUEUE_STATS,
  });

  const startQueueMutation = useMutation({
    mutationFn: api.startQueueWorker,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['queue-messages'] });
      toast.success('Queue worker started successfully');
    },
    onError: (error: Error) => {
      toast.error(`Failed to start queue worker: ${error.message}`);
    },
  });

  const stopQueueMutation = useMutation({
    mutationFn: api.stopQueueWorker,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['queue-messages'] });
      toast.success('Queue worker stopped successfully');
    },
    onError: (error: Error) => {
      toast.error(`Failed to stop queue worker: ${error.message}`);
    },
  });

  const restartBaileysMutation = useMutation({
    mutationFn: api.restartBaileys,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['baileys-status'] });
      toast.success('Baileys service restarted successfully');
    },
    onError: (error: Error) => {
      toast.error(`Failed to restart Baileys: ${error.message}`);
    },
  });

  const handleAction = useCallback(async (
    action: string,
    mutation: { mutateAsync: () => Promise<unknown> }
  ) => {
    setActionLoading(action);
    await mutation.mutateAsync();
    setActionLoading(null);
  }, []);

  if (isLoading) {
    return <LoadingState size="lg" fullPage />;
  }

  const cpuPercent = resources?.cpu_percent ?? 0;
  const memPercent = resources?.memory?.percent ?? 0;
  const diskPercent = resources?.disk?.percent ?? 0;

  const resourceCards = [
    {
      label: 'CPU Usage',
      value: `${cpuPercent.toFixed(1)}%`,
      percent: cpuPercent,
      icon: Cpu,
      iconBg: 'var(--info-soft)',
      iconColor: 'var(--info)',
    },
    {
      label: 'Memory Usage',
      value: `${memPercent.toFixed(1)}%`,
      percent: memPercent,
      icon: MemoryStick,
      iconBg: 'var(--brand-soft)',
      iconColor: 'var(--brand-accent)',
      detail: `${formatBytes(resources?.memory.used || 0)} / ${formatBytes(resources?.memory.total || 0)}`,
    },
    {
      label: 'Disk Usage',
      value: `${diskPercent.toFixed(1)}%`,
      percent: diskPercent,
      icon: HardDrive,
      iconBg: 'var(--warning-soft)',
      iconColor: 'var(--warning)',
      detail: `${formatBytes(resources?.disk?.used ?? 0)} / ${formatBytes(resources?.disk?.total ?? 0)}`,
    },
  ];

  return (
    <div className="space-y-5">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold" style={{ color: 'var(--text-primary)' }}>
            System
          </h2>
          <p className="text-sm mt-0.5" style={{ color: 'var(--text-tertiary)' }}>
            Monitor resources and control services
          </p>
        </div>
        <button
          onClick={() => queryClient.invalidateQueries({ queryKey: ['system-resources'] })}
          className="btn-secondary"
        >
          <RefreshCw className="w-4 h-4" />
          Refresh
        </button>
      </div>

      {/* Resource Usage Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {resourceCards.map((card, i) => {
          const Icon = card.icon;
          return (
            <motion.div
              key={card.label}
              initial={{ opacity: 0, y: 16 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.05 }}
              className="card p-5"
            >
              <div className="flex items-center gap-3 mb-4">
                <div
                  className="p-2.5 rounded-lg"
                  style={{ background: card.iconBg }}
                >
                  <Icon className="w-5 h-5" style={{ color: card.iconColor }} />
                </div>
                <div>
                  <p className="text-xs" style={{ color: 'var(--text-tertiary)' }}>{card.label}</p>
                  <p className="text-xl font-bold" style={{ color: 'var(--text-primary)' }}>{card.value}</p>
                </div>
              </div>

              <ProgressBar value={card.percent} color={getBarColor(card.percent)} />

              {card.detail && (
                <p className="text-xs mt-2" style={{ color: 'var(--text-tertiary)' }}>{card.detail}</p>
              )}
            </motion.div>
          );
        })}
      </div>

      {/* Service Controls */}
      <motion.div
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.2 }}
        className="card p-5"
      >
        <h3 className="text-sm font-semibold mb-4" style={{ color: 'var(--text-primary)' }}>
          Service Controls
        </h3>

        <div className="space-y-3">
          {/* Queue Worker */}
          <div
            className="flex items-center justify-between p-3.5 rounded-lg"
            style={{ background: 'var(--bg-input)' }}
          >
            <div className="flex items-center gap-3">
              <Server className="w-4 h-4" style={{ color: 'var(--text-tertiary)' }} />
              <div>
                <p className="text-sm font-medium" style={{ color: 'var(--text-primary)' }}>
                  Queue Worker
                </p>
                <p className="text-xs" style={{ color: 'var(--text-tertiary)' }}>
                  Process pending messages in queue
                </p>
              </div>
            </div>

            <div className="flex gap-2">
              <button
                onClick={() => handleAction('start-queue', startQueueMutation)}
                disabled={actionLoading === 'start-queue'}
                className="text-xs py-1.5 px-3 rounded-lg flex items-center gap-1.5 font-medium transition-colors"
                style={{
                  background: 'var(--success-soft)',
                  color: 'var(--success)',
                  border: '1px solid var(--success-soft-border)',
                }}
              >
                {actionLoading === 'start-queue' ? (
                  <Loader2 className="w-3.5 h-3.5 animate-spin" />
                ) : (
                  <Play className="w-3.5 h-3.5" />
                )}
                Start
              </button>

              <button
                onClick={() => handleAction('stop-queue', stopQueueMutation)}
                disabled={actionLoading === 'stop-queue'}
                className="btn-danger text-xs py-1.5 px-3"
              >
                {actionLoading === 'stop-queue' ? (
                  <Loader2 className="w-3.5 h-3.5 animate-spin" />
                ) : (
                  <Square className="w-3.5 h-3.5" />
                )}
                Stop
              </button>
            </div>
          </div>

          {/* Baileys */}
          <div
            className="flex items-center justify-between p-3.5 rounded-lg"
            style={{ background: 'var(--bg-input)' }}
          >
            <div className="flex items-center gap-3">
              <Activity className="w-4 h-4" style={{ color: 'var(--text-tertiary)' }} />
              <div>
                <p className="text-sm font-medium" style={{ color: 'var(--text-primary)' }}>
                  Baileys Service
                </p>
                <p className="text-xs" style={{ color: 'var(--text-tertiary)' }}>
                  Restart WhatsApp Web connection
                </p>
              </div>
            </div>

            <button
              onClick={() => handleAction('restart-baileys', restartBaileysMutation)}
              disabled={actionLoading === 'restart-baileys'}
              className="btn-primary text-xs py-1.5 px-3"
            >
              {actionLoading === 'restart-baileys' ? (
                <Loader2 className="w-3.5 h-3.5 animate-spin" />
              ) : (
                <RefreshCw className="w-3.5 h-3.5" />
              )}
              Restart
            </button>
          </div>
        </div>
      </motion.div>
    </div>
  );
}

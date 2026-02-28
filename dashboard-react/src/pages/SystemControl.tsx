import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { motion } from 'framer-motion';
import { 
  Cpu, 
  HardDrive, 
  MemoryStick, 
  RefreshCw, 
  Play, 
  Square,
  Loader2,
  Server,
  Activity
} from 'lucide-react';
import { api } from '../services/api';

function formatBytes(bytes: number): string {
  if (bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

function ProgressBar({ value, color = 'brand' }: { value: number; color?: string }) {
  const colorClasses: Record<string, string> = {
    brand: 'bg-brand-500',
    green: 'bg-green-500',
    yellow: 'bg-yellow-500',
    red: 'bg-red-500',
  };

  return (
    <div className="h-2 bg-slate-700 rounded-full overflow-hidden">
      <div
        className={`h-full ${colorClasses[color]} transition-all duration-500`}
        style={{ width: `${Math.min(value, 100)}%` }}
      />
    </div>
  );
}

export function SystemControl() {
  const queryClient = useQueryClient();
  const [actionLoading, setActionLoading] = useState<string | null>(null);

  const { data: resources, isLoading } = useQuery({
    queryKey: ['system-resources'],
    queryFn: api.getSystemResources,
    refetchInterval: 5000,
  });

  const startQueueMutation = useMutation({
    mutationFn: api.startQueueWorker,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['queue-stats'] }),
  });

  const stopQueueMutation = useMutation({
    mutationFn: api.stopQueueWorker,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['queue-stats'] }),
  });

  const restartBaileysMutation = useMutation({
    mutationFn: api.restartBaileys,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['baileys-status'] }),
  });

  const handleAction = async (action: string, mutation: any) => {
    setActionLoading(action);
    await mutation.mutateAsync();
    setActionLoading(null);
  };

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
          <h2 className="text-2xl font-bold text-slate-100">System Control</h2>
          <p className="text-slate-400 mt-1">Monitor system resources and control services</p>
        </div>
        <button
          onClick={() => queryClient.invalidateQueries({ queryKey: ['system-resources'] })}
          className="flex items-center gap-2 px-4 py-2 bg-slate-700 hover:bg-slate-600 text-slate-200 rounded-lg transition-colors"
        >
          <RefreshCw className="w-4 h-4" />
          Refresh
        </button>
      </div>

      {/* Resource Usage Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* CPU */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="bg-dark-800 border border-slate-700 rounded-xl p-6"
        >
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-3">
              <div className="p-3 bg-blue-500/20 rounded-lg">
                <Cpu className="w-6 h-6 text-blue-400" />
              </div>
              <div>
                <p className="text-slate-400">CPU Usage</p>
                <p className="text-2xl font-bold text-slate-100">{(resources?.cpu_percent ?? 0).toFixed(1)}%</p>
              </div>
            </div>
          </div>
            <ProgressBar 
            value={resources?.cpu_percent ?? 0} 
            color={(resources?.cpu_percent ?? 0) > 80 ? 'red' : (resources?.cpu_percent ?? 0) > 60 ? 'yellow' : 'green'}
          />
        </motion.div>

        {/* Memory */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="bg-dark-800 border border-slate-700 rounded-xl p-6"
        >
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-3">
              <div className="p-3 bg-purple-500/20 rounded-lg">
                <MemoryStick className="w-6 h-6 text-purple-400" />
              </div>
              <div>
                <p className="text-slate-400">Memory Usage</p>
                <p className="text-2xl font-bold text-slate-100">{(resources?.memory?.percent ?? 0).toFixed(1)}%</p>
              </div>
            </div>
          </div>
          
          <ProgressBar 
            value={resources?.memory?.percent ?? 0}
            color={(resources?.memory?.percent ?? 0) > 80 ? 'red' : (resources?.memory?.percent ?? 0) > 60 ? 'yellow' : 'green'}
          />
          
          <p className="text-sm text-slate-400 mt-2">
            {formatBytes(resources?.memory.used || 0)} / {formatBytes(resources?.memory.total || 0)}
          </p>
        </motion.div>

        {/* Disk */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
          className="bg-dark-800 border border-slate-700 rounded-xl p-6"
        >
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-3">
              <div className="p-3 bg-yellow-500/20 rounded-lg">
                <HardDrive className="w-6 h-6 text-yellow-400" />
              </div>
              <div>
                <p className="text-slate-400">Disk Usage</p>
                <p className="text-2xl font-bold text-slate-100">{(resources?.disk?.percent ?? 0).toFixed(1)}%</p>
              </div>
            </div>
          </div>
          
          <ProgressBar 
            value={resources?.disk?.percent ?? 0}
            color={(resources?.disk?.percent ?? 0) > 80 ? 'red' : (resources?.disk?.percent ?? 0) > 60 ? 'yellow' : 'green'}
          />
          
          <p className="text-sm text-slate-400 mt-2">
            {formatBytes(resources?.disk?.used ?? 0)} / {formatBytes(resources?.disk?.total ?? 0)}
          </p>
        </motion.div>
      </div>

      {/* Service Controls */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.3 }}
        className="bg-dark-800 border border-slate-700 rounded-xl p-6"
      >
        <h3 className="text-lg font-semibold text-slate-100 mb-4">Service Controls</h3>
        
        <div className="space-y-4">
          {/* Queue Worker */}
          <div className="flex items-center justify-between p-4 rounded-lg bg-slate-700/30">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-slate-600 rounded-lg">
                <Server className="w-5 h-5 text-slate-300" />
              </div>
              <div>
                <p className="font-medium text-slate-200">Queue Worker</p>
                <p className="text-sm text-slate-400">Process pending messages in queue</p>
              </div>
            </div>
            
            <div className="flex gap-2">
              <button
                onClick={() => handleAction('start-queue', startQueueMutation)}
                disabled={actionLoading === 'start-queue'}
                className="flex items-center gap-2 px-4 py-2 bg-green-500/20 hover:bg-green-500/30 text-green-400 border border-green-500/30 rounded-lg transition-colors disabled:opacity-50"
              >
                {actionLoading === 'start-queue' ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : (
                  <Play className="w-4 h-4" />
                )}
                Start
              </button>
              
              <button
                onClick={() => handleAction('stop-queue', stopQueueMutation)}
                disabled={actionLoading === 'stop-queue'}
                className="flex items-center gap-2 px-4 py-2 bg-red-500/20 hover:bg-red-500/30 text-red-400 border border-red-500/30 rounded-lg transition-colors disabled:opacity-50"
              >
                {actionLoading === 'stop-queue' ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : (
                  <Square className="w-4 h-4" />
                )}
                Stop
              </button>
            </div>
          </div>

          {/* Baileys */}
          <div className="flex items-center justify-between p-4 rounded-lg bg-slate-700/30">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-slate-600 rounded-lg">
                <Activity className="w-5 h-5 text-slate-300" />
              </div>
              <div>
                <p className="font-medium text-slate-200">Baileys Service</p>
                <p className="text-sm text-slate-400">Restart WhatsApp Web connection</p>
              </div>
            </div>
            
            <button
              onClick={() => handleAction('restart-baileys', restartBaileysMutation)}
              disabled={actionLoading === 'restart-baileys'}
              className="flex items-center gap-2 px-4 py-2 bg-brand-500/20 hover:bg-brand-500/30 text-brand-400 border border-brand-500/30 rounded-lg transition-colors disabled:opacity-50"
            >
              {actionLoading === 'restart-baileys' ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <RefreshCw className="w-4 h-4" />
              )}
              Restart
            </button>
          </div>
        </div>
      </motion.div>
    </div>
  );
}

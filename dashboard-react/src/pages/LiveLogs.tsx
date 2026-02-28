import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { motion } from 'framer-motion';
import {
  FileText,
  RefreshCw,
  Filter,
  AlertTriangle,
  Info,
  AlertCircle,
  Bug,
} from 'lucide-react';
import { api } from '../services/api';
import { LoadingState } from '../components/ui/LoadingState';
import { REFETCH_INTERVALS, LIMITS } from '../constants';
import type { LogEntry } from '../types';

const levels = [
  { value: '', label: 'All Levels' },
  { value: 'DEBUG', label: 'Debug' },
  { value: 'INFO', label: 'Info' },
  { value: 'WARNING', label: 'Warning' },
  { value: 'ERROR', label: 'Error' },
];

const sources = [
  { value: '', label: 'All Sources' },
  { value: 'fastapi', label: 'FastAPI' },
  { value: 'baileys', label: 'Baileys' },
  { value: 'system', label: 'System' },
  { value: 'gateway', label: 'Gateway' },
];

export function LiveLogs() {
  const [level, setLevel] = useState('');
  const [source, setSource] = useState('');
  const [autoRefresh, setAutoRefresh] = useState(true);

  const { data: logs, isLoading, refetch } = useQuery({
    queryKey: ['logs', level, source],
    queryFn: () => api.getLogs({ level: level || undefined, source: source || undefined, limit: LIMITS.MAX_LOGS }),
    refetchInterval: autoRefresh ? REFETCH_INTERVALS.LIVE_LOGS : false,
  });

  const getLevelIcon = (level: string) => {
    switch (level) {
      case 'ERROR':
        return <AlertCircle className="w-3.5 h-3.5" style={{ color: 'var(--danger)' }} />;
      case 'WARNING':
        return <AlertTriangle className="w-3.5 h-3.5" style={{ color: 'var(--warning)' }} />;
      case 'DEBUG':
        return <Bug className="w-3.5 h-3.5" style={{ color: 'var(--info)' }} />;
      default:
        return <Info className="w-3.5 h-3.5" style={{ color: 'var(--brand-accent)' }} />;
    }
  };

  const getLevelStyle = (level: string) => {
    switch (level) {
      case 'ERROR':
        return { bg: 'var(--danger-soft)', color: 'var(--danger)', border: 'var(--danger-soft-border)' };
      case 'WARNING':
        return { bg: 'var(--warning-soft)', color: 'var(--warning)', border: 'var(--warning-soft-border)' };
      case 'DEBUG':
        return { bg: 'var(--info-soft)', color: 'var(--info)', border: 'var(--info-soft-border)' };
      default:
        return { bg: 'var(--brand-soft)', color: 'var(--brand-accent)', border: 'var(--brand-soft-border)' };
    }
  };

  return (
    <div className="space-y-5">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold" style={{ color: 'var(--text-primary)' }}>
            Live Logs
          </h2>
          <p className="text-sm mt-0.5" style={{ color: 'var(--text-tertiary)' }}>
            Real-time application logs and events
          </p>
        </div>
        <div className="flex items-center gap-2">
          <label className="flex items-center gap-2 cursor-pointer">
            <button
              onClick={() => setAutoRefresh(!autoRefresh)}
              className={`toggle ${autoRefresh ? 'active' : ''}`}
              role="switch"
              aria-checked={autoRefresh}
              aria-label="Enable automatic refresh"
            />
            <span className="text-xs" style={{ color: 'var(--text-secondary)' }}>Auto</span>
          </label>

          <button onClick={() => refetch()} className="btn-secondary">
            <RefreshCw className="w-4 h-4" />
            Refresh
          </button>
        </div>
      </div>

      {/* Filters */}
      <motion.div
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        className="card p-4"
      >
        <div className="flex items-center gap-3 flex-wrap">
          <div className="flex items-center gap-1.5">
            <Filter className="w-3.5 h-3.5" style={{ color: 'var(--text-tertiary)' }} />
            <span className="text-xs font-medium" style={{ color: 'var(--text-tertiary)' }}>Filters:</span>
          </div>

          <select
            value={level}
            onChange={(e) => setLevel(e.target.value)}
            className="input w-auto text-xs"
            aria-label="Filter by log level"
          >
            {levels.map((l) => (
              <option key={l.value} value={l.value}>{l.label}</option>
            ))}
          </select>

          <select
            value={source}
            onChange={(e) => setSource(e.target.value)}
            className="input w-auto text-xs"
            aria-label="Filter by log source"
          >
            {sources.map((s) => (
              <option key={s.value} value={s.value}>{s.label}</option>
            ))}
          </select>
        </div>
      </motion.div>

      {/* Logs */}
      <motion.div
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.1 }}
        className="card overflow-hidden"
      >
        <div className="max-h-[600px] overflow-y-auto">
          {isLoading ? (
            <div className="py-12">
              <LoadingState size="md" />
            </div>
          ) : (
            <div>
              {logs?.logs?.map((log: LogEntry) => {
                const ls = getLevelStyle(log.level);
                return (
                  <div
                    key={log.id}
                    className="px-4 py-3 transition-colors"
                    style={{ borderBottom: '1px solid var(--border-subtle)' }}
                    onMouseEnter={(e) => (e.currentTarget.style.background = 'var(--bg-input)')}
                    onMouseLeave={(e) => (e.currentTarget.style.background = 'transparent')}
                  >
                    <div className="flex items-start gap-3">
                      <div className="flex-shrink-0 mt-0.5">
                        {getLevelIcon(log.level)}
                      </div>

                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 mb-0.5">
                          <span
                            className="px-1.5 py-0.5 text-[10px] font-semibold rounded"
                            style={{
                              background: ls.bg,
                              color: ls.color,
                              border: `1px solid ${ls.border}`,
                            }}
                          >
                            {log.level}
                          </span>

                          <span className="text-[10px]" style={{ color: 'var(--text-tertiary)' }}>
                            {new Date(log.timestamp).toLocaleString()}
                          </span>

                          {log.source && (
                            <span className="text-[10px]" style={{ color: 'var(--text-tertiary)' }}>
                              [{log.source}]
                            </span>
                          )}
                        </div>

                        <p className="text-xs font-mono" style={{ color: 'var(--text-tertiary)' }}>
                          {log.logger}
                        </p>
                        <p className="text-sm mt-0.5" style={{ color: 'var(--text-primary)' }}>
                          {log.message}
                        </p>
                      </div>
                    </div>
                  </div>
                );
              })}

              {logs?.logs?.length === 0 && (
                <div className="py-12 text-center" style={{ color: 'var(--text-tertiary)' }}>
                  <div className="flex flex-col items-center gap-2">
                    <FileText className="w-10 h-10 opacity-40" />
                    <p className="text-sm">No logs found</p>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      </motion.div>
    </div>
  );
}

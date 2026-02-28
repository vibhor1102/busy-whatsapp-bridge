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
  Bug
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
        return <AlertCircle className="w-4 h-4 text-red-400" />;
      case 'WARNING':
        return <AlertTriangle className="w-4 h-4 text-yellow-400" />;
      case 'DEBUG':
        return <Bug className="w-4 h-4 text-purple-400" />;
      default:
        return <Info className="w-4 h-4 text-blue-400" />;
    }
  };

  const getLevelColor = (level: string) => {
    switch (level) {
      case 'ERROR':
        return 'bg-red-500/10 text-red-400 border-red-500/30';
      case 'WARNING':
        return 'bg-yellow-500/10 text-yellow-400 border-yellow-500/30';
      case 'DEBUG':
        return 'bg-purple-500/10 text-purple-400 border-purple-500/30';
      default:
        return 'bg-blue-500/10 text-blue-400 border-blue-500/30';
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-slate-100">Live Logs</h2>
          <p className="text-slate-400 mt-1">Real-time application logs and events</p>
        </div>
        <div className="flex items-center gap-3">
          <label className="flex items-center gap-2 text-slate-300">
            <input
              type="checkbox"
              checked={autoRefresh}
              onChange={(e) => setAutoRefresh(e.target.checked)}
              className="w-4 h-4 rounded border-slate-600 text-brand-500 focus:ring-brand-500"
              aria-label="Enable automatic refresh"
            />
            Auto-refresh
          </label>
          
          <button
            onClick={() => refetch()}
            className="flex items-center gap-2 px-4 py-2 bg-slate-700 hover:bg-slate-600 text-slate-200 rounded-lg transition-colors"
          >
            <RefreshCw className="w-4 h-4" />
            Refresh
          </button>
        </div>
      </div>

      {/* Filters */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="bg-dark-800 border border-slate-700 rounded-xl p-4"
      >
        <div className="flex items-center gap-4 flex-wrap">
          <div className="flex items-center gap-2">
            <Filter className="w-4 h-4 text-slate-400" />
            <span className="text-slate-400">Filters:</span>
          </div>
          
          <select
            value={level}
            onChange={(e) => setLevel(e.target.value)}
            className="px-3 py-2 bg-slate-700 border border-slate-600 rounded-lg text-slate-200 focus:outline-none focus:ring-2 focus:ring-brand-500"
            aria-label="Filter by log level"
          >
            {levels.map((l) => (
              <option key={l.value} value={l.value}>{l.label}</option>
            ))}
          </select>
          
          <select
            value={source}
            onChange={(e) => setSource(e.target.value)}
            className="px-3 py-2 bg-slate-700 border border-slate-600 rounded-lg text-slate-200 focus:outline-none focus:ring-2 focus:ring-brand-500"
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
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.1 }}
        className="bg-dark-800 border border-slate-700 rounded-xl overflow-hidden"
      >
        <div className="max-h-[600px] overflow-y-auto">
          {isLoading ? (
            <div className="py-12">
              <LoadingState size="md" />
            </div>
          ) : (
            <div className="divide-y divide-slate-700">
              {logs?.logs?.map((log: LogEntry) => (
                <div key={log.id} className="p-4 hover:bg-slate-700/20 transition-colors">
                  <div className="flex items-start gap-4">
                    <div className="flex-shrink-0 mt-0.5">
                      {getLevelIcon(log.level)}
                    </div>
                    
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-3 mb-1">
                        <span className={`px-2 py-0.5 text-xs font-medium rounded border ${getLevelColor(log.level)}`}>
                          {log.level}
                        </span>
                        
                        <span className="text-xs text-slate-500">
                          {new Date(log.timestamp).toLocaleString()}
                        </span>
                        
                        {log.source && (
                          <span className="text-xs text-slate-500">
                            [{log.source}]
                          </span>
                        )}
                      </div>
                      
                      <p className="text-sm text-slate-300 font-mono">{log.logger}</p>
                      <p className="text-slate-200 mt-1">{log.message}</p>
                    </div>
                  </div>
                </div>
              ))}
              
              {logs?.logs?.length === 0 && (
                <div className="py-12 text-center text-slate-400">
                  <div className="flex flex-col items-center gap-2">
                    <FileText className="w-12 h-12 opacity-50" />
                    <p>No logs found</p>
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

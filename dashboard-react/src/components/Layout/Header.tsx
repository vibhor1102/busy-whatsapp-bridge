import { useLocation } from 'react-router-dom';
import { RefreshCw, Database, Wifi, Inbox, AlertCircle } from 'lucide-react';
import { useDashboardStore } from '../../stores/dashboardStore';
import { useSystemStore, selectIsBaileysConnected } from '../../stores/systemStore';
import { useQueueStore } from '../../stores/queueStore';
import { api } from '../../services/api';

interface HeaderProps {
  onMenuClick?: () => void;
}

export function Header({ onMenuClick }: HeaderProps) {
  const location = useLocation();
  const stats = useDashboardStore((state) => state.stats);
  const baileysConnected = useSystemStore(selectIsBaileysConnected);
  const queueStats = useQueueStore((state) => state.stats);

  const getPageTitle = () => {
    const path = location.pathname;
    switch (path) {
      case '/': return 'Overview';
      case '/whatsapp': return 'WhatsApp Manager';
      case '/queue': return 'Message Queue';
      case '/reminders': return 'Payment Reminders';
      case '/logs': return 'Live Logs';
      case '/system': return 'System Control';
      case '/settings': return 'Settings';
      default: return 'Dashboard';
    }
  };

  const handleRefresh = async () => {
    try {
      const newStats = await api.getDashboardStats();
      useDashboardStore.getState().setStats(newStats);
    } catch (error) {
      console.error('Failed to refresh:', error);
    }
  };

  return (
    <header className="h-16 bg-dark-800 border-b border-slate-700 flex items-center justify-between px-6 sticky top-0 z-40">
      {/* Left Section */}
      <div className="flex items-center gap-4">
        {onMenuClick && (
          <button
            onClick={onMenuClick}
            className="p-2 rounded-lg hover:bg-slate-700 transition-colors text-slate-400 hover:text-slate-200 lg:hidden focus:outline-none focus:ring-2 focus:ring-brand-500"
            aria-label="Toggle navigation menu"
            title="Toggle menu"
          >
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
            </svg>
          </button>
        )}
        <h1 className="text-xl font-semibold text-slate-100">{getPageTitle()}</h1>
      </div>

      {/* Right Section - Status Pills */}
      <div className="flex items-center gap-3">
        {/* WhatsApp Status */}
        <div
          className={`flex items-center gap-2 px-3 py-1.5 rounded-full text-sm font-medium ${
            baileysConnected
              ? 'bg-green-500/20 text-green-400 border border-green-500/30'
              : 'bg-red-500/20 text-red-400 border border-red-500/30'
          }`}
        >
          <Wifi className="w-4 h-4" />
          <span>{baileysConnected ? 'WhatsApp Online' : 'WhatsApp Offline'}</span>
        </div>

        {/* Database Status */}
        <div
          className={`flex items-center gap-2 px-3 py-1.5 rounded-full text-sm font-medium ${
            stats?.database_connected
              ? 'bg-green-500/20 text-green-400 border border-green-500/30'
              : 'bg-red-500/20 text-red-400 border border-red-500/30'
          }`}
        >
          <Database className="w-4 h-4" />
          <span>{stats?.database_connected ? 'DB Connected' : 'DB Error'}</span>
          {!stats?.database_connected && stats?.database_error && (
            <div className="group relative">
              <AlertCircle className="w-4 h-4" />
              <div className="absolute right-0 top-full mt-2 w-64 p-3 bg-slate-800 border border-slate-700 rounded-lg shadow-xl opacity-0 group-hover:opacity-100 transition-opacity z-50">
                <p className="text-xs text-slate-400">{stats.database_error}</p>
              </div>
            </div>
          )}
        </div>

        {/* Queue Status */}
        {queueStats && queueStats.pending > 0 && (
          <div className="flex items-center gap-2 px-3 py-1.5 rounded-full text-sm font-medium bg-brand-500/20 text-brand-400 border border-brand-500/30">
            <Inbox className="w-4 h-4" />
            <span>{queueStats.pending} Pending</span>
          </div>
        )}

        {/* Refresh Button */}
        <button
          onClick={handleRefresh}
          className="p-2 rounded-lg hover:bg-slate-700 transition-colors text-slate-400 hover:text-slate-200 focus:outline-none focus:ring-2 focus:ring-brand-500"
          title="Refresh Data"
          aria-label="Refresh dashboard data"
        >
          <RefreshCw className="w-5 h-5" aria-hidden="true" />
        </button>
      </div>
    </header>
  );
}

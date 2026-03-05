import { useState, useEffect } from 'react';
import { useLocation } from 'react-router-dom';
import { RefreshCw, Database, Wifi, Inbox, AlertCircle, Building2 } from 'lucide-react';
import { useDashboardStore } from '../../stores/dashboardStore';
import { useSystemStore, selectIsBaileysConnected } from '../../stores/systemStore';
import { useQueueStore } from '../../stores/queueStore';
import { api, type CompanyInfo } from '../../services/api';

interface HeaderProps {
  onMenuClick?: () => void;
}

export function Header({ onMenuClick }: HeaderProps) {
  const location = useLocation();
  const stats = useDashboardStore((state) => state.stats);
  const baileysConnected = useSystemStore(selectIsBaileysConnected);
  const setBaileysStatus = useSystemStore((state) => state.setBaileysStatus);
  const queueStats = useQueueStore((state) => state.stats);

  const getPageTitle = () => {
    const path = location.pathname.replace('/dashboard', '');
    switch (path) {
      case '/': case '': return 'Overview';
      case '/whatsapp': return 'WhatsApp';
      case '/queue': return 'Message Queue';
      case '/reminders': return 'Payment Reminders';
      case '/logs': return 'Live Logs';
      case '/system': return 'System';
      case '/settings': return 'Settings';
      default: return 'Dashboard';
    }
  };

  const [companies, setCompanies] = useState<CompanyInfo[]>([]);
  const [activeCompany, setActiveCompany] = useState(api.getCompanyId());

  useEffect(() => {
    api.getCompanies().then(res => {
      setCompanies(res.companies);
      if (res.companies.length > 0) {
        const current = api.getCompanyId();
        const chosen = res.companies.find(c => c.id === current)?.id || res.companies[0].id;
        if (chosen !== current) {
          api.setCompanyId(chosen);
        }
        setActiveCompany(chosen);
      }
    }).catch(console.error);
  }, []);

  const handleCompanyChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const selected = e.target.value;
    setActiveCompany(selected);
    api.setCompanyId(selected);
    window.location.reload();
  };

  const handleRefresh = async () => {
    try {
      const [newStats, newBaileysStatus] = await Promise.all([
        api.getDashboardStats(),
        api.getBaileysStatus(),
      ]);
      useDashboardStore.getState().setStats(newStats);
      setBaileysStatus(newBaileysStatus);
    } catch (error) {
      console.error('Failed to refresh:', error);
    }
  };

  return (
    <header
      className="h-14 flex items-center justify-between px-6 sticky top-0 z-40 backdrop-blur-xl border-b"
      style={{
        background: 'var(--bg-header)',
        borderColor: 'var(--border-default)',
      }}
    >
      {/* Left Section */}
      <div className="flex items-center gap-4">
        {onMenuClick && (
          <button
            onClick={onMenuClick}
            className="p-2 rounded-lg transition-colors lg:hidden"
            style={{ color: 'var(--text-tertiary)' }}
            aria-label="Toggle navigation menu"
            title="Toggle menu"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
            </svg>
          </button>
        )}
        <h1
          className="text-lg font-semibold"
          style={{ color: 'var(--text-primary)' }}
        >
          {getPageTitle()}
        </h1>

        {/* Company Selector */}
        {companies.length > 0 && (
          <div className="hidden md:flex items-center ml-4 pl-4 border-l" style={{ borderColor: 'var(--border-default)' }}>
            <Building2 className="w-4 h-4 mr-2" style={{ color: 'var(--text-tertiary)' }} />
            <select
              value={activeCompany}
              onChange={handleCompanyChange}
              className="input py-1 text-sm bg-transparent border-none appearance-none cursor-pointer focus:ring-0"
              style={{ color: 'var(--text-secondary)' }}
            >
              {companies.map(c => (
                <option key={c.id} value={c.id}>{c.name}</option>
              ))}
            </select>
          </div>
        )}
      </div>

      {/* Right Section - Status Pills */}
      <div className="flex items-center gap-2">
        {/* WhatsApp Status */}
        <div
          className="badge"
          style={{
            background: baileysConnected ? 'var(--success-soft)' : 'var(--danger-soft)',
            color: baileysConnected ? 'var(--success)' : 'var(--danger)',
            borderColor: baileysConnected ? 'var(--success-soft-border)' : 'var(--danger-soft-border)',
          }}
        >
          <Wifi className="w-3.5 h-3.5" />
          <span className="hidden sm:inline">{baileysConnected ? 'Online' : 'Offline'}</span>
        </div>

        {/* Database Status */}
        <div
          className="badge"
          style={{
            background: stats?.database_connected ? 'var(--success-soft)' : 'var(--danger-soft)',
            color: stats?.database_connected ? 'var(--success)' : 'var(--danger)',
            borderColor: stats?.database_connected ? 'var(--success-soft-border)' : 'var(--danger-soft-border)',
          }}
        >
          <Database className="w-3.5 h-3.5" />
          <span className="hidden sm:inline">{stats?.database_connected ? 'DB' : 'DB Err'}</span>
          {!stats?.database_connected && stats?.database_error && (
            <div className="group relative">
              <AlertCircle className="w-3.5 h-3.5" />
              <div
                className="absolute right-0 top-full mt-2 w-64 p-3 rounded-lg shadow-xl opacity-0 group-hover:opacity-100 transition-opacity z-50"
                style={{
                  background: 'var(--bg-card)',
                  border: '1px solid var(--border-default)',
                  color: 'var(--text-secondary)',
                }}
              >
                <p className="text-xs">{stats.database_error}</p>
              </div>
            </div>
          )}
        </div>

        {/* Queue Status */}
        {queueStats && queueStats.pending > 0 && (
          <div
            className="badge"
            style={{
              background: 'var(--brand-soft)',
              color: 'var(--brand-accent)',
              borderColor: 'var(--brand-soft-border)',
            }}
          >
            <Inbox className="w-3.5 h-3.5" />
            <span>{queueStats.pending}</span>
          </div>
        )}

        {/* Refresh Button */}
        <button
          onClick={handleRefresh}
          className="p-1.5 rounded-lg transition-colors"
          style={{ color: 'var(--text-tertiary)' }}
          onMouseEnter={(e) => (e.currentTarget.style.background = 'var(--bg-input)')}
          onMouseLeave={(e) => (e.currentTarget.style.background = 'transparent')}
          title="Refresh Data"
          aria-label="Refresh dashboard data"
        >
          <RefreshCw className="w-4 h-4" aria-hidden="true" />
        </button>
      </div>
    </header>
  );
}

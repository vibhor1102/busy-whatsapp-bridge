import { useEffect } from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  MessageSquare,
  Inbox,
  Database,
  CheckCircle,
  TrendingUp,
  AlertTriangle,
  Bell,
  ArrowRight,
} from 'lucide-react';
import { motion } from 'framer-motion';
import { api } from '../services/api';
import { useDashboardStore } from '../stores/dashboardStore';
import { LoadingState } from '../components/ui/LoadingState';
import { REFETCH_INTERVALS } from '../constants';

interface StatCardProps {
  title: string;
  value: string | number;
  subtitle?: string;
  icon: React.ElementType;
  status: 'success' | 'warning' | 'danger' | 'info' | 'brand';
  trend?: { value: number; isPositive: boolean };
  delay?: number;
}

function StatCard({ title, value, subtitle, icon: Icon, status, trend, delay = 0 }: StatCardProps) {
  const statusStyles = {
    success: { color: 'var(--success)', bg: 'var(--success-soft)', border: 'var(--success-soft-border)' },
    warning: { color: 'var(--warning)', bg: 'var(--warning-soft)', border: 'var(--warning-soft-border)' },
    danger: { color: 'var(--danger)', bg: 'var(--danger-soft)', border: 'var(--danger-soft-border)' },
    info: { color: 'var(--info)', bg: 'var(--info-soft)', border: 'var(--info-soft-border)' },
    brand: { color: 'var(--brand-accent)', bg: 'var(--brand-soft)', border: 'var(--brand-soft-border)' },
  };

  const s = statusStyles[status];

  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay, duration: 0.3 }}
      className="card p-5"
    >
      <div className="flex items-start justify-between">
        <div className="flex-1 min-w-0">
          <p className="text-xs font-medium uppercase tracking-wider" style={{ color: 'var(--text-tertiary)' }}>
            {title}
          </p>
          <p className="text-2xl font-bold mt-1.5" style={{ color: 'var(--text-primary)' }}>
            {value}
          </p>
          {subtitle && (
            <p className="text-xs mt-1" style={{ color: 'var(--text-tertiary)' }}>
              {subtitle}
            </p>
          )}
          {trend && (
            <div className="flex items-center gap-1 mt-2 text-xs font-medium" style={{ color: trend.isPositive ? 'var(--success)' : 'var(--danger)' }}>
              <TrendingUp className={`w-3.5 h-3.5 ${!trend.isPositive && 'rotate-180'}`} />
              <span>{trend.value}%</span>
            </div>
          )}
        </div>
        <div
          className="p-2.5 rounded-xl flex-shrink-0"
          style={{ background: s.bg, border: `1px solid ${s.border}` }}
        >
          <Icon className="w-5 h-5" style={{ color: s.color }} />
        </div>
      </div>
    </motion.div>
  );
}

export function Overview() {
  const setStats = useDashboardStore((state) => state.setStats);

  const { data: stats, isLoading } = useQuery({
    queryKey: ['dashboard-stats'],
    queryFn: () => api.getDashboardStats(),
    refetchInterval: REFETCH_INTERVALS.DASHBOARD_STATS,
  });

  useEffect(() => {
    if (stats) {
      setStats(stats);
    }
  }, [stats, setStats]);

  if (isLoading) {
    return <LoadingState size="lg" fullPage />;
  }

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div>
        <h2 className="text-2xl font-bold" style={{ color: 'var(--text-primary)' }}>
          Dashboard
        </h2>
        <p className="text-sm mt-1" style={{ color: 'var(--text-tertiary)' }}>
          Real-time system monitoring and statistics
        </p>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          title="WhatsApp"
          value={stats?.whatsapp.state === 'connected' ? 'Connected' : 'Disconnected'}
          icon={MessageSquare}
          status={stats?.whatsapp.state === 'connected' ? 'success' : 'danger'}
          delay={0}
        />
        <StatCard
          title="Queue"
          value={stats?.queue.pending || 0}
          subtitle={`${stats?.queue.retrying || 0} retrying`}
          icon={Inbox}
          status={(stats?.queue.pending || 0) > 0 ? 'warning' : 'success'}
          delay={0.05}
        />
        <StatCard
          title="Sent Today"
          value={stats?.messages.sent_today || 0}
          subtitle={`${stats?.messages.failed_today || 0} failed`}
          icon={CheckCircle}
          status="brand"
          delay={0.1}
        />
        <StatCard
          title="Database"
          value={stats?.database_connected ? 'Connected' : 'Error'}
          icon={Database}
          status={stats?.database_connected ? 'success' : 'danger'}
          delay={0.15}
        />
      </div>

      {/* Two Column Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
        {/* Quick Actions */}
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
          className="card p-5"
        >
          <h3 className="text-sm font-semibold mb-4" style={{ color: 'var(--text-primary)' }}>
            Quick Actions
          </h3>
          <div className="space-y-2.5">
            <a
              href="/dashboard/reminders"
              className="flex items-center gap-3 p-3.5 rounded-xl transition-all group"
              style={{
                background: 'var(--brand-soft)',
                border: '1px solid var(--brand-soft-border)',
              }}
              onMouseEnter={(e) => (e.currentTarget.style.borderColor = 'var(--brand-accent)')}
              onMouseLeave={(e) => (e.currentTarget.style.borderColor = 'var(--brand-soft-border)')}
            >
              <div
                className="p-2 rounded-lg"
                style={{ background: 'var(--brand-accent)', color: 'white' }}
              >
                <Bell className="w-4 h-4" />
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium" style={{ color: 'var(--text-primary)' }}>
                  Send Payment Reminders
                </p>
                <p className="text-xs" style={{ color: 'var(--text-tertiary)' }}>
                  Send reminders to selected parties
                </p>
              </div>
              <ArrowRight className="w-4 h-4 opacity-0 group-hover:opacity-100 transition-opacity" style={{ color: 'var(--brand-accent)' }} />
            </a>

            <a
              href="/dashboard/queue"
              className="flex items-center gap-3 p-3.5 rounded-xl transition-all group"
              style={{
                background: 'var(--bg-input)',
                border: '1px solid var(--border-default)',
              }}
              onMouseEnter={(e) => (e.currentTarget.style.borderColor = 'var(--border-strong)')}
              onMouseLeave={(e) => (e.currentTarget.style.borderColor = 'var(--border-default)')}
            >
              <div
                className="p-2 rounded-lg"
                style={{ background: 'var(--bg-input-hover)', color: 'var(--text-secondary)' }}
              >
                <Inbox className="w-4 h-4" />
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium" style={{ color: 'var(--text-primary)' }}>
                  Message Queue
                </p>
                <p className="text-xs" style={{ color: 'var(--text-tertiary)' }}>
                  {stats?.queue.pending || 0} messages pending
                </p>
              </div>
              <ArrowRight className="w-4 h-4 opacity-0 group-hover:opacity-100 transition-opacity" style={{ color: 'var(--text-tertiary)' }} />
            </a>

            <a
              href="/dashboard/whatsapp"
              className="flex items-center gap-3 p-3.5 rounded-xl transition-all group"
              style={{
                background: 'var(--bg-input)',
                border: '1px solid var(--border-default)',
              }}
              onMouseEnter={(e) => (e.currentTarget.style.borderColor = 'var(--border-strong)')}
              onMouseLeave={(e) => (e.currentTarget.style.borderColor = 'var(--border-default)')}
            >
              <div
                className="p-2 rounded-lg"
                style={{ background: 'var(--bg-input-hover)', color: 'var(--text-secondary)' }}
              >
                <MessageSquare className="w-4 h-4" />
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium" style={{ color: 'var(--text-primary)' }}>
                  WhatsApp Status
                </p>
                <p className="text-xs" style={{ color: 'var(--text-tertiary)' }}>
                  {stats?.whatsapp.state === 'connected' ? 'Connected and ready' : 'Needs attention'}
                </p>
              </div>
              <ArrowRight className="w-4 h-4 opacity-0 group-hover:opacity-100 transition-opacity" style={{ color: 'var(--text-tertiary)' }} />
            </a>
          </div>
        </motion.div>

        {/* System Status */}
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.25 }}
          className="card p-5"
        >
          <h3 className="text-sm font-semibold mb-4" style={{ color: 'var(--text-primary)' }}>
            System Status
          </h3>

          <div className="space-y-2">
            {[
              {
                label: 'WhatsApp Connection',
                ok: stats?.whatsapp.state === 'connected',
                statusText: stats?.whatsapp.state === 'connected' ? 'Online' : 'Offline',
              },
              {
                label: 'Queue Worker',
                ok: stats?.queue.worker_running,
                statusText: stats?.queue.worker_running ? 'Running' : 'Stopped',
              },
              {
                label: 'Database',
                ok: stats?.database_connected,
                statusText: stats?.database_connected ? 'Connected' : 'Error',
              },
            ].map((item) => (
              <div
                key={item.label}
                className="flex items-center justify-between p-3 rounded-lg"
                style={{ background: 'var(--bg-input)' }}
              >
                <div className="flex items-center gap-2.5">
                  <div
                    className="w-2 h-2 rounded-full"
                    style={{
                      backgroundColor: item.ok ? 'var(--success)' : 'var(--danger)',
                      boxShadow: item.ok ? '0 0 6px rgba(16, 185, 129, 0.4)' : 'none',
                    }}
                  />
                  <span className="text-sm" style={{ color: 'var(--text-secondary)' }}>
                    {item.label}
                  </span>
                </div>
                <span
                  className="text-xs font-medium"
                  style={{ color: item.ok ? 'var(--success)' : 'var(--danger)' }}
                >
                  {item.statusText}
                </span>
              </div>
            ))}
          </div>

          {!stats?.database_connected && stats?.database_error && (
            <div
              className="mt-4 p-3 rounded-lg flex items-start gap-2.5"
              style={{
                background: 'var(--danger-soft)',
                border: '1px solid var(--danger-soft-border)',
              }}
            >
              <AlertTriangle className="w-4 h-4 flex-shrink-0 mt-0.5" style={{ color: 'var(--danger)' }} />
              <div>
                <p className="text-xs font-medium" style={{ color: 'var(--danger)' }}>
                  Database Connection Error
                </p>
                <p className="text-xs mt-0.5" style={{ color: 'var(--text-secondary)' }}>
                  {stats.database_error}
                </p>
              </div>
            </div>
          )}
        </motion.div>
      </div>
    </div>
  );
}

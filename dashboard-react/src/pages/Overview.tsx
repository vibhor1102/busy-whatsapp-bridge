import { useEffect } from 'react';
import { useQuery } from '@tanstack/react-query';
import { 
  MessageSquare, 
  Inbox, 
  Database, 
  CheckCircle, 
  TrendingUp,
  AlertTriangle
} from 'lucide-react';
import { motion } from 'framer-motion';
import { api } from '../services/api';
import { useDashboardStore } from '../stores/dashboardStore';

interface StatCardProps {
  title: string;
  value: string | number;
  subtitle?: string;
  icon: React.ElementType;
  color: 'blue' | 'green' | 'yellow' | 'red' | 'purple';
  trend?: { value: number; isPositive: boolean };
}

function StatCard({ title, value, subtitle, icon: Icon, color, trend }: StatCardProps) {
  const colorClasses = {
    blue: 'bg-blue-500/20 text-blue-400 border-blue-500/30',
    green: 'bg-green-500/20 text-green-400 border-green-500/30',
    yellow: 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30',
    red: 'bg-red-500/20 text-red-400 border-red-500/30',
    purple: 'bg-purple-500/20 text-purple-400 border-purple-500/30',
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className={`p-6 rounded-xl border ${colorClasses[color]} backdrop-blur-sm`}
    >
      <div className="flex items-start justify-between">
        <div>
          <p className="text-sm font-medium opacity-80">{title}</p>
          <p className="text-3xl font-bold mt-2">{value}</p>
          {subtitle && <p className="text-sm mt-1 opacity-70">{subtitle}</p>}
          {trend && (
            <div className={`flex items-center gap-1 mt-2 text-sm ${trend.isPositive ? 'text-green-400' : 'text-red-400'}`}>
              <TrendingUp className={`w-4 h-4 ${!trend.isPositive && 'rotate-180'}`} />
              <span>{trend.value}%</span>
            </div>
          )}
        </div>
        <div className={`p-3 rounded-lg ${colorClasses[color]}`}>
          <Icon className="w-6 h-6" />
        </div>
      </div>
    </motion.div>
  );
}

export function Overview() {
  const setStats = useDashboardStore((state) => state.setStats);
  
  const { data: stats, isLoading } = useQuery({
    queryKey: ['dashboard-stats'],
    queryFn: api.getDashboardStats,
    refetchInterval: 30000,
  });

  useEffect(() => {
    if (stats) {
      setStats(stats);
    }
  }, [stats, setStats]);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-brand-500"></div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-slate-100">Dashboard Overview</h2>
          <p className="text-slate-400 mt-1">Real-time system monitoring and statistics</p>
        </div>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          title="WhatsApp Status"
          value={stats?.whatsapp.state === 'connected' ? 'Connected' : 'Disconnected'}
          icon={MessageSquare}
          color={stats?.whatsapp.state === 'connected' ? 'green' : 'red'}
        />

        <StatCard
          title="Queue Pending"
          value={stats?.queue.pending || 0}
          subtitle={`${stats?.queue.retrying || 0} retrying`}
          icon={Inbox}
          color={(stats?.queue.pending || 0) > 0 ? 'yellow' : 'green'}
        />

        <StatCard
          title="Messages Today"
          value={stats?.messages.sent_today || 0}
          subtitle={`${stats?.messages.failed_today || 0} failed`}
          icon={CheckCircle}
          color="blue"
        />

        <StatCard
          title="Database"
          value={stats?.database_connected ? 'Connected' : 'Error'}
          icon={Database}
          color={stats?.database_connected ? 'green' : 'red'}
        />
      </div>

      {/* System Health */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Quick Actions */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
          className="bg-dark-800 border border-slate-700 rounded-xl p-6"
        >
          <h3 className="text-lg font-semibold text-slate-100 mb-4">Quick Actions</h3>
          <div className="space-y-3">
            <a
              href="/reminders"
              className="flex items-center gap-3 p-4 rounded-lg bg-brand-500/10 border border-brand-500/30 hover:bg-brand-500/20 transition-colors"
            >
              <div className="p-2 bg-brand-500/20 rounded-lg">
                <MessageSquare className="w-5 h-5 text-brand-400" />
              </div>
              <div>
                <p className="font-medium text-slate-100">Send Payment Reminders</p>
                <p className="text-sm text-slate-400">Send reminders to selected parties</p>
              </div>
            </a>

            <a
              href="/queue"
              className="flex items-center gap-3 p-4 rounded-lg bg-slate-700/50 border border-slate-600 hover:bg-slate-700 transition-colors"
            >
              <div className="p-2 bg-slate-600 rounded-lg">
                <Inbox className="w-5 h-5 text-slate-300" />
              </div>
              <div>
                <p className="font-medium text-slate-100">Process Message Queue</p>
                <p className="text-sm text-slate-400">{stats?.queue.pending || 0} messages pending</p>
              </div>
            </a>

            <a
              href="/whatsapp"
              className="flex items-center gap-3 p-4 rounded-lg bg-slate-700/50 border border-slate-600 hover:bg-slate-700 transition-colors"
            >
              <div className="p-2 bg-slate-600 rounded-lg">
                <CheckCircle className="w-5 h-5 text-slate-300" />
              </div>
              <div>
                <p className="font-medium text-slate-100">Check WhatsApp Status</p>
                <p className="text-sm text-slate-400">{stats?.whatsapp.state === 'connected' ? 'Connected and ready' : 'Needs attention'}</p>
              </div>
            </a>
          </div>
        </motion.div>

        {/* Recent Activity */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3 }}
          className="bg-dark-800 border border-slate-700 rounded-xl p-6"
        >
          <h3 className="text-lg font-semibold text-slate-100 mb-4">System Status</h3>
          
          <div className="space-y-4">
            <div className="flex items-center justify-between p-3 rounded-lg bg-slate-700/30">
              <div className="flex items-center gap-3">
                <div className={`w-2.5 h-2.5 rounded-full ${stats?.whatsapp.state === 'connected' ? 'bg-green-500 animate-pulse' : 'bg-red-500'}`} />
                <span className="text-slate-300">WhatsApp Connection</span>
              </div>
              <span className={`text-sm font-medium ${stats?.whatsapp.state === 'connected' ? 'text-green-400' : 'text-red-400'}`}>
                {stats?.whatsapp.state === 'connected' ? 'Online' : 'Offline'}
              </span>
            </div>

            <div className="flex items-center justify-between p-3 rounded-lg bg-slate-700/30">
              <div className="flex items-center gap-3">
                <div className={`w-2.5 h-2.5 rounded-full ${stats?.queue.worker_running ? 'bg-green-500 animate-pulse' : 'bg-yellow-500'}`} />
                <span className="text-slate-300">Queue Worker</span>
              </div>
              <span className={`text-sm font-medium ${stats?.queue.worker_running ? 'text-green-400' : 'text-yellow-400'}`}>
                {stats?.queue.worker_running ? 'Running' : 'Stopped'}
              </span>
            </div>

            <div className="flex items-center justify-between p-3 rounded-lg bg-slate-700/30">
              <div className="flex items-center gap-3">
                <div className={`w-2.5 h-2.5 rounded-full ${stats?.database_connected ? 'bg-green-500' : 'bg-red-500'}`} />
                <span className="text-slate-300">Database</span>
              </div>
              <span className={`text-sm font-medium ${stats?.database_connected ? 'text-green-400' : 'text-red-400'}`}>
                {stats?.database_connected ? 'Connected' : 'Error'}
              </span>
            </div>
          </div>

          {!stats?.database_connected && stats?.database_error && (
            <div className="mt-4 p-4 rounded-lg bg-red-500/10 border border-red-500/30">
              <div className="flex items-start gap-3">
                <AlertTriangle className="w-5 h-5 text-red-400 flex-shrink-0 mt-0.5" />
                <div>
                  <p className="font-medium text-red-400">Database Connection Error</p>
                  <p className="text-sm text-red-300/80 mt-1">{stats.database_error}</p>
                </div>
              </div>
            </div>
          )}
        </motion.div>
      </div>
    </div>
  );
}

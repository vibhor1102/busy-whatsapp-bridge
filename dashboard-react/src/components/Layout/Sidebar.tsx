import { NavLink } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import {
  LayoutDashboard,
  MessageSquare,
  Inbox,
  Bell,
  FileText,
  Settings,
  Cpu,
  ChevronLeft,
  ChevronRight,
  Smartphone,
} from 'lucide-react';
import { useSystemStore, selectIsBaileysConnected } from '../../stores/systemStore';
import { useQueueStore } from '../../stores/queueStore';

interface SidebarProps {
  collapsed: boolean;
  onToggle: () => void;
}

const navItems = [
  { path: '/', label: 'Overview', icon: LayoutDashboard },
  { path: '/whatsapp', label: 'WhatsApp', icon: MessageSquare },
  { path: '/queue', label: 'Message Queue', icon: Inbox },
  { path: '/reminders', label: 'Payment Reminders', icon: Bell },
  { path: '/logs', label: 'Live Logs', icon: FileText },
  { path: '/system', label: 'System', icon: Cpu },
  { path: '/settings', label: 'Settings', icon: Settings },
];

export function Sidebar({ collapsed, onToggle }: SidebarProps) {
  const baileysConnected = useSystemStore(selectIsBaileysConnected);
  const queueStats = useQueueStore((state) => state.stats);

  return (
    <motion.aside
      initial={false}
      animate={{ width: collapsed ? 80 : 260 }}
      transition={{ duration: 0.3, ease: 'easeInOut' }}
      className="fixed left-0 top-0 h-screen bg-dark-800 border-r border-slate-700 flex flex-col z-50"
    >
      {/* Logo Section */}
      <div className="h-16 flex items-center justify-between px-4 border-b border-slate-700">
        <div className="flex items-center gap-3 overflow-hidden">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-brand-400 to-brand-600 flex items-center justify-center flex-shrink-0">
            <Smartphone className="w-5 h-5 text-white" />
          </div>
          <AnimatePresence mode="wait">
            {!collapsed && (
              <motion.span
                initial={{ opacity: 0, x: -10 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: -10 }}
                className="font-semibold text-slate-100 whitespace-nowrap"
              >
                Busy Bridge
              </motion.span>
            )}
          </AnimatePresence>
        </div>
        
        <button
          onClick={onToggle}
          className="p-1.5 rounded-lg hover:bg-slate-700 transition-colors"
        >
          {collapsed ? (
            <ChevronRight className="w-5 h-5 text-slate-400" />
          ) : (
            <ChevronLeft className="w-5 h-5 text-slate-400" />
          )}
        </button>
      </div>

      {/* Navigation */}
      <nav className="flex-1 py-4 px-3 space-y-1">
        {navItems.map((item) => {
          const Icon = item.icon;
          const hasBadge = item.path === '/queue' && queueStats && queueStats.pending > 0;
          
          return (
            <NavLink
              key={item.path}
              to={item.path}
              className={({ isActive }) =>
                `flex items-center gap-3 px-3 py-2.5 rounded-lg transition-all duration-200 group relative ${
                  isActive
                    ? 'bg-brand-500/20 text-brand-400 border border-brand-500/30'
                    : 'text-slate-400 hover:bg-slate-700 hover:text-slate-200'
                }`
              }
            >
              <Icon className="w-5 h-5 flex-shrink-0" />
              
              <AnimatePresence mode="wait">
                {!collapsed && (
                  <motion.span
                    initial={{ opacity: 0, width: 0 }}
                    animate={{ opacity: 1, width: 'auto' }}
                    exit={{ opacity: 0, width: 0 }}
                    className="whitespace-nowrap overflow-hidden font-medium"
                  >
                    {item.label}
                  </motion.span>
                )}
              </AnimatePresence>
              
              {/* Badge for queue */}
              {hasBadge && !collapsed && (
                <span className="ml-auto bg-brand-500 text-white text-xs font-bold px-2 py-0.5 rounded-full">
                  {queueStats?.pending}
                </span>
              )}
              
              {/* Tooltip for collapsed state */}
              {collapsed && (
                <div className="absolute left-full ml-2 px-2 py-1 bg-slate-800 text-slate-200 text-sm rounded-lg opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap z-50 border border-slate-700">
                  {item.label}
                </div>
              )}
            </NavLink>
          );
        })}
      </nav>

      {/* Footer Status */}
      <div className="p-4 border-t border-slate-700">
        <div className="flex items-center gap-2">
          <div
            className={`w-2.5 h-2.5 rounded-full ${
              baileysConnected ? 'bg-green-500 animate-pulse' : 'bg-red-500'
            }`}
          />
          <AnimatePresence mode="wait">
            {!collapsed && (
              <motion.span
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                className="text-sm text-slate-400"
              >
                {baileysConnected ? 'Connected' : 'Disconnected'}
              </motion.span>
            )}
          </AnimatePresence>
        </div>
        
        {!collapsed && (
          <div className="mt-2 text-xs text-slate-500">
            v1.0.0
          </div>
        )}
      </div>
    </motion.aside>
  );
}

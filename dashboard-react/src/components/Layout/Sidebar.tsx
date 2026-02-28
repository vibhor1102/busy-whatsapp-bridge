import { NavLink, type NavLinkRenderProps } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import {
  LayoutDashboard,
  Bell,
  MessageSquare,
  Inbox,
  FileText,
  Settings,
  Cpu,
  ChevronLeft,
  ChevronRight,
  Smartphone,
  Circle,
} from 'lucide-react';
import { useSystemStore, selectIsBaileysConnected } from '../../stores/systemStore';
import { useQueueStore } from '../../stores/queueStore';

interface SidebarProps {
  collapsed: boolean;
  onToggle: () => void;
}

const navItems = [
  { path: '.', label: 'Overview', icon: LayoutDashboard },
  { path: 'reminders', label: 'Reminders', icon: Bell },
  { path: 'whatsapp', label: 'WhatsApp', icon: MessageSquare },
  { path: 'queue', label: 'Queue', icon: Inbox },
  { path: 'logs', label: 'Logs', icon: FileText },
  { path: 'system', label: 'System', icon: Cpu },
  { path: 'settings', label: 'Settings', icon: Settings },
];

export function Sidebar({ collapsed, onToggle }: SidebarProps) {
  const baileysConnected = useSystemStore(selectIsBaileysConnected);
  const queueStats = useQueueStore((state) => state.stats);

  return (
    <motion.aside
      initial={false}
      animate={{ width: collapsed ? 72 : 256 }}
      transition={{ duration: 0.25, ease: [0.4, 0, 0.2, 1] }}
      className="fixed left-0 top-0 h-screen flex flex-col z-50 backdrop-blur-xl border-r"
      style={{
        background: 'var(--bg-sidebar)',
        borderColor: 'var(--border-default)',
      }}
    >
      {/* Logo Section */}
      <div
        className="h-16 flex items-center justify-between px-4 border-b"
        style={{ borderColor: 'var(--border-default)' }}
      >
        <div className="flex items-center gap-3 overflow-hidden">
          <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-brand-500 to-brand-700 flex items-center justify-center flex-shrink-0 shadow-md">
            <Smartphone className="w-5 h-5 text-white" />
          </div>
          <AnimatePresence mode="wait">
            {!collapsed && (
              <motion.span
                initial={{ opacity: 0, x: -10 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: -10 }}
                className="font-semibold whitespace-nowrap"
                style={{ color: 'var(--text-primary)' }}
              >
                Busy Bridge
              </motion.span>
            )}
          </AnimatePresence>
        </div>

        <button
          onClick={onToggle}
          className="p-1.5 rounded-lg transition-colors"
          style={{ color: 'var(--text-tertiary)' }}
          onMouseEnter={(e) => (e.currentTarget.style.background = 'var(--bg-input)')}
          onMouseLeave={(e) => (e.currentTarget.style.background = 'transparent')}
        >
          {collapsed ? (
            <ChevronRight className="w-4 h-4" />
          ) : (
            <ChevronLeft className="w-4 h-4" />
          )}
        </button>
      </div>

      {/* Navigation */}
      <nav className="flex-1 py-3 px-3 space-y-0.5 overflow-y-auto">
        {navItems.map((item, index) => {
          const Icon = item.icon;
          const hasBadge = item.path === 'queue' && queueStats && queueStats.pending > 0;

          return (
            <div key={item.path}>
              {/* Separator after first item (Overview) */}
              {index === 1 && (
                <div
                  className="my-2 mx-2 border-t"
                  style={{ borderColor: 'var(--border-subtle)' }}
                />
              )}
              {/* Separator before settings section */}
              {index === 5 && (
                <div
                  className="my-2 mx-2 border-t"
                  style={{ borderColor: 'var(--border-subtle)' }}
                />
              )}
              <NavLink
                to={item.path}
                end={item.path === '.'}
                className={({ isActive }: NavLinkRenderProps) =>
                  `flex items-center gap-3 px-3 py-2 rounded-lg transition-all duration-150 group relative ${isActive
                    ? 'font-medium'
                    : ''
                  }`
                }
                style={({ isActive }: NavLinkRenderProps) => ({
                  background: isActive ? 'var(--brand-soft)' : 'transparent',
                  color: isActive ? 'var(--brand-accent)' : 'var(--text-secondary)',
                  borderLeft: isActive ? '3px solid var(--brand-accent)' : '3px solid transparent',
                })}
              >
                <Icon className="w-[18px] h-[18px] flex-shrink-0" />

                <AnimatePresence mode="wait">
                  {!collapsed && (
                    <motion.span
                      initial={{ opacity: 0, width: 0 }}
                      animate={{ opacity: 1, width: 'auto' }}
                      exit={{ opacity: 0, width: 0 }}
                      className="whitespace-nowrap overflow-hidden text-sm"
                    >
                      {item.label}
                    </motion.span>
                  )}
                </AnimatePresence>

                {/* Badge for queue */}
                {hasBadge && !collapsed && (
                  <span className="ml-auto text-xs font-semibold px-2 py-0.5 rounded-full"
                    style={{
                      background: 'var(--brand-accent)',
                      color: 'white',
                    }}
                  >
                    {queueStats?.pending}
                  </span>
                )}

                {/* Tooltip for collapsed state */}
                {collapsed && (
                  <div
                    className="absolute left-full ml-3 px-2.5 py-1.5 text-xs rounded-lg opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap z-50 shadow-lg pointer-events-none"
                    style={{
                      background: 'var(--bg-card)',
                      color: 'var(--text-primary)',
                      border: '1px solid var(--border-default)',
                    }}
                  >
                    {item.label}
                  </div>
                )}
              </NavLink>
            </div>
          );
        })}
      </nav>

      {/* Footer Status */}
      <div
        className="p-4 border-t"
        style={{ borderColor: 'var(--border-default)' }}
      >
        <div className="flex items-center gap-2">
          <Circle
            className={`w-2.5 h-2.5 flex-shrink-0 ${baileysConnected ? 'fill-emerald-500 text-emerald-500' : 'fill-red-500 text-red-500'
              }`}
            style={baileysConnected ? { filter: 'drop-shadow(0 0 3px rgb(16 185 129 / 0.5))' } : {}}
          />
          <AnimatePresence mode="wait">
            {!collapsed && (
              <motion.span
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                className="text-xs"
                style={{ color: 'var(--text-tertiary)' }}
              >
                {baileysConnected ? 'WhatsApp Online' : 'WhatsApp Offline'}
              </motion.span>
            )}
          </AnimatePresence>
        </div>
      </div>
    </motion.aside>
  );
}

export const statusColorMap: Record<string, string> = {
  // Connection states — using inline styles via getStatusStyle is preferred,
  // but these classes are kept for backward compatibility in simple contexts
  connected: 'text-emerald-500 dark:text-emerald-400',
  qr_ready: 'text-amber-500 dark:text-amber-400',
  connecting: 'text-blue-500 dark:text-blue-400',
  reconnecting: 'text-blue-500 dark:text-blue-400',
  disconnected: 'text-red-500 dark:text-red-400',
  logged_out: 'text-red-500 dark:text-red-400',
  unreachable: 'text-red-500 dark:text-red-400',
  unknown: 'text-gray-500 dark:text-gray-400',

  // Session states
  online: 'text-emerald-500',
  sending: 'text-emerald-500',
  paused: 'text-amber-500',
  stopped: 'text-red-500',
  error: 'text-red-500',
  completed: 'text-blue-500',

  // Message states
  sent: 'text-emerald-500 dark:text-emerald-400',
  failed: 'text-red-500 dark:text-red-400',
  retrying: 'text-amber-500 dark:text-amber-400',
  pending: 'text-gray-500 dark:text-gray-400',
};

/** Get a Tailwind class string for status-based coloring */
export function getStatusColor(status: string): string {
  return statusColorMap[status] || statusColorMap.unknown;
}

/** Get inline-style-friendly CSS variable based status styles */
export function getStatusStyle(status: string): { color: string; bg: string; border: string } {
  switch (status) {
    case 'connected':
    case 'online':
    case 'sending':
    case 'sent':
      return { color: 'var(--success)', bg: 'var(--success-soft)', border: 'var(--success-soft-border)' };
    case 'qr_ready':
    case 'paused':
    case 'retrying':
      return { color: 'var(--warning)', bg: 'var(--warning-soft)', border: 'var(--warning-soft-border)' };
    case 'disconnected':
    case 'logged_out':
    case 'unreachable':
    case 'stopped':
    case 'error':
    case 'failed':
      return { color: 'var(--danger)', bg: 'var(--danger-soft)', border: 'var(--danger-soft-border)' };
    case 'connecting':
    case 'reconnecting':
    case 'completed':
      return { color: 'var(--brand-accent)', bg: 'var(--brand-soft)', border: 'var(--brand-soft-border)' };
    default:
      return { color: 'var(--text-tertiary)', bg: 'var(--bg-input)', border: 'var(--border-default)' };
  }
}

/** Get a dot color for session/connection status */
export function getStatusDotColor(status: string): string {
  switch (status) {
    case 'connected':
    case 'online':
    case 'sending':
    case 'sent':
      return '#10b981'; // emerald-500
    case 'qr_ready':
    case 'paused':
    case 'retrying':
      return '#f59e0b'; // amber-500
    case 'disconnected':
    case 'logged_out':
    case 'stopped':
    case 'error':
    case 'failed':
      return '#ef4444'; // red-500
    default:
      return '#6b7280'; // gray-500
  }
}

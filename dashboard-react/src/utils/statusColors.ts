export const statusColorMap: Record<string, string> = {
  // Connection states
  connected: 'bg-green-500/20 text-green-400 border-green-500/30',
  qr_ready: 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30',
  connecting: 'bg-blue-500/20 text-blue-400 border-blue-500/30',
  reconnecting: 'bg-blue-500/20 text-blue-400 border-blue-500/30',
  disconnected: 'bg-red-500/20 text-red-400 border-red-500/30',
  logged_out: 'bg-red-500/20 text-red-400 border-red-500/30',
  unreachable: 'bg-red-500/20 text-red-400 border-red-500/30',
  unknown: 'bg-slate-500/20 text-slate-400 border-slate-500/30',
  
  // Session states
  online: 'bg-green-500',
  sending: 'bg-green-500',
  paused: 'bg-yellow-500',
  stopped: 'bg-red-500',
  error: 'bg-red-500',
  completed: 'bg-brand-500',
  
  // Message states
  sent: 'text-green-400',
  failed: 'text-red-400',
  retrying: 'text-yellow-400',
  pending: 'text-slate-400',
};

export function getStatusColor(status: string): string {
  return statusColorMap[status] || statusColorMap.unknown;
}

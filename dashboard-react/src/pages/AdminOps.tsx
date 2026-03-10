import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { AlertTriangle, CheckCircle2, Clock3, PlayCircle, RefreshCw, RotateCcw, ShieldAlert, Smartphone } from 'lucide-react';
import { toast } from 'sonner';
import { api } from '../services/api';
import type { PlannerSummaryDay } from '../types';

function StatTile({ label, value, tone = 'neutral' }: { label: string; value: string | number; tone?: 'neutral' | 'warning' | 'danger' | 'success' }) {
  const toneMap = {
    neutral: { border: 'var(--border-default)', text: 'var(--text-primary)' },
    warning: { border: 'var(--warning-soft-border)', text: 'var(--warning)' },
    danger: { border: 'rgba(239, 68, 68, 0.35)', text: 'var(--danger)' },
    success: { border: 'rgba(16, 185, 129, 0.35)', text: 'var(--success)' },
  };
  const style = toneMap[tone];

  return (
    <div className="card p-4" style={{ borderColor: style.border }}>
      <p className="text-xs uppercase tracking-[0.16em]" style={{ color: 'var(--text-tertiary)' }}>{label}</p>
      <p className="mt-2 text-2xl font-semibold" style={{ color: style.text }}>{value}</p>
    </div>
  );
}

function PlannerDayRow({ day }: { day: PlannerSummaryDay }) {
  return (
    <div className="grid grid-cols-[160px_1fr] gap-4 rounded-xl border p-3" style={{ borderColor: 'var(--border-default)' }}>
      <div>
        <div className="text-sm font-semibold" style={{ color: 'var(--text-primary)' }}>{day.day}</div>
        <div className="text-xs" style={{ color: 'var(--text-tertiary)' }}>{day.party_codes.length} parties</div>
      </div>
      <div className="grid grid-cols-3 gap-2 text-sm">
        <div><span style={{ color: 'var(--text-tertiary)' }}>Planned</span><div style={{ color: 'var(--text-primary)' }}>{day.planned_count}</div></div>
        <div><span style={{ color: 'var(--text-tertiary)' }}>Released</span><div style={{ color: 'var(--text-primary)' }}>{day.released_count}</div></div>
        <div><span style={{ color: 'var(--text-tertiary)' }}>Forfeited</span><div style={{ color: 'var(--text-primary)' }}>{day.forfeited_count}</div></div>
      </div>
    </div>
  );
}

export function AdminOps() {
  const queryClient = useQueryClient();
  const opsQuery = useQuery({
    queryKey: ['dispatch-ops-status'],
    queryFn: () => api.getDispatchOpsStatus(),
    refetchInterval: 15000,
  });

  const refreshOps = async () => {
    await queryClient.invalidateQueries({ queryKey: ['dispatch-ops-status'] });
  };

  const restartBridge = useMutation({
    mutationFn: () => api.restartBaileys(),
    onSuccess: async () => {
      toast.success('Baileys restart requested');
      await refreshOps();
    },
    onError: (error: Error) => toast.error(error.message),
  });

  const replan = useMutation({
    mutationFn: () => api.replanCurrentWeek(),
    onSuccess: async () => {
      toast.success('Weekly reminder plan rebuilt');
      await refreshOps();
    },
    onError: (error: Error) => toast.error(error.message),
  });

  const releaseDue = useMutation({
    mutationFn: () => api.releaseDueReminders(),
    onSuccess: async (result) => {
      toast.success(`Release result: ${String(result.result.status ?? 'ok')}`);
      await refreshOps();
    },
    onError: (error: Error) => toast.error(error.message),
  });

  const acknowledge = useMutation({
    mutationFn: () => api.acknowledgeDispatchIncident(),
    onSuccess: async () => {
      toast.success('Incident acknowledged');
      await refreshOps();
    },
    onError: (error: Error) => toast.error(error.message),
  });

  const ignore = useMutation({
    mutationFn: () => api.ignoreDispatchIncident(),
    onSuccess: async () => {
      toast.success('Incident muted');
      await refreshOps();
    },
    onError: (error: Error) => toast.error(error.message),
  });

  const resolve = useMutation({
    mutationFn: () => api.resolveDispatchIncident(),
    onSuccess: async () => {
      toast.success('Incident cleared');
      await refreshOps();
    },
    onError: (error: Error) => toast.error(error.message),
  });

  if (opsQuery.isLoading) {
    return <div className="p-6 text-sm" style={{ color: 'var(--text-tertiary)' }}>Loading operations console...</div>;
  }

  if (opsQuery.isError || !opsQuery.data) {
    return <div className="p-6 text-sm" style={{ color: 'var(--danger)' }}>Failed to load operations console.</div>;
  }

  const ops = opsQuery.data;
  const incident = ops.incident.incident;
  const bridgeHealthy = ops.bridge.state === 'connected' && !ops.incident.dispatch_blocked;

  return (
    <div className="space-y-6 p-6">
      <div className="flex items-start justify-between gap-4">
        <div>
          <p className="text-xs uppercase tracking-[0.2em]" style={{ color: 'var(--text-tertiary)' }}>Hidden Admin</p>
          <h1 className="mt-2 text-3xl font-semibold" style={{ color: 'var(--text-primary)' }}>Dispatch Operations</h1>
          <p className="mt-2 max-w-3xl text-sm" style={{ color: 'var(--text-secondary)' }}>
            Bridge health, weekly reminder spread, catch-up state, and manual recovery controls live here.
          </p>
        </div>
        <button className="btn-secondary" onClick={() => refreshOps()}>
          <RefreshCw className="h-4 w-4" />
          Refresh
        </button>
      </div>

      <div className="grid gap-4 md:grid-cols-4">
        <StatTile label="Bridge State" value={ops.bridge.state} tone={bridgeHealthy ? 'success' : 'danger'} />
        <StatTile label="Snapshot" value={ops.snapshot.same_day_ready ? 'Ready' : 'Missing'} tone={ops.snapshot.same_day_ready ? 'success' : 'warning'} />
        <StatTile label="Due Today" value={ops.planner.due_today.length} tone={ops.planner.due_today.length > 0 ? 'warning' : 'neutral'} />
        <StatTile label="Dispatch Mode" value={ops.dispatch_mode.replace('_', ' ')} tone={ops.dispatch_mode === 'paused' ? 'warning' : 'neutral'} />
      </div>

      <div className="grid gap-6 xl:grid-cols-[1.1fr_0.9fr]">
        <section className="card p-5">
          <div className="flex items-center gap-2">
            <Smartphone className="h-4 w-4" />
            <h2 className="text-lg font-semibold" style={{ color: 'var(--text-primary)' }}>Bridge and Incident</h2>
          </div>

          <div className="mt-4 grid gap-3 md:grid-cols-2">
            <div className="rounded-xl border p-4" style={{ borderColor: 'var(--border-default)' }}>
              <div className="text-xs uppercase tracking-[0.16em]" style={{ color: 'var(--text-tertiary)' }}>Session</div>
              <div className="mt-2 text-sm" style={{ color: 'var(--text-primary)' }}>
                State: {ops.bridge.state}
              </div>
              <div className="text-sm" style={{ color: 'var(--text-primary)' }}>
                Session state: {ops.bridge.sessionState ?? ops.bridge.sessionState ?? 'unknown'}
              </div>
              <div className="text-sm" style={{ color: 'var(--text-primary)' }}>
                Reconnect attempts: {ops.bridge.reconnectAttempts ?? 0}
              </div>
              <div className="text-sm" style={{ color: 'var(--text-primary)' }}>
                Last disconnect: {ops.bridge.lastDisconnectReason ?? 'n/a'}
              </div>
            </div>

            <div className="rounded-xl border p-4" style={{ borderColor: incident ? 'rgba(239, 68, 68, 0.35)' : 'var(--border-default)' }}>
              <div className="flex items-center gap-2">
                {incident ? <ShieldAlert className="h-4 w-4" /> : <CheckCircle2 className="h-4 w-4" />}
                <span className="text-xs uppercase tracking-[0.16em]" style={{ color: 'var(--text-tertiary)' }}>Incident</span>
              </div>
              {incident ? (
                <div className="mt-2 space-y-1 text-sm">
                  <div style={{ color: 'var(--text-primary)' }}>{incident.title}</div>
                  <div style={{ color: 'var(--text-secondary)' }}>{incident.message}</div>
                  <div style={{ color: 'var(--text-tertiary)' }}>Severity: {incident.severity}</div>
                  <div style={{ color: 'var(--text-tertiary)' }}>Manual recovery: {incident.requires_manual_resolution ? 'required' : 'not required'}</div>
                </div>
              ) : (
                <div className="mt-2 text-sm" style={{ color: 'var(--text-secondary)' }}>No active incident.</div>
              )}
            </div>
          </div>

          <div className="mt-4 flex flex-wrap gap-2">
            <button className="btn-secondary" onClick={() => restartBridge.mutate()} disabled={restartBridge.isPending}>
              <RotateCcw className="h-4 w-4" />
              Restart Bridge
            </button>
            <button className="btn-secondary" onClick={() => acknowledge.mutate()} disabled={!incident || acknowledge.isPending}>
              <AlertTriangle className="h-4 w-4" />
              Acknowledge
            </button>
            <button className="btn-secondary" onClick={() => ignore.mutate()} disabled={!incident || ignore.isPending}>
              <Clock3 className="h-4 w-4" />
              Ignore Alerts
            </button>
            <button className="btn-secondary" onClick={() => resolve.mutate()} disabled={!incident || resolve.isPending}>
              <CheckCircle2 className="h-4 w-4" />
              Resolve
            </button>
          </div>
        </section>

        <section className="card p-5">
          <div className="flex items-center gap-2">
            <PlayCircle className="h-4 w-4" />
            <h2 className="text-lg font-semibold" style={{ color: 'var(--text-primary)' }}>Release Controls</h2>
          </div>
          <div className="mt-4 space-y-3 text-sm" style={{ color: 'var(--text-secondary)' }}>
            <div>Same-day snapshot: <strong style={{ color: 'var(--text-primary)' }}>{ops.snapshot.same_day_ready ? 'ready' : 'missing'}</strong></div>
            <div>Reminder dispatch allowed: <strong style={{ color: 'var(--text-primary)' }}>{ops.policy.can_dispatch_reminders ? 'yes' : 'no'}</strong></div>
            <div>Blocked reason: <strong style={{ color: 'var(--text-primary)' }}>{ops.policy.blocked_reason || 'none'}</strong></div>
            <div>Due today: <strong style={{ color: 'var(--text-primary)' }}>{ops.planner.due_today.join(', ') || 'none'}</strong></div>
          </div>
          <div className="mt-4 flex flex-wrap gap-2">
            <button className="btn-secondary" onClick={() => replan.mutate()} disabled={replan.isPending}>
              <RefreshCw className="h-4 w-4" />
              Rebuild Week Plan
            </button>
            <button className="btn-primary" onClick={() => releaseDue.mutate()} disabled={releaseDue.isPending}>
              <PlayCircle className="h-4 w-4" />
              Release Due Reminders
            </button>
          </div>
        </section>
      </div>

      <section className="card p-5">
        <div className="flex items-center gap-2">
          <RefreshCw className="h-4 w-4" />
          <h2 className="text-lg font-semibold" style={{ color: 'var(--text-primary)' }}>Weekly Spread</h2>
        </div>
        <div className="mt-2 text-sm" style={{ color: 'var(--text-secondary)' }}>
          Week anchor: {ops.planner.summary.week_key}
        </div>
        <div className="mt-4 grid gap-4 md:grid-cols-3">
          <StatTile label="Planned" value={ops.planner.summary.totals.planned} />
          <StatTile label="Released" value={ops.planner.summary.totals.released} tone="success" />
          <StatTile label="Forfeited" value={ops.planner.summary.totals.forfeited} tone={ops.planner.summary.totals.forfeited > 0 ? 'warning' : 'neutral'} />
        </div>
        <div className="mt-4 space-y-3">
          {ops.planner.summary.days.length === 0 ? (
            <div className="rounded-xl border p-4 text-sm" style={{ borderColor: 'var(--border-default)', color: 'var(--text-secondary)' }}>
              No weekly plan yet. Refresh same-day reminder data, then rebuild the week plan.
            </div>
          ) : (
            ops.planner.summary.days.map((day) => <PlannerDayRow key={day.day} day={day} />)
          )}
        </div>
      </section>
    </div>
  );
}

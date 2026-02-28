import { useEffect, useState, useCallback } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { motion } from 'framer-motion';
import {
  RefreshCw,
  LogOut,
  QrCode,
  CheckCircle,
  XCircle,
  Smartphone,
  AlertTriangle,
  Loader2,
} from 'lucide-react';
import { api } from '../services/api';
import { useSystemStore } from '../stores/systemStore';
import { LoadingState } from '../components/ui/LoadingState';
import { getStatusStyle } from '../utils/statusColors';
import { REFETCH_INTERVALS } from '../constants';
import { toast } from 'sonner';

export function WhatsAppManager() {
  const queryClient = useQueryClient();
  const setBaileysStatus = useSystemStore((state) => state.setBaileysStatus);
  const [isRefreshing, setIsRefreshing] = useState(false);

  const { data: status, isLoading } = useQuery({
    queryKey: ['baileys-status'],
    queryFn: api.getBaileysStatus,
    refetchInterval: REFETCH_INTERVALS.BAILEYS_STATUS,
  });

  useEffect(() => {
    if (status) {
      setBaileysStatus(status);
    }
  }, [status, setBaileysStatus]);

  const restartMutation = useMutation({
    mutationFn: api.restartBaileys,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['baileys-status'] });
      toast.success('Baileys service restarted successfully');
    },
    onError: (error: Error) => {
      toast.error(`Failed to restart Baileys: ${error.message}`);
    },
  });

  const disconnectMutation = useMutation({
    mutationFn: api.disconnectWhatsApp,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['baileys-status'] });
      toast.success('WhatsApp disconnected successfully');
    },
    onError: (error: Error) => {
      toast.error(`Failed to disconnect WhatsApp: ${error.message}`);
    },
  });

  const clearSessionMutation = useMutation({
    mutationFn: api.clearWhatsAppSession,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['baileys-status'] });
      toast.success('Session cleared successfully');
    },
    onError: (error: Error) => {
      toast.error(`Failed to clear session: ${error.message}`);
    },
  });

  const handleRefresh = useCallback(async () => {
    setIsRefreshing(true);
    await queryClient.invalidateQueries({ queryKey: ['baileys-status'] });
    setIsRefreshing(false);
  }, [queryClient]);

  const getStatusIcon = (state: string) => {
    switch (state) {
      case 'connected':
        return <CheckCircle className="w-5 h-5" />;
      case 'qr_ready':
        return <QrCode className="w-5 h-5" />;
      case 'connecting':
      case 'reconnecting':
        return <Loader2 className="w-5 h-5 animate-spin" />;
      default:
        return <XCircle className="w-5 h-5" />;
    }
  };

  if (isLoading) {
    return <LoadingState size="lg" fullPage />;
  }

  const isConnected = status?.state === 'connected';
  const isQrReady = status?.state === 'qr_ready';
  const statusStyle = getStatusStyle(status?.state || 'unknown');

  return (
    <div className="space-y-5">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold" style={{ color: 'var(--text-primary)' }}>
            WhatsApp
          </h2>
          <p className="text-sm mt-0.5" style={{ color: 'var(--text-tertiary)' }}>
            Manage connection and session
          </p>
        </div>
        <button onClick={handleRefresh} disabled={isRefreshing} className="btn-secondary">
          <RefreshCw className={`w-4 h-4 ${isRefreshing && 'animate-spin'}`} />
          Refresh
        </button>
      </div>

      {/* Status Card */}
      <motion.div
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        className="card p-5"
      >
        <div className="flex items-center justify-between mb-5">
          <div className="flex items-center gap-4">
            <div
              className="p-3 rounded-xl"
              style={{ background: statusStyle.bg, color: statusStyle.color, border: `1px solid ${statusStyle.border}` }}
            >
              {getStatusIcon(status?.state || 'unknown')}
            </div>

            <div>
              <p className="text-xs" style={{ color: 'var(--text-tertiary)' }}>Connection Status</p>
              <p className="text-xl font-bold capitalize" style={{ color: 'var(--text-primary)' }}>
                {(status?.state || 'unknown').replace('_', ' ')}
              </p>
            </div>
          </div>

          <div className="flex gap-2">
            <button
              onClick={() => restartMutation.mutate()}
              disabled={restartMutation.isPending}
              className="btn-primary"
            >
              {restartMutation.isPending ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <RefreshCw className="w-4 h-4" />
              )}
              Restart
            </button>

            {isConnected && (
              <button
                onClick={() => disconnectMutation.mutate()}
                disabled={disconnectMutation.isPending}
                className="btn-danger"
              >
                {disconnectMutation.isPending ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : (
                  <LogOut className="w-4 h-4" />
                )}
                Disconnect
              </button>
            )}
          </div>
        </div>

        {status?.error && (
          <div
            className="p-3 rounded-lg flex items-start gap-2.5"
            style={{
              background: 'var(--danger-soft)',
              border: '1px solid var(--danger-soft-border)',
            }}
          >
            <AlertTriangle className="w-4 h-4 flex-shrink-0 mt-0.5" style={{ color: 'var(--danger)' }} />
            <p className="text-sm" style={{ color: 'var(--danger)' }}>{status.error}</p>
          </div>
        )}

        {isConnected && status?.user && (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3 mt-5">
            <div className="p-3 rounded-lg" style={{ background: 'var(--bg-input)' }}>
              <p className="text-xs" style={{ color: 'var(--text-tertiary)' }}>Connected Account</p>
              <p className="text-sm font-medium mt-0.5" style={{ color: 'var(--text-primary)' }}>
                {status.user.name}
              </p>
            </div>
            <div className="p-3 rounded-lg" style={{ background: 'var(--bg-input)' }}>
              <p className="text-xs" style={{ color: 'var(--text-tertiary)' }}>Phone Number</p>
              <p className="text-sm font-medium mt-0.5" style={{ color: 'var(--text-primary)' }}>
                {status.user.phone}
              </p>
            </div>
          </div>
        )}
      </motion.div>

      {/* QR Code Section */}
      {isQrReady && status?.qr_image && (
        <motion.div
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          className="card p-8"
        >
          <div className="text-center">
            <div
              className="inline-flex items-center justify-center w-14 h-14 rounded-full mb-4"
              style={{ background: 'var(--warning-soft)' }}
            >
              <QrCode className="w-7 h-7" style={{ color: 'var(--warning)' }} />
            </div>

            <h3 className="text-lg font-semibold mb-1.5" style={{ color: 'var(--text-primary)' }}>
              Scan QR Code
            </h3>
            <p className="text-sm mb-6 max-w-md mx-auto" style={{ color: 'var(--text-tertiary)' }}>
              Open WhatsApp on your phone, go to Settings &gt; Linked Devices, and scan this QR code to connect
            </p>

            <div className="inline-block p-5 bg-white rounded-xl shadow-lg">
              <img
                src={`data:image/png;base64,${status?.qr_image}`}
                alt="WhatsApp QR Code"
                className="w-56 h-56"
              />
            </div>
          </div>
        </motion.div>
      )}

      {/* Session Management */}
      <motion.div
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.15 }}
        className="card p-5"
      >
        <h3 className="text-sm font-semibold mb-4" style={{ color: 'var(--text-primary)' }}>
          Session Management
        </h3>

        <div
          className="flex items-center justify-between p-3.5 rounded-lg"
          style={{ background: 'var(--bg-input)' }}
        >
          <div className="flex items-center gap-3">
            <Smartphone className="w-4 h-4" style={{ color: 'var(--text-tertiary)' }} />
            <div>
              <p className="text-sm font-medium" style={{ color: 'var(--text-primary)' }}>
                Clear Session Data
              </p>
              <p className="text-xs" style={{ color: 'var(--text-tertiary)' }}>
                Remove saved credentials and require re-authentication
              </p>
            </div>
          </div>

          <button
            onClick={() => clearSessionMutation.mutate()}
            disabled={clearSessionMutation.isPending}
            className="btn-danger text-xs"
          >
            {clearSessionMutation.isPending ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              'Clear Session'
            )}
          </button>
        </div>
      </motion.div>
    </div>
  );
}

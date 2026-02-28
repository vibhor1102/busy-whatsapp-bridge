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
  Loader2
} from 'lucide-react';
import { api } from '../services/api';
import { useSystemStore } from '../stores/systemStore';
import { LoadingState } from '../components/ui/LoadingState';
import { getStatusColor } from '../utils/statusColors';
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

  // Using getStatusColor from utils/statusColors.ts

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

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-slate-100">WhatsApp Manager</h2>
          <p className="text-slate-400 mt-1">Manage WhatsApp Web connection and session</p>
        </div>
        <button
          onClick={handleRefresh}
          disabled={isRefreshing}
          className="flex items-center gap-2 px-4 py-2 bg-slate-700 hover:bg-slate-600 text-slate-200 rounded-lg transition-colors disabled:opacity-50"
        >
          <RefreshCw className={`w-4 h-4 ${isRefreshing && 'animate-spin'}`} />
          Refresh
        </button>
      </div>

      {/* Status Card */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="bg-dark-800 border border-slate-700 rounded-xl p-6"
      >
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-4">
            <div className={`p-4 rounded-xl ${getStatusColor(status?.state || 'unknown')}`}>
              {getStatusIcon(status?.state || 'unknown')}
            </div>
            
            <div>
              <p className="text-sm text-slate-400">Connection Status</p>
              <p className="text-2xl font-bold text-slate-100 capitalize">
                {(status?.state || 'unknown').replace('_', ' ')}
              </p>
            </div>
          </div>

          <div className="flex gap-3">
            <button
              onClick={() => restartMutation.mutate()}
              disabled={restartMutation.isPending}
              className="flex items-center gap-2 px-4 py-2 bg-brand-500 hover:bg-brand-600 text-white rounded-lg transition-colors disabled:opacity-50"
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
                className="flex items-center gap-2 px-4 py-2 bg-red-500/20 hover:bg-red-500/30 text-red-400 border border-red-500/30 rounded-lg transition-colors disabled:opacity-50"
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
          <div className="p-4 rounded-lg bg-red-500/10 border border-red-500/30">
            <div className="flex items-start gap-3">
              <AlertTriangle className="w-5 h-5 text-red-400 flex-shrink-0 mt-0.5" />
              <p className="text-red-400">{status.error}</p>
            </div>
          </div>
        )}

        {isConnected && status?.user && (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-6">
            <div className="p-4 rounded-lg bg-slate-700/30">
              <p className="text-sm text-slate-400">Connected Account</p>
              <p className="text-lg font-medium text-slate-100 mt-1">{status.user.name}</p>
            </div>
            
            <div className="p-4 rounded-lg bg-slate-700/30">
              <p className="text-sm text-slate-400">Phone Number</p>
              <p className="text-lg font-medium text-slate-100 mt-1">{status.user.phone}</p>
            </div>
          </div>
        )}
      </motion.div>

      {/* QR Code Section */}
      {isQrReady && status?.qr_image && (
        <motion.div
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          className="bg-dark-800 border border-slate-700 rounded-xl p-8"
        >
          <div className="text-center">
            <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-yellow-500/20 mb-4">
              <QrCode className="w-8 h-8 text-yellow-400" />
            </div>
            
            <h3 className="text-xl font-semibold text-slate-100 mb-2">Scan QR Code</h3>
            <p className="text-slate-400 mb-6 max-w-md mx-auto">
              Open WhatsApp on your phone, go to Settings &gt; Linked Devices, and scan this QR code to connect
            </p>
            
            <div className="inline-block p-6 bg-white rounded-xl">
              <img
                src={`data:image/png;base64,${status?.qr_image}`}
                alt="WhatsApp QR Code"
                className="w-64 h-64"
              />
            </div>
          </div>
        </motion.div>
      )}

      {/* Session Management */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.2 }}
        className="bg-dark-800 border border-slate-700 rounded-xl p-6"
      >
        <h3 className="text-lg font-semibold text-slate-100 mb-4">Session Management</h3>
        
        <div className="space-y-4">
          <div className="flex items-center justify-between p-4 rounded-lg bg-slate-700/30">
            <div className="flex items-center gap-3">
              <Smartphone className="w-5 h-5 text-slate-400" />
              <div>
                <p className="font-medium text-slate-200">Clear Session Data</p>
                <p className="text-sm text-slate-400">Remove saved credentials and require re-authentication</p>
              </div>
            </div>
            
            <button
              onClick={() => clearSessionMutation.mutate()}
              disabled={clearSessionMutation.isPending}
              className="px-4 py-2 bg-red-500/20 hover:bg-red-500/30 text-red-400 border border-red-500/30 rounded-lg transition-colors disabled:opacity-50"
            >
              {clearSessionMutation.isPending ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                'Clear Session'
              )}
            </button>
          </div>
        </div>
      </motion.div>
    </div>
  );
}

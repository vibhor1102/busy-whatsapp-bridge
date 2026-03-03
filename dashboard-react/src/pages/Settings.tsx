import { useEffect, useState, useCallback, useRef } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { motion } from 'framer-motion';
import {
  Save,
  Loader2,
  Smartphone,
  FileText,
} from 'lucide-react';
import { api } from '../services/api';
import { LoadingState } from '../components/ui/LoadingState';
import { toast } from 'sonner';
import { DatabaseSettingsManager } from '../components/settings/DatabaseSettingsManager';
import type { Settings as SettingsConfig } from '../types';

const DEFAULT_BAILEYS_URL = import.meta.env.VITE_BAILEYS_SERVER_URL || 'http://localhost:3001';
const DEFAULT_PROVIDER = 'baileys';
const DEFAULT_LOG_LEVEL = 'INFO';

function Toggle({ checked, onChange, label }: {
  checked: boolean;
  onChange: (val: boolean) => void;
  label: string;
}) {
  return (
    <label className="flex items-center gap-3 cursor-pointer">
      <button
        onClick={() => onChange(!checked)}
        className={`toggle ${checked ? 'active' : ''}`}
        role="switch"
        aria-checked={checked}
        aria-label={label}
        type="button"
      />
      <span className="text-sm" style={{ color: 'var(--text-secondary)' }}>{label}</span>
    </label>
  );
}

export function Settings() {
  const queryClient = useQueryClient();
  const [formData, setFormData] = useState({
    whatsapp_provider: DEFAULT_PROVIDER,
    baileys_server_url: DEFAULT_BAILEYS_URL,
    baileys_enabled: true,
    log_level: DEFAULT_LOG_LEVEL,
    bds_file_path: '',
    companies: {} as Record<string, { bds_file_path: string; bds_password?: string }>,
  });

  const { data: settings, isLoading } = useQuery({
    queryKey: ['settings'],
    queryFn: () => api.getSettingsConfig(),
  });

  const hasInitializedRef = useRef(false);

  useEffect(() => {
    if (settings?.content && !hasInitializedRef.current) {
      hasInitializedRef.current = true;
      const content = settings.content as {
        whatsapp_provider?: string;
        baileys_server_url?: string;
        baileys_enabled?: boolean;
        log_level?: string;
        database?: {
          bds_file_path?: string;
          companies?: Record<string, { bds_file_path: string; bds_password?: string }>;
        };
      };

      const dbBaseDir = content.database?.bds_file_path || '';
      const initialCompanies = content.database?.companies || {};

      setFormData({
        whatsapp_provider: content.whatsapp_provider || DEFAULT_PROVIDER,
        baileys_server_url: content.baileys_server_url || DEFAULT_BAILEYS_URL,
        baileys_enabled: content.baileys_enabled ?? true,
        log_level: content.log_level || DEFAULT_LOG_LEVEL,
        bds_file_path: dbBaseDir,
        companies: initialCompanies
      });
    }
  }, [settings]);

  const updateMutation = useMutation({
    mutationFn: (settings: Partial<SettingsConfig>) => api.updateSettingsConfig(settings),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['settings'] });
      toast.success('Settings saved successfully');
    },
    onError: (error: Error) => {
      toast.error(`Failed to save settings: ${error.message}`);
    },
  });

  const handleSubmit = useCallback(async (e: React.FormEvent) => {
    e.preventDefault();
    await updateMutation.mutateAsync(formData);
  }, [updateMutation, formData]);

  if (isLoading) {
    return <LoadingState size="lg" fullPage />;
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h2 className="text-2xl font-bold" style={{ color: 'var(--text-primary)' }}>Settings</h2>
        <p className="text-sm mt-1" style={{ color: 'var(--text-tertiary)' }}>
          Configure application settings
        </p>
      </div>

      {/* Settings Form */}
      <motion.form
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        onSubmit={handleSubmit}
        className="card p-6"
      >
        <div className="space-y-8">
          {/* WhatsApp Settings */}
          <div
            className="pb-6 border-b"
            style={{ borderColor: 'var(--border-default)' }}
          >
            <div className="flex items-center gap-2.5 mb-4">
              <div
                className="p-2 rounded-lg"
                style={{ background: 'var(--brand-soft)', border: '1px solid var(--brand-soft-border)' }}
              >
                <Smartphone className="w-4 h-4" style={{ color: 'var(--brand-accent)' }} />
              </div>
              <h3 className="text-sm font-semibold" style={{ color: 'var(--text-primary)' }}>
                WhatsApp Settings
              </h3>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-medium mb-1.5" style={{ color: 'var(--text-secondary)' }}>
                  Provider
                </label>
                <select
                  value={formData.whatsapp_provider}
                  onChange={(e) => setFormData({ ...formData, whatsapp_provider: e.target.value })}
                  className="input"
                >
                  <option value="baileys">Baileys</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-medium mb-1.5" style={{ color: 'var(--text-secondary)' }}>
                  Baileys Server URL
                </label>
                <input
                  type="text"
                  value={formData.baileys_server_url}
                  onChange={(e) => setFormData({ ...formData, baileys_server_url: e.target.value })}
                  className="input"
                />
              </div>
            </div>

            <div className="mt-4">
              <Toggle
                checked={formData.baileys_enabled}
                onChange={(val) => setFormData({ ...formData, baileys_enabled: val })}
                label="Enable Baileys Integration"
              />
            </div>
          </div>

          {/* Database Settings Managed Separately via Multi-Company Dynamic Component */}
          <DatabaseSettingsManager
            companies={formData.companies}
            onChange={(newCompanies) => setFormData({ ...formData, companies: newCompanies })}
          />

          {/* Logging Settings */}
          <div>
            <div className="flex items-center gap-2.5 mb-4">
              <div
                className="p-2 rounded-lg"
                style={{ background: 'var(--warning-soft)', border: '1px solid var(--warning-soft-border)' }}
              >
                <FileText className="w-4 h-4" style={{ color: 'var(--warning)' }} />
              </div>
              <h3 className="text-sm font-semibold" style={{ color: 'var(--text-primary)' }}>
                Logging Settings
              </h3>
            </div>

            <div>
              <label className="block text-xs font-medium mb-1.5" style={{ color: 'var(--text-secondary)' }}>
                Log Level
              </label>
              <select
                value={formData.log_level}
                onChange={(e) => setFormData({ ...formData, log_level: e.target.value })}
                className="input max-w-xs"
              >
                <option value="DEBUG">Debug</option>
                <option value="INFO">Info</option>
                <option value="WARNING">Warning</option>
                <option value="ERROR">Error</option>
              </select>
            </div>
          </div>
        </div>

        {/* Submit Button */}
        <div className="mt-8 flex justify-end">
          <button
            type="submit"
            disabled={updateMutation.isPending}
            className="btn-primary"
          >
            {updateMutation.isPending ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                Saving...
              </>
            ) : (
              <>
                <Save className="w-4 h-4" />
                Save Settings
              </>
            )}
          </button>
        </div>
      </motion.form>
    </div>
  );
}

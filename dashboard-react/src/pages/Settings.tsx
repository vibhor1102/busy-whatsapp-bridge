import { useEffect, useState, useCallback, useRef } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Save,
  Loader2,
  Smartphone,
  FileText,
  Database,
  Monitor,
} from 'lucide-react';
import { api } from '../services/api';
import { LoadingState } from '../components/ui/LoadingState';
import { toast } from 'sonner';
import { DatabaseSettingsManager } from '../components/settings/DatabaseSettingsManager';
import type { Settings as SettingsConfig } from '../types';

const DEFAULT_BAILEYS_URL = import.meta.env.VITE_BAILEYS_SERVER_URL || 'http://localhost:3001';
const DEFAULT_PROVIDER = 'baileys';
const DEFAULT_LOG_LEVEL = 'INFO';

function Toggle({ checked, onChange, label, description }: {
  checked: boolean;
  onChange: (val: boolean) => void;
  label: string;
  description?: string;
}) {
  return (
    <label className="flex items-start gap-3 cursor-pointer">
      <button
        onClick={() => onChange(!checked)}
        className={`toggle mt-0.5 ${checked ? 'active' : ''}`}
        role="switch"
        aria-checked={checked}
        aria-label={label}
        type="button"
      />
      <div>
        <span className="text-sm font-medium" style={{ color: 'var(--text-primary)' }}>{label}</span>
        {description && <p className="text-xs mt-0.5" style={{ color: 'var(--text-tertiary)' }}>{description}</p>}
      </div>
    </label>
  );
}

type TabId = 'database' | 'whatsapp' | 'system';

export function Settings() {
  const queryClient = useQueryClient();
  const [activeTab, setActiveTab] = useState<TabId>('database');
  const [formData, setFormData] = useState({
    whatsapp_provider: DEFAULT_PROVIDER,
    baileys_server_url: DEFAULT_BAILEYS_URL,
    baileys_enabled: true,
    log_level: DEFAULT_LOG_LEVEL,
    bds_file_path: '',
    companies: {} as Record<string, { bds_file_path: string; bds_password?: string }>,
  });

  const { data: settings, isLoading: isSettingsLoading } = useQuery({
    queryKey: ['settings'],
    queryFn: () => api.getSettingsConfig(),
  });

  const { data: reminderConfig, isLoading: isReminderConfigLoading } = useQuery({
    queryKey: ['reminderConfig'],
    queryFn: () => api.getReminderConfig(),
  });

  const hasInitializedRef = useRef(false);

  useEffect(() => {
    if (settings?.content && reminderConfig && !hasInitializedRef.current) {
      hasInitializedRef.current = true;
      const content = settings.content as any;

      const dbBaseDir = content.database?.bds_file_path || '';
      const initialCompanies = content.database?.companies || {};

      setFormData({
        whatsapp_provider: content.whatsapp?.provider || content.whatsapp_provider || DEFAULT_PROVIDER,
        baileys_server_url: content.baileys?.server_url || content.baileys_server_url || DEFAULT_BAILEYS_URL,
        baileys_enabled: content.baileys?.enabled ?? content.baileys_enabled ?? true,
        log_level: content.logging?.level || content.log_level || DEFAULT_LOG_LEVEL,
        bds_file_path: dbBaseDir,
        companies: initialCompanies,
      });
    }
  }, [settings, reminderConfig]);

  const updateSettingsMutation = useMutation({
    mutationFn: (newSettings: Partial<SettingsConfig>) => api.updateSettingsConfig(newSettings),
  });

  const isSaving = updateSettingsMutation.isPending;

  const handleSubmit = useCallback(async (e: React.FormEvent) => {
    e.preventDefault();

    try {
      // 1. Update Core Settings
      await updateSettingsMutation.mutateAsync({
        whatsapp_provider: formData.whatsapp_provider,
        baileys_server_url: formData.baileys_server_url,
        baileys_enabled: formData.baileys_enabled,
        log_level: formData.log_level,
        bds_file_path: formData.bds_file_path,
        companies: formData.companies as any,
      });

      queryClient.invalidateQueries({ queryKey: ['settings'] });
      toast.success('Settings saved successfully');
    } catch (error: any) {
      toast.error(`Failed to save settings: ${error.message}`);
    }
  }, [updateSettingsMutation, formData, queryClient]);

  if (isSettingsLoading || isReminderConfigLoading) {
    return <LoadingState size="lg" fullPage />;
  }

  const tabs: { id: TabId; label: string; icon: React.ElementType }[] = [
    { id: 'database', label: 'Databases', icon: Database },
    { id: 'whatsapp', label: 'WhatsApp', icon: Smartphone },
    { id: 'system', label: 'System', icon: Monitor },
  ];

  return (
    <div className="space-y-6 max-w-5xl mx-auto pb-12">
      {/* Header */}
      <div>
        <h2 className="text-2xl font-bold" style={{ color: 'var(--text-primary)' }}>Settings</h2>
        <p className="text-sm mt-1" style={{ color: 'var(--text-tertiary)' }}>
          Manage application configurations and preferences
        </p>
      </div>

      <div className="flex flex-col lg:flex-row gap-6">
        {/* Sidebar Nav */}
        <div className="lg:w-64 flex-shrink-0 space-y-1">
          {tabs.map((tab) => {
            const Icon = tab.icon;
            const isActive = activeTab === tab.id;
            return (
              <button
                key={tab.id}
                onClick={(e) => {
                  e.preventDefault();
                  setActiveTab(tab.id);
                }}
                className={`w-full flex items-center gap-3 px-4 py-3 rounded-xl text-sm font-medium transition-all ${isActive
                  ? 'bg-blue-50 text-blue-600 dark:bg-blue-900/20 dark:text-blue-400'
                  : 'hover:bg-gray-100 dark:hover:bg-gray-800'
                  }`}
                style={{
                  color: isActive ? 'var(--brand-accent)' : 'var(--text-secondary)',
                  backgroundColor: isActive ? 'var(--brand-soft)' : 'transparent',
                }}
              >
                <Icon className={`w-4 h-4 ${isActive ? '' : 'opacity-70'}`} />
                {tab.label}
              </button>
            );
          })}
        </div>

        {/* Settings Content */}
        <motion.div
          className="flex-1 card p-0 overflow-hidden"
          layout
        >
          <form onSubmit={handleSubmit} className="flex flex-col h-full">
            <div className="p-6 md:p-8 flex-1">
              <AnimatePresence mode="wait">
                <motion.div
                  key={activeTab}
                  initial={{ opacity: 0, x: 10 }}
                  animate={{ opacity: 1, x: 0 }}
                  exit={{ opacity: 0, x: -10 }}
                  transition={{ duration: 0.2 }}
                  className="space-y-8"
                >

                  {/* TAB: DATABASE */}
                  {activeTab === 'database' && (
                    <div className="space-y-6">
                      <DatabaseSettingsManager
                        companies={formData.companies}
                        onChange={(newCompanies) => setFormData({ ...formData, companies: newCompanies })}
                      />
                    </div>
                  )}

                  {/* TAB: WHATSAPP */}
                  {activeTab === 'whatsapp' && (
                    <div className="space-y-6">
                      <div className="pb-4 border-b border-gray-100 dark:border-gray-800">
                        <h3 className="text-lg font-semibold" style={{ color: 'var(--text-primary)' }}>WhatsApp Integration</h3>
                        <p className="text-sm text-gray-500 mt-1">Configure Baileys connection to WhatsApp Web</p>
                      </div>

                      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                        <div className="space-y-1.5">
                          <label className="text-sm font-medium" style={{ color: 'var(--text-secondary)' }}>Provider</label>
                          <select
                            value={formData.whatsapp_provider}
                            onChange={(e) => setFormData({ ...formData, whatsapp_provider: e.target.value })}
                            className="input w-full"
                          >
                            <option value="baileys">Baileys (Web API)</option>
                          </select>
                        </div>

                        <div className="space-y-1.5">
                          <label className="text-sm font-medium" style={{ color: 'var(--text-secondary)' }}>Baileys Server URL</label>
                          <input
                            type="text"
                            value={formData.baileys_server_url}
                            onChange={(e) => setFormData({ ...formData, baileys_server_url: e.target.value })}
                            className="input w-full font-mono"
                          />
                        </div>
                      </div>

                      <div className="pt-2">
                        <Toggle
                          checked={formData.baileys_enabled}
                          onChange={(val) => setFormData({ ...formData, baileys_enabled: val })}
                          label="Enable WhatsApp Bridge"
                          description="Turn on/off the application's ability to communicate with WhatsApp"
                        />
                      </div>
                    </div>
                  )}

                  {/* TAB: SYSTEM */}
                  {activeTab === 'system' && (
                    <div className="space-y-6">
                      <div className="pb-4 border-b border-gray-100 dark:border-gray-800">
                        <h3 className="text-lg font-semibold" style={{ color: 'var(--text-primary)' }}>System Configuration</h3>
                        <p className="text-sm text-gray-500 mt-1">Application diagnostics and logging</p>
                      </div>

                      <div className="space-y-5">
                        <div className="max-w-md space-y-1.5">
                          <label className="flex items-center gap-2 text-sm font-medium" style={{ color: 'var(--text-secondary)' }}>
                            <FileText className="w-4 h-4" />
                            Log Level
                          </label>
                          <select
                            value={formData.log_level}
                            onChange={(e) => setFormData({ ...formData, log_level: e.target.value })}
                            className="input w-full"
                          >
                            <option value="DEBUG">DEBUG - Detailed troubleshooting</option>
                            <option value="INFO">INFO - Standard operations (Recommended)</option>
                            <option value="WARNING">WARNING - Only irregular anomalies</option>
                            <option value="ERROR">ERROR - Critical failures only</option>
                          </select>
                          <p className="text-xs text-gray-500 mt-1">Changes log verbosity in %APPDATA%\BusyWhatsappBridge\logs</p>
                        </div>
                      </div>
                    </div>
                  )}

                </motion.div>
              </AnimatePresence>
            </div>

            {/* Footer with Save Button */}
            <div className="p-6 bg-gray-50/50 dark:bg-gray-900/20 border-t border-gray-100 dark:border-gray-800 flex justify-end">
              <button
                type="submit"
                disabled={isSaving}
                className="btn-primary shadow-sm px-6"
              >
                {isSaving ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin mr-2" />
                    Saving Changes...
                  </>
                ) : (
                  <>
                    <Save className="w-4 h-4 mr-2" />
                    Save All Settings
                  </>
                )}
              </button>
            </div>
          </form>
        </motion.div>
      </div>
    </div>
  );
}

import { useEffect, useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { motion } from 'framer-motion';
import { 
  Save, 
  Loader2,
  Smartphone,
  Database,
  FileText
} from 'lucide-react';
import { api } from '../services/api';

export function Settings() {
  const queryClient = useQueryClient();
  const [formData, setFormData] = useState({
    whatsapp_provider: 'baileys',
    baileys_server_url: 'http://localhost:3001',
    baileys_enabled: true,
    log_level: 'INFO',
    bds_file_path: '',
  });

  const { data: settings, isLoading } = useQuery({
    queryKey: ['settings'],
    queryFn: api.getSettingsConfig,
  });

  useEffect(() => {
    if (settings?.content) {
      setFormData({
        whatsapp_provider: settings.content.whatsapp_provider || 'baileys',
        baileys_server_url: settings.content.baileys_server_url || 'http://localhost:3001',
        baileys_enabled: settings.content.baileys_enabled ?? true,
        log_level: settings.content.log_level || 'INFO',
        bds_file_path: settings.content.bds_file_path || '',
      });
    }
  }, [settings]);

  const updateMutation = useMutation({
    mutationFn: api.updateSettingsConfig,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['settings'] });
    },
  });

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    await updateMutation.mutateAsync(formData);
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-brand-500"></div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-slate-100">Settings</h2>
          <p className="text-slate-400 mt-1">Configure application settings</p>
        </div>
      </div>

      {/* Settings Form */}
      <motion.form
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        onSubmit={handleSubmit}
        className="bg-dark-800 border border-slate-700 rounded-xl p-6"
      >
        <div className="space-y-6">
          {/* WhatsApp Settings */}
          <div className="border-b border-slate-700 pb-6">
            <div className="flex items-center gap-3 mb-4">
              <div className="p-2 bg-brand-500/20 rounded-lg">
                <Smartphone className="w-5 h-5 text-brand-400" />
              </div>
              <h3 className="text-lg font-semibold text-slate-100">WhatsApp Settings</h3>
            </div>
            
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-slate-300 mb-2">
                  Provider
                </label>
                <select
                  value={formData.whatsapp_provider}
                  onChange={(e) => setFormData({ ...formData, whatsapp_provider: e.target.value })}
                  className="w-full px-4 py-2 bg-slate-700 border border-slate-600 rounded-lg text-slate-200 focus:outline-none focus:ring-2 focus:ring-brand-500"
                >
                  <option value="baileys">Baileys</option>
                </select>
              </div>
              
              <div>
                <label className="block text-sm font-medium text-slate-300 mb-2">
                  Baileys Server URL
                </label>
                <input
                  type="text"
                  value={formData.baileys_server_url}
                  onChange={(e) => setFormData({ ...formData, baileys_server_url: e.target.value })}
                  className="w-full px-4 py-2 bg-slate-700 border border-slate-600 rounded-lg text-slate-200 focus:outline-none focus:ring-2 focus:ring-brand-500"
                />
              </div>
            </div>
            
            <div className="mt-4">
              <label className="flex items-center gap-3">
                <input
                  type="checkbox"
                  checked={formData.baileys_enabled}
                  onChange={(e) => setFormData({ ...formData, baileys_enabled: e.target.checked })}
                  className="w-4 h-4 rounded border-slate-600 text-brand-500 focus:ring-brand-500"
                />
                <span className="text-slate-300">Enable Baileys Integration</span>
              </label>
            </div>
          </div>

          {/* Database Settings */}
          <div className="border-b border-slate-700 pb-6">
            <div className="flex items-center gap-3 mb-4">
              <div className="p-2 bg-blue-500/20 rounded-lg">
                <Database className="w-5 h-5 text-blue-400" />
              </div>
              <h3 className="text-lg font-semibold text-slate-100">Database Settings</h3>
            </div>
            
            <div>
              <label className="block text-sm font-medium text-slate-300 mb-2">
                Busy Database File Path
              </label>
              <input
                type="text"
                value={formData.bds_file_path}
                onChange={(e) => setFormData({ ...formData, bds_file_path: e.target.value })}
                placeholder="C:\\Path\\To\\Your\\Database.bds"
                className="w-full px-4 py-2 bg-slate-700 border border-slate-600 rounded-lg text-slate-200 focus:outline-none focus:ring-2 focus:ring-brand-500"
              />
              <p className="text-sm text-slate-400 mt-1">Path to the Busy .bds database file</p>
            </div>
          </div>

          {/* Logging Settings */}
          <div>
            <div className="flex items-center gap-3 mb-4">
              <div className="p-2 bg-yellow-500/20 rounded-lg">
                <FileText className="w-5 h-5 text-yellow-400" />
              </div>
              <h3 className="text-lg font-semibold text-slate-100">Logging Settings</h3>
            </div>
            
            <div>
              <label className="block text-sm font-medium text-slate-300 mb-2">
                Log Level
              </label>
              <select
                value={formData.log_level}
                onChange={(e) => setFormData({ ...formData, log_level: e.target.value })}
                className="w-full px-4 py-2 bg-slate-700 border border-slate-600 rounded-lg text-slate-200 focus:outline-none focus:ring-2 focus:ring-brand-500"
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
            className="flex items-center gap-2 px-6 py-3 bg-brand-500 hover:bg-brand-600 text-white rounded-lg transition-colors disabled:opacity-50 font-medium"
          >
            {updateMutation.isPending ? (
              <>
                <Loader2 className="w-5 h-5 animate-spin" />
                Saving...
              </>
            ) : (
              <>
                <Save className="w-5 h-5" />
                Save Settings
              </>
            )}
          </button>
        </div>
      </motion.form>
    </div>
  );
}

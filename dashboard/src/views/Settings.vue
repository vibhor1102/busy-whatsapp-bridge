<template>
  <div class="bw-page">
    <div class="bw-page-header">
      <div>
        <h1>Settings</h1>
        <p class="subtitle">Application configuration</p>
      </div>
      <div class="header-actions">
        <Button icon="pi pi-refresh" label="Reload" severity="secondary" class="p-button-sm" :loading="loading" @click="loadSettings" />
        <Button icon="pi pi-save" label="Save" class="p-button-sm" :loading="saving" @click="saveSettings" />
      </div>
    </div>

    <!-- Configuration -->
    <div class="bw-section">
      <div class="bw-section-header">
        <h2><i class="pi pi-cog"></i> Configuration</h2>
      </div>
      <div class="bw-section-body">
        <div class="settings-grid">
          <div class="setting-field">
            <label>WhatsApp Provider</label>
            <Dropdown v-model="form.whatsapp_provider" :options="providerOptions" optionLabel="label" optionValue="value" class="w-full" />
          </div>
          <div class="setting-field">
            <label>Baileys Server URL</label>
            <InputText v-model="form.baileys_server_url" placeholder="http://localhost:3001" class="w-full" />
          </div>
          <div class="setting-field">
            <label>Log Level</label>
            <Dropdown v-model="form.log_level" :options="logLevelOptions" optionLabel="label" optionValue="value" class="w-full" />
          </div>
          <div class="setting-field">
            <label>BDS File Path</label>
            <InputText v-model="form.bds_file_path" placeholder="C:\Path\db12025.bds" class="w-full" />
          </div>
          <div class="setting-field switch-row">
            <InputSwitch v-model="form.baileys_enabled" />
            <label>Enable Baileys</label>
          </div>
        </div>
        <small class="settings-note">Changes are saved to conf.json. Some may require a restart.</small>
        <p v-if="message" class="settings-message">{{ message }}</p>
      </div>
    </div>

    <!-- Runtime Values -->
    <div class="bw-section">
      <div class="bw-section-header">
        <h2><i class="pi pi-code"></i> Runtime Values</h2>
      </div>
      <div class="bw-section-body">
        <pre class="runtime-json">{{ runtimeSettingsPretty }}</pre>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { api } from '@/services/api'
import Button from 'primevue/button'
import Dropdown from 'primevue/dropdown'
import InputText from 'primevue/inputtext'
import InputSwitch from 'primevue/inputswitch'

const loading = ref(false)
const saving = ref(false)
const message = ref('')
const runtimeSettings = ref<Record<string, any>>({})

const form = reactive({
  whatsapp_provider: 'baileys',
  baileys_server_url: 'http://localhost:3001',
  baileys_enabled: true,
  log_level: 'INFO',
  bds_file_path: '',
})

const providerOptions = [
  { label: 'Baileys', value: 'baileys' },
  { label: 'Meta', value: 'meta' },
  { label: 'Webhook', value: 'webhook' },
  { label: 'Evolution', value: 'evolution' },
]

const logLevelOptions = [
  { label: 'DEBUG', value: 'DEBUG' },
  { label: 'INFO', value: 'INFO' },
  { label: 'WARNING', value: 'WARNING' },
  { label: 'ERROR', value: 'ERROR' },
  { label: 'CRITICAL', value: 'CRITICAL' },
]

const runtimeSettingsPretty = computed(() => JSON.stringify(runtimeSettings.value, null, 2))

const loadSettings = async () => {
  loading.value = true; message.value = ''
  try {
    const [runtime, config] = await Promise.all([api.getSettings(), api.getSettingsConfig()])
    runtimeSettings.value = runtime
    const content = config.content || {}
    form.whatsapp_provider = content.whatsapp?.provider || runtime.WHATSAPP_PROVIDER || form.whatsapp_provider
    form.baileys_server_url = content.baileys?.server_url || runtime.BAILEYS_SERVER_URL || form.baileys_server_url
    form.baileys_enabled = Boolean(content.baileys?.enabled ?? runtime.BAILEYS_ENABLED)
    form.log_level = content.logging?.level || runtime.LOG_LEVEL || form.log_level
    form.bds_file_path = content.database?.bds_file_path || ''
  } catch { message.value = 'Failed to load settings.' } finally { loading.value = false }
}

const saveSettings = async () => {
  saving.value = true; message.value = ''
  try {
    const result = await api.updateSettingsConfig({
      whatsapp_provider: form.whatsapp_provider,
      baileys_server_url: form.baileys_server_url,
      baileys_enabled: form.baileys_enabled,
      log_level: form.log_level,
      bds_file_path: form.bds_file_path,
    })
    message.value = result.message || 'Settings saved.'
    await loadSettings()
  } catch (e: any) {
    message.value = e?.message || 'Failed to save.'
  } finally { saving.value = false }
}

onMounted(loadSettings)
</script>

<style scoped>
.header-actions {
  display: flex;
  gap: var(--bw-space-sm);
}

.settings-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: var(--bw-space-md);
}

.setting-field {
  display: flex;
  flex-direction: column;
  gap: 0.3rem;
}

.setting-field label {
  font-size: 0.75rem;
  color: var(--bw-text-muted);
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.04em;
}

.switch-row {
  flex-direction: row;
  align-items: center;
  gap: var(--bw-space-sm);
  margin-top: 1.5rem;
}

.switch-row label {
  text-transform: none;
  font-size: 0.875rem;
  font-weight: 500;
  color: var(--bw-text-primary);
}

.settings-note {
  display: block;
  margin-top: var(--bw-space-md);
  color: var(--bw-text-muted);
  font-size: 0.78rem;
}

.settings-message {
  margin-top: var(--bw-space-sm);
  color: var(--bw-brand-primary-light);
  font-size: 0.82rem;
}

.runtime-json {
  margin: 0;
  white-space: pre-wrap;
  word-break: break-word;
  font-size: 0.78rem;
  font-family: var(--bw-font-mono);
  color: var(--bw-text-secondary);
  line-height: 1.6;
  background: rgba(15, 23, 42, 0.4);
  padding: var(--bw-space-md);
  border-radius: var(--bw-radius-md);
  max-height: 400px;
  overflow: auto;
}
</style>

<template>
  <div class="page-container">
    <div class="page-head">
      <h1>Settings</h1>
      <div class="nav-links">
        <router-link to="/" class="nav-link">Overview</router-link>
        <router-link to="/whatsapp" class="nav-link">WhatsApp</router-link>
        <router-link to="/system" class="nav-link">System Control</router-link>
      </div>
    </div>

    <Card>
      <template #title>Configuration (conf.json)</template>
      <template #content>
        <div class="form-grid">
          <label>
            WhatsApp Provider
            <select v-model="form.whatsapp_provider">
              <option value="baileys">baileys</option>
              <option value="meta">meta</option>
              <option value="webhook">webhook</option>
              <option value="evolution">evolution</option>
            </select>
          </label>

          <label>
            Baileys Server URL
            <input v-model="form.baileys_server_url" type="text" placeholder="http://localhost:3001" />
          </label>

          <label>
            Log Level
            <select v-model="form.log_level">
              <option value="DEBUG">DEBUG</option>
              <option value="INFO">INFO</option>
              <option value="WARNING">WARNING</option>
              <option value="ERROR">ERROR</option>
              <option value="CRITICAL">CRITICAL</option>
            </select>
          </label>

          <label>
            BDS File Path
            <input v-model="form.bds_file_path" type="text" placeholder="C:\\Path\\db12025.bds" />
          </label>

          <label class="switch">
            <input v-model="form.baileys_enabled" type="checkbox" />
            Enable Baileys
          </label>
        </div>

        <div class="actions">
          <Button icon="pi pi-refresh" label="Reload" severity="secondary" :loading="loading" @click="loadSettings" />
          <Button icon="pi pi-save" label="Save Settings" :loading="saving" @click="saveSettings" />
        </div>

        <p class="note">
          Changes are persisted to `conf.json`. Some changes require restart to fully apply.
        </p>
        <p v-if="message" class="message">{{ message }}</p>
      </template>
    </Card>

    <Card>
      <template #title>Current Runtime Values</template>
      <template #content>
        <pre class="runtime">{{ runtimeSettingsPretty }}</pre>
      </template>
    </Card>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { api } from '@/services/api'
import Card from 'primevue/card'
import Button from 'primevue/button'

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

const runtimeSettingsPretty = computed(() => JSON.stringify(runtimeSettings.value, null, 2))

const loadSettings = async () => {
  loading.value = true
  message.value = ''
  try {
    const [runtime, config] = await Promise.all([
      api.getSettings(),
      api.getSettingsConfig(),
    ])
    runtimeSettings.value = runtime
    const content = config.content || {}
    form.whatsapp_provider = content.whatsapp?.provider || runtime.WHATSAPP_PROVIDER || form.whatsapp_provider
    form.baileys_server_url = content.baileys?.server_url || runtime.BAILEYS_SERVER_URL || form.baileys_server_url
    form.baileys_enabled = Boolean(content.baileys?.enabled ?? runtime.BAILEYS_ENABLED)
    form.log_level = content.logging?.level || runtime.LOG_LEVEL || form.log_level
    form.bds_file_path = content.database?.bds_file_path || ''
  } catch (error) {
    console.error('Failed to load settings', error)
    message.value = 'Failed to load settings.'
  } finally {
    loading.value = false
  }
}

const saveSettings = async () => {
  saving.value = true
  message.value = ''
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
  } catch (error: any) {
    console.error('Failed to save settings', error)
    message.value = error?.message || 'Failed to save settings.'
  } finally {
    saving.value = false
  }
}

onMounted(loadSettings)
</script>

<style scoped>
.page-container {
  max-width: 1400px;
  margin: 0 auto;
  display: grid;
  gap: 1rem;
}

.page-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
}

.nav-links {
  display: flex;
  gap: 0.5rem;
  flex-wrap: wrap;
}

.nav-link {
  padding: 0.25rem 0.6rem;
  border: 1px solid var(--surface-border);
  border-radius: 999px;
  text-decoration: none;
  color: var(--text-color-secondary);
  font-size: 0.75rem;
}

.form-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
  gap: 0.9rem;
}

label {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
  font-size: 0.8rem;
  color: var(--text-color-secondary);
}

select,
input[type="text"] {
  border: 1px solid var(--surface-border);
  border-radius: 6px;
  background: var(--surface-card);
  color: var(--text-color);
  padding: 0.45rem 0.55rem;
}

.switch {
  flex-direction: row;
  align-items: center;
  margin-top: 1.45rem;
  color: var(--text-color);
}

.actions {
  display: flex;
  gap: 0.6rem;
  margin-top: 1rem;
}

.note,
.message {
  margin-top: 0.8rem;
  color: var(--text-color-secondary);
}

.runtime {
  margin: 0;
  white-space: pre-wrap;
  word-break: break-word;
  font-size: 0.82rem;
}
</style>

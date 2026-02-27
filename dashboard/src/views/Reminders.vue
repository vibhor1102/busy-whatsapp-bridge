<template>
  <div class="reminders-page">
    <!-- Header Section -->
    <div class="page-header">
      <div class="header-content">
        <h1>Payment Reminders</h1>
        <p class="subtitle">Send payment reminders with attached ledgers</p>
        <div class="snapshot-meta" v-if="snapshotStatus">
          <span v-if="snapshotStatus.has_snapshot">
            Last refreshed: {{ formatDateTime(snapshotStatus.last_refreshed_at) }}
          </span>
          <span v-else>Snapshot not generated yet</span>
          <span class="divider">|</span>
          <span>Rows: {{ snapshotStatus.row_count }} | Due &gt; 0: {{ snapshotStatus.nonzero_count }}</span>
        </div>
      </div>
      <div class="header-actions">
        <Button
          label="Refresh Data"
          icon="pi pi-sync"
          class="p-button-outlined p-button-sm"
          @click="refreshSnapshot"
          :loading="snapshotRefreshing"
        />
      </div>
    </div>

    <!-- Error Message -->
    <Message v-if="loadError" severity="warn" :closable="false" class="mb-3">
      {{ loadError }}
    </Message>

    <!-- Stats Cards -->
    <div class="stats-grid">
      <Card class="stat-card">
        <template #content>
          <div class="stat-value">{{ stats?.eligible_parties || 0 }}</div>
          <div class="stat-label">Eligible Parties</div>
        </template>
      </Card>
      <Card class="stat-card">
        <template #content>
          <div class="stat-value">{{ stats?.enabled_parties || 0 }}</div>
          <div class="stat-label">With Reminders Enabled</div>
        </template>
      </Card>
      <Card class="stat-card">
        <template #content>
          <div class="stat-value">{{ formatCurrency(stats?.total_amount_due || 0) }}</div>
          <div class="stat-label">Total Amount Due</div>
        </template>
      </Card>
      <Card class="stat-card" :class="{ 'session-active': activeSession }">
        <template #content>
          <div class="stat-value" :class="{ 'text-primary': activeSession }">
            {{ activeSession ? activeSession.progress.percentage + '%' : 'Ready' }}
          </div>
          <div class="stat-label">
            {{ activeSession ? 'Session Progress' : 'No Active Session' }}
          </div>
        </template>
      </Card>
    </div>

    <!-- Active Session Panel -->
    <Card v-if="activeSession" class="session-panel mb-4">
      <template #title>
        <div class="flex justify-content-between align-items-center">
          <span class="session-title">
            <i class="pi pi-send"></i>
            Active Session: {{ activeSession.session_id }}
          </span>
          <Tag 
            :value="activeSession.state" 
            :severity="getSessionStateSeverity(activeSession.state)"
            class="session-tag"
          />
        </div>
      </template>
      <template #content>
        <div class="session-details">
          <div class="progress-section">
            <ProgressBar :value="activeSession.progress.percentage" class="session-progress" />
            <div class="progress-stats">
              <span>{{ activeSession.progress.current }} / {{ activeSession.progress.total }} parties</span>
              <span class="percentage">{{ activeSession.progress.percentage }}% complete</span>
            </div>
          </div>
          
          <div class="metrics-grid" v-if="activeSession.metrics">
            <div class="metric">
              <i class="pi pi-clock"></i>
              <span>Duration: {{ formatDuration(activeSession.metrics.duration_seconds) }}</span>
            </div>
            <div class="metric" v-if="activeSession.metrics.avg_delay_seconds">
              <i class="pi pi-pause"></i>
              <span>Avg Delay: {{ activeSession.metrics.avg_delay_seconds.toFixed(1) }}s</span>
            </div>
            <div class="metric" v-if="activeSession.metrics.typing_time_total">
              <i class="pi pi-pencil"></i>
              <span>Typing: {{ activeSession.metrics.typing_time_total.toFixed(0) }}s</span>
            </div>
          </div>
          
          <div class="session-controls">
            <Button
              v-if="['online', 'sending', 'typing', 'reading'].includes(activeSession.state)"
              label="Pause"
              icon="pi pi-pause"
              class="p-button-warning p-button-sm"
              @click="pauseSession"
            />
            <Button
              v-if="activeSession.state === 'paused'"
              label="Resume"
              icon="pi pi-play"
              class="p-button-success p-button-sm"
              @click="resumeSession"
            />
            <Button
              label="Stop"
              icon="pi pi-stop"
              class="p-button-danger p-button-sm ml-2"
              @click="stopSession"
            />
          </div>
        </div>
      </template>
    </Card>

    <!-- Template Section -->
    <Card class="template-section mb-4">
      <template #title>
        <div class="flex justify-content-between align-items-center">
          <span><i class="pi pi-envelope"></i> Message Template</span>
          <Button
            icon="pi pi-cog"
            label="Manage Templates"
            class="p-button-outlined p-button-sm"
            @click="showTemplateManager = true"
          />
        </div>
      </template>
      <template #content>
        <div class="template-selector">
          <Dropdown
            v-model="defaultTemplateId"
            :options="templates"
            optionLabel="name"
            optionValue="id"
            placeholder="Select Default Template"
            class="w-full md:w-30rem"
          />
          <small class="template-hint">
            This template will be used by default. You can assign different templates to individual parties below.
          </small>
        </div>
        <div v-if="selectedTemplate" class="template-preview mt-3">
          <label>Preview:</label>
          <div class="preview-box">
            <pre>{{ selectedTemplate.content }}</pre>
          </div>
        </div>
      </template>
    </Card>

    <!-- Anti-Spam Configuration -->
    <Card class="antispam-section mb-4">
      <template #title>
        <div class="flex justify-content-between align-items-center">
          <span><i class="pi pi-shield"></i> Anti-Spam Protection</span>
          <Tag :severity="antiSpamConfig.enabled ? 'success' : 'secondary'" :value="antiSpamConfig.enabled ? 'Enabled' : 'Disabled'" />
        </div>
      </template>
      <template #content>
        <div class="antispam-grid">
          <div class="antispam-toggle">
            <label class="toggle-label">
              <InputSwitch v-model="antiSpamConfig.enabled" @change="saveAntiSpamConfig" />
              <span>Enable Anti-Spam Features</span>
            </label>
            <small>Protects against WhatsApp bulk detection</small>
          </div>
          
          <div class="antispam-options" v-if="antiSpamConfig.enabled">
            <div class="option">
              <label class="toggle-label">
                <InputSwitch v-model="antiSpamConfig.message_inflation" @change="saveAntiSpamConfig" />
                <span>Message Size Inflation</span>
              </label>
              <small>Adds invisible characters (3-5x size)</small>
            </div>
            
            <div class="option">
              <label class="toggle-label">
                <InputSwitch v-model="antiSpamConfig.pdf_inflation" @change="saveAntiSpamConfig" />
                <span>PDF Size Inflation</span>
              </label>
              <small>Adds invisible metadata (1-3x size)</small>
            </div>
            
            <div class="option">
              <label class="toggle-label">
                <InputSwitch v-model="antiSpamConfig.typing_simulation" @change="saveAntiSpamConfig" />
                <span>Human Typing Simulation</span>
              </label>
              <small>Shows typing indicator before sending</small>
            </div>
            
            <div class="option">
              <label class="toggle-label">
                <InputSwitch v-model="antiSpamConfig.startup_delay_enabled" @change="saveAntiSpamConfig" />
                <span>Session Startup Delay</span>
              </label>
              <small>Waits 3-5 min before sending (sets online)</small>
            </div>
          </div>
        </div>
      </template>
    </Card>

    <!-- Split Party Selection -->
    <div class="parties-split-view">
      <!-- Selected Parties Panel -->
      <Card class="parties-panel selected-panel">
        <template #title>
          <div class="panel-header">
            <span class="panel-title">
              <i class="pi pi-check-circle"></i>
              Selected Parties
              <Tag :value="selectedParties.length.toString()" severity="primary" />
            </span>
            <span class="panel-amount">{{ formatCurrency(selectedTotalAmount) }}</span>
          </div>
        </template>
        <template #content>
          <div v-if="selectedParties.length === 0" class="empty-state">
            <i class="pi pi-users"></i>
            <p>No parties selected</p>
            <small>Select parties from the Available list</small>
          </div>
          
          <div v-else class="parties-list">
            <DataTable 
              :value="selectedParties" 
              class="p-datatable-sm"
              scrollable
              scrollHeight="400px"
              sortField="amount_due"
              :sortOrder="-1"
            >
              <Column field="name" header="Party Name" sortable>
                <template #body="{ data }">
                  <div class="party-name">
                    <span class="name">{{ data.name }}</span>
                    <span class="code">{{ data.code }}</span>
                  </div>
                </template>
              </Column>
              
              <Column field="amount_due" header="Amount Due" sortable>
                <template #body="{ data }">
                  <span class="amount">{{ formatCurrency(data.amount_due) }}</span>
                </template>
              </Column>
              
              <Column field="phone" header="Phone">
                <template #body="{ data }">
                  <span class="phone">{{ data.phone || 'N/A' }}</span>
                </template>
              </Column>
              
              <Column header="Template" style="width: 200px">
                <template #body="{ data }">
                  <Dropdown
                    v-model="partyTemplates[data.code]"
                    :options="templates"
                    optionLabel="name"
                    optionValue="id"
                    placeholder="Use Default"
                    class="template-dropdown"
                  />
                </template>
              </Column>
              
              <Column style="width: 80px">
                <template #body="{ data }">
                  <Button
                    icon="pi pi-times"
                    class="p-button-text p-button-danger p-button-sm"
                    @click="deselectParty(data.code)"
                    tooltip="Remove from selection"
                  />
                </template>
              </Column>
            </DataTable>
          </div>
          
          <div v-if="selectedParties.length > 0" class="panel-actions">
            <Button
              label="Clear All"
              icon="pi pi-trash"
              class="p-button-text p-button-danger p-button-sm"
              @click="clearAllSelections"
            />
          </div>
        </template>
      </Card>

      <!-- Available Parties Panel -->
      <Card class="parties-panel available-panel">
        <template #title>
          <div class="panel-header">
            <span class="panel-title">
              <i class="pi pi-users"></i>
              Available Parties
              <Tag :value="availableParties.length.toString()" severity="secondary" />
            </span>
            <div class="panel-filters">
              <span class="p-input-icon-left">
                <i class="pi pi-search" />
                <InputText 
                  v-model="searchQuery" 
                  placeholder="Search..." 
                  class="p-inputtext-sm"
                />
              </span>
              <Dropdown
                v-model="filterBy"
                :options="filterOptions"
                optionLabel="label"
                optionValue="value"
                class="p-dropdown-sm"
              />
            </div>
          </div>
        </template>
        <template #content>
          <div class="parties-list">
            <DataTable 
              :value="filteredAvailableParties" 
              class="p-datatable-sm"
              scrollable
              scrollHeight="400px"
              sortField="amount_due"
              :sortOrder="-1"
              lazy
              @page="onPageChange"
              :first="first"
              :rows="rows"
              :totalRecords="totalRecords"
              paginator
              :rowsPerPageOptions="[10, 25, 50]"
            >
              <Column style="width: 50px">
                <template #body="{ data }">
                  <Checkbox 
                    :modelValue="isSelected(data.code)"
                    @change="(e) => toggleSelection(data, e.checked)"
                  />
                </template>
              </Column>
              
              <Column field="name" header="Party Name" sortable>
                <template #body="{ data }">
                  <div class="party-name">
                    <span class="name">{{ data.name }}</span>
                    <span class="code">{{ data.code }}</span>
                  </div>
                </template>
              </Column>
              
              <Column field="amount_due" header="Amount Due" sortable>
                <template #body="{ data }">
                  <span class="amount">{{ formatCurrency(data.amount_due) }}</span>
                </template>
              </Column>
              
              <Column field="phone" header="Phone">
                <template #body="{ data }">
                  <span class="phone">{{ data.phone || 'N/A' }}</span>
                </template>
              </Column>
              
              <Column field="last_reminder_sent" header="Last Reminder" sortable>
                <template #body="{ data }">
                  <span class="last-reminder">
                    {{ data.last_reminder_sent ? formatDateTime(data.last_reminder_sent) : 'Never' }}
                  </span>
                </template>
              </Column>
            </DataTable>
          </div>
          
          <div class="panel-actions">
            <Button
              label="Select All on Page"
              icon="pi pi-check-square"
              class="p-button-text p-button-sm"
              @click="selectPage"
            />
          </div>
        </template>
      </Card>
    </div>

    <!-- Action Bar -->
    <div class="action-bar">
      <div class="action-info">
        <span class="selection-count">
          <strong>{{ selectedParties.length }}</strong> parties selected
        </span>
        <span class="total-amount">
          Total: <strong>{{ formatCurrency(selectedTotalAmount) }}</strong>
        </span>
      </div>
      
      <div class="action-buttons">
        <Button
          label="Export Selected"
          icon="pi pi-download"
          class="p-button-outlined p-button-secondary mr-2"
          @click="exportSelected"
          :disabled="selectedParties.length === 0"
        />
        <Button
          label="Send Reminders"
          icon="pi pi-send"
          class="p-button-primary p-button-lg"
          :disabled="selectedParties.length === 0 || !defaultTemplateId || activeSession"
          :loading="sending"
          @click="confirmSend"
        />
      </div>
    </div>

    <!-- Send Confirmation Dialog -->
    <Dialog 
      v-model:visible="showConfirmDialog" 
      header="Confirm Send" 
      modal 
      :style="{ width: '450px' }"
    >
      <div class="confirm-content">
        <div class="confirm-icon">
          <i class="pi pi-exclamation-triangle"></i>
        </div>
        <div class="confirm-details">
          <p>You are about to send reminders to:</p>
          <ul>
            <li><strong>{{ selectedParties.length }}</strong> parties</li>
            <li>Total amount: <strong>{{ formatCurrency(selectedTotalAmount) }}</strong></li>
            <li>Using template: <strong>{{ selectedTemplate?.name || 'Default' }}</strong></li>
          </ul>
          <div class="confirm-antispam" v-if="antiSpamConfig.enabled">
            <Tag severity="success" value="Anti-Spam Enabled" />
            <small>
              Estimated time: {{ estimatedDuration }}
              (includes {{ antiSpamConfig.startup_delay_enabled ? '3-5 min startup delay' : 'no startup delay' }})
            </small>
          </div>
        </div>
      </div>
      <template #footer>
        <Button label="Cancel" icon="pi pi-times" class="p-button-text" @click="showConfirmDialog = false" />
        <Button label="Send Now" icon="pi pi-send" class="p-button-primary" @click="sendReminders" :loading="sending" />
      </template>
    </Dialog>

    <!-- Template Manager Dialog -->
    <Dialog 
      v-model:visible="showTemplateManager" 
      header="Template Manager" 
      modal 
      maximizable
      :style="{ width: '900px', height: '600px' }"
    >
      <TemplateManager 
        @close="showTemplateManager = false"
        @template-saved="onTemplateSaved"
      />
    </Dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import Button from 'primevue/button'
import Card from 'primevue/card'
import Checkbox from 'primevue/checkbox'
import Column from 'primevue/column'
import DataTable from 'primevue/datatable'
import Dialog from 'primevue/dialog'
import Dropdown from 'primevue/dropdown'
import InputSwitch from 'primevue/inputswitch'
import InputText from 'primevue/inputtext'
import Message from 'primevue/message'
import ProgressBar from 'primevue/progressbar'
import Tag from 'primevue/tag'
import { useToast } from 'primevue/usetoast'
import type { DataTablePageEvent } from 'primevue/datatable'
import { api } from '@/services/api'
import type {
  MessageTemplate,
  PartyReminderInfo,
  ReminderConfig,
  ReminderSnapshotStatus,
  ReminderStats,
} from '@/types'

const toast = useToast()

// State
const loading = ref(false)
const sending = ref(false)
const snapshotRefreshing = ref(false)
const loadError = ref('')

const config = ref<ReminderConfig | null>(null)
const templates = ref<MessageTemplate[]>([])
const defaultTemplateId = ref('')
const partyTemplates = ref<Record<string, string>>({}) // Per-party template assignments
const stats = ref<ReminderStats | null>(null)
const snapshotStatus = ref<ReminderSnapshotStatus | null>(null)

// Anti-spam configuration
const antiSpamConfig = ref({
  enabled: true,
  message_inflation: true,
  pdf_inflation: true,
  typing_simulation: true,
  startup_delay_enabled: true
})

// Session state
const activeSession = ref<{
  session_id: string
  state: string
  progress: {
    current: number
    total: number
    percentage: number
  }
  metrics?: {
    duration_seconds: number
    avg_delay_seconds?: number
    typing_time_total?: number
  }
} | null>(null)

// Party selection state
const allParties = ref<PartyReminderInfo[]>([])
const selectedPartyCodes = ref<Set<string>>(new Set())
const totalRecords = ref(0)
const first = ref(0)
const rows = ref(25)
const filterBy = ref('all')
const searchQuery = ref('')

// UI state
const showConfirmDialog = ref(false)
const showTemplateManager = ref(false)

// Computed
const selectedParties = computed(() => {
  return allParties.value.filter(p => selectedPartyCodes.value.has(p.code))
})

const availableParties = computed(() => {
  return allParties.value.filter(p => !selectedPartyCodes.value.has(p.code))
})

const filteredAvailableParties = computed(() => {
  let parties = availableParties.value
  
  // Apply search filter
  if (searchQuery.value) {
    const query = searchQuery.value.toLowerCase()
    parties = parties.filter(p => 
      p.name.toLowerCase().includes(query) || 
      p.code.toLowerCase().includes(query) ||
      (p.phone && p.phone.includes(query))
    )
  }
  
  // Apply filter
  if (filterBy.value === 'enabled') {
    parties = parties.filter(p => p.permanent_enabled)
  } else if (filterBy.value === 'recent') {
    const thirtyDaysAgo = new Date()
    thirtyDaysAgo.setDate(thirtyDaysAgo.getDate() - 30)
    parties = parties.filter(p => 
      !p.last_reminder_sent || new Date(p.last_reminder_sent) < thirtyDaysAgo
    )
  }
  
  return parties
})

const selectedTotalAmount = computed(() => {
  return selectedParties.value.reduce((sum, p) => sum + Number(p.amount_due || 0), 0)
})

const selectedTemplate = computed(() => {
  return templates.value.find(t => t.id === defaultTemplateId.value)
})

const estimatedDuration = computed(() => {
  const count = selectedParties.value.length
  if (count === 0) return '0 min'
  
  // Base calculation: ~15s per message average
  const baseSeconds = count * 15
  
  // Add startup delay
  const startupDelay = antiSpamConfig.value.startup_delay_enabled ? 240 : 0 // 4 min average
  
  // Add typing simulation
  const typingDelay = antiSpamConfig.value.typing_simulation ? count * 8 : 0
  
  const totalSeconds = baseSeconds + startupDelay + typingDelay
  const minutes = Math.ceil(totalSeconds / 60)
  
  if (minutes < 60) {
    return `${minutes} min`
  } else {
    const hours = Math.floor(minutes / 60)
    const mins = minutes % 60
    return `${hours}h ${mins}m`
  }
})

const filterOptions = [
  { label: 'All Parties', value: 'all' },
  { label: 'Reminders Enabled', value: 'enabled' },
  { label: 'Not Recent', value: 'recent' }
]

// Methods
function isSelected(code: string): boolean {
  return selectedPartyCodes.value.has(code)
}

function toggleSelection(party: PartyReminderInfo, checked: boolean): void {
  if (checked) {
    selectedPartyCodes.value.add(party.code)
  } else {
    selectedPartyCodes.value.delete(party.code)
  }
}

function deselectParty(code: string): void {
  selectedPartyCodes.value.delete(code)
}

function selectPage(): void {
  filteredAvailableParties.value.forEach(p => {
    selectedPartyCodes.value.add(p.code)
  })
}

function clearAllSelections(): void {
  selectedPartyCodes.value.clear()
  partyTemplates.value = {}
}

function formatCurrency(amount: number): string {
  const symbol = config.value?.currency_symbol || '₹'
  return `${symbol}${new Intl.NumberFormat('en-IN', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(amount)}`
}

function formatDateTime(dt: string | null): string {
  if (!dt) return 'N/A'
  return new Date(dt).toLocaleString('en-IN', {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  })
}

function formatDuration(seconds: number): string {
  if (seconds < 60) return `${seconds}s`
  const mins = Math.floor(seconds / 60)
  const secs = seconds % 60
  if (mins < 60) return `${mins}m ${secs}s`
  const hours = Math.floor(mins / 60)
  const remainingMins = mins % 60
  return `${hours}h ${remainingMins}m`
}

function getSessionStateSeverity(state: string): string {
  switch (state) {
    case 'online':
    case 'sending':
      return 'success'
    case 'typing':
    case 'reading':
      return 'info'
    case 'paused':
      return 'warning'
    case 'stopped':
    case 'error':
      return 'danger'
    default:
      return 'secondary'
  }
}

// API Calls
async function loadData(): Promise<void> {
  loading.value = true
  try {
    await Promise.all([
      loadConfig(),
      loadTemplates(),
      loadStats(),
      loadParties()
    ])
  } finally {
    loading.value = false
  }
}

async function loadConfig(): Promise<void> {
  try {
    config.value = await api.getReminderConfig()
  } catch (e) {
    console.error('Failed to load config', e)
  }
}

async function loadTemplates(): Promise<void> {
  try {
    templates.value = await api.getTemplates()
    // Set default template
    const defaultTemplate = templates.value.find(t => t.is_default)
    if (defaultTemplate && !defaultTemplateId.value) {
      defaultTemplateId.value = defaultTemplate.id
    }
  } catch (e) {
    console.error('Failed to load templates', e)
  }
}

async function loadStats(): Promise<void> {
  try {
    stats.value = await api.getReminderStats()
  } catch (e) {
    console.error('Failed to load stats', e)
  }
}

async function loadParties(): Promise<void> {
  try {
    const response = await api.getEligibleParties({
      offset: first.value,
      limit: rows.value,
      filter_by: filterBy.value
    })
    allParties.value = response.items
    totalRecords.value = response.total
  } catch (e) {
    console.error('Failed to load parties', e)
  }
}

async function refreshSnapshot(): Promise<void> {
  snapshotRefreshing.value = true
  try {
    snapshotStatus.value = await api.refreshReminderSnapshot()
    toast.add({
      severity: 'success',
      summary: 'Snapshot Refreshed',
      detail: `Found ${snapshotStatus.value.row_count} parties`,
      life: 3000
    })
    await loadParties()
  } catch {
    toast.add({
      severity: 'error',
      summary: 'Refresh Failed',
      detail: 'Could not refresh data',
      life: 3000
    })
  } finally {
    snapshotRefreshing.value = false
  }
}

async function saveAntiSpamConfig(): Promise<void> {
  try {
    await api.updateAntiSpamConfig(antiSpamConfig.value)
    toast.add({
      severity: 'success',
      summary: 'Settings Saved',
      detail: 'Anti-spam configuration updated',
      life: 2000
    })
  } catch {
    toast.add({
      severity: 'error',
      summary: 'Error',
      detail: 'Failed to save settings',
      life: 3000
    })
  }
}

function confirmSend(): void {
  if (selectedParties.value.length === 0) return
  showConfirmDialog.value = true
}

async function sendReminders(): Promise<void> {
  sending.value = true
  showConfirmDialog.value = false
  
  try {
    const partyCodes = Array.from(selectedPartyCodes.value)
    
    // Build party-template mapping
    const partyTemplateMap: Record<string, string> = {}
    partyCodes.forEach(code => {
      if (partyTemplates.value[code]) {
        partyTemplateMap[code] = partyTemplates.value[code]
      }
    })
    
    const result = await api.sendReminders(partyCodes, defaultTemplateId.value, partyTemplateMap)
    
    if (result.session_id) {
      activeSession.value = {
        session_id: result.session_id,
        state: 'starting',
        progress: {
          current: 0,
          total: partyCodes.length,
          percentage: 0
        }
      }
      startSessionPolling(result.session_id)
    }
    
    toast.add({
      severity: 'success',
      summary: 'Session Started',
      detail: `Sending to ${partyCodes.length} parties. ${antiSpamConfig.value.startup_delay_enabled ? 'Startup delay active.' : ''}`,
      life: 5000
    })
    
    // Clear selection after successful start
    selectedPartyCodes.value.clear()
    partyTemplates.value = {}
  } catch {
    toast.add({
      severity: 'error',
      summary: 'Error',
      detail: 'Failed to start reminder session',
      life: 3000
    })
  } finally {
    sending.value = false
  }
}

function startSessionPolling(sessionId: string): void {
  const interval = setInterval(async () => {
    try {
      const status = await api.getSessionStatus(sessionId)
      if (status) {
        activeSession.value = {
          session_id: sessionId,
          state: status.state,
          progress: status.progress,
          metrics: status.metrics
        }
        
        if (['completed', 'stopped', 'error'].includes(status.state)) {
          clearInterval(interval)
          setTimeout(() => {
            activeSession.value = null
          }, 10000) // Keep visible for 10 seconds after completion
        }
      }
    } catch {
      clearInterval(interval)
      activeSession.value = null
    }
  }, 2000)
}

async function pauseSession(): Promise<void> {
  if (!activeSession.value?.session_id) return
  try {
    await api.pauseSession(activeSession.value.session_id)
    toast.add({ severity: 'info', summary: 'Paused', detail: 'Session paused', life: 2000 })
  } catch {
    toast.add({ severity: 'error', summary: 'Error', detail: 'Failed to pause', life: 3000 })
  }
}

async function resumeSession(): Promise<void> {
  if (!activeSession.value?.session_id) return
  try {
    await api.resumeSession(activeSession.value.session_id)
    toast.add({ severity: 'success', summary: 'Resumed', detail: 'Session resumed', life: 2000 })
  } catch {
    toast.add({ severity: 'error', summary: 'Error', detail: 'Failed to resume', life: 3000 })
  }
}

async function stopSession(): Promise<void> {
  if (!activeSession.value?.session_id) return
  try {
    await api.stopSession(activeSession.value.session_id)
    activeSession.value = null
    toast.add({ severity: 'success', summary: 'Stopped', detail: 'Session stopped', life: 2000 })
  } catch {
    toast.add({ severity: 'error', summary: 'Error', detail: 'Failed to stop', life: 3000 })
  }
}

function onPageChange(event: DataTablePageEvent): void {
  first.value = event.first
  rows.value = event.rows
  loadParties()
}

function onTemplateSaved(): void {
  loadTemplates()
}

function exportSelected(): void {
  const data = selectedParties.value.map(p => ({
    code: p.code,
    name: p.name,
    phone: p.phone,
    amount_due: p.amount_due,
    template: partyTemplates.value[p.code] || defaultTemplateId.value
  }))
  
  const csv = [
    ['Code', 'Name', 'Phone', 'Amount Due', 'Template ID'].join(','),
    ...data.map(row => [
      row.code,
      `"${row.name}"`,
      row.phone,
      row.amount_due,
      row.template
    ].join(','))
  ].join('\n')
  
  const blob = new Blob([csv], { type: 'text/csv' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `selected-parties-${new Date().toISOString().split('T')[0]}.csv`
  a.click()
  URL.revokeObjectURL(url)
  
  toast.add({ severity: 'success', summary: 'Exported', detail: 'CSV file downloaded', life: 3000 })
}

// Watchers
watch(filterBy, () => {
  first.value = 0
  loadParties()
})

watch(searchQuery, () => {
  // Debounce could be added here
})

// Lifecycle
onMounted(() => {
  loadData()
})
</script>

<style scoped>
.reminders-page {
  padding: 1.5rem;
  max-width: 1600px;
  margin: 0 auto;
}

/* Header */
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 1.5rem;
}

.header-content h1 {
  margin: 0 0 0.25rem 0;
  font-size: 1.75rem;
  font-weight: 600;
}

.subtitle {
  margin: 0 0 0.5rem 0;
  color: var(--text-color-secondary);
}

.snapshot-meta {
  display: flex;
  gap: 0.75rem;
  font-size: 0.875rem;
  color: var(--text-color-secondary);
}

.divider {
  color: var(--surface-400);
}

/* Stats Grid */
.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 1rem;
  margin-bottom: 1.5rem;
}

.stat-card {
  text-align: center;
}

.stat-card.session-active {
  border: 2px solid var(--primary-color);
}

.stat-value {
  font-size: 1.75rem;
  font-weight: 700;
  color: var(--text-color);
  margin-bottom: 0.25rem;
}

.stat-value.text-primary {
  color: var(--primary-color);
}

.stat-label {
  font-size: 0.875rem;
  color: var(--text-color-secondary);
}

/* Session Panel */
.session-panel {
  border-left: 4px solid var(--primary-color);
}

.session-title {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-weight: 600;
}

.session-tag {
  text-transform: capitalize;
}

.session-details {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.progress-section {
  width: 100%;
}

.session-progress {
  height: 1rem;
  margin-bottom: 0.5rem;
}

.progress-stats {
  display: flex;
  justify-content: space-between;
  font-size: 0.875rem;
  color: var(--text-color-secondary);
}

.progress-stats .percentage {
  font-weight: 600;
  color: var(--primary-color);
}

.metrics-grid {
  display: flex;
  gap: 2rem;
  flex-wrap: wrap;
}

.metric {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.875rem;
  color: var(--text-color-secondary);
}

.metric i {
  color: var(--primary-color);
}

.session-controls {
  display: flex;
  gap: 0.5rem;
  padding-top: 0.5rem;
  border-top: 1px solid var(--surface-200);
}

/* Template Section */
.template-section {
  margin-bottom: 1.5rem;
}

.template-selector {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.template-hint {
  color: var(--text-color-secondary);
  font-size: 0.875rem;
}

.template-preview {
  background: var(--surface-100);
  padding: 1rem;
  border-radius: 6px;
}

.template-preview label {
  font-weight: 600;
  margin-bottom: 0.5rem;
  display: block;
}

.preview-box pre {
  margin: 0;
  white-space: pre-wrap;
  word-wrap: break-word;
  font-size: 0.875rem;
  color: var(--text-color-secondary);
}

/* Anti-Spam Section */
.antispam-section {
  margin-bottom: 1.5rem;
}

.antispam-grid {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.antispam-toggle,
.antispam-options .option {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.toggle-label {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  font-weight: 500;
  cursor: pointer;
}

.antispam-options {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 1rem;
  padding-left: 2.5rem;
}

.antispam-options small {
  color: var(--text-color-secondary);
  font-size: 0.75rem;
}

/* Split View */
.parties-split-view {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1rem;
  margin-bottom: 1.5rem;
}

@media (max-width: 1200px) {
  .parties-split-view {
    grid-template-columns: 1fr;
  }
}

.parties-panel {
  min-height: 500px;
}

.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  width: 100%;
}

.panel-title {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-weight: 600;
}

.panel-amount {
  font-weight: 600;
  color: var(--primary-color);
}

.panel-filters {
  display: flex;
  gap: 0.5rem;
  align-items: center;
}

/* Party Tables */
.parties-list {
  min-height: 300px;
}

.party-name {
  display: flex;
  flex-direction: column;
}

.party-name .name {
  font-weight: 500;
}

.party-name .code {
  font-size: 0.75rem;
  color: var(--text-color-secondary);
}

.amount {
  font-weight: 600;
  color: var(--primary-color);
}

.phone {
  font-size: 0.875rem;
  color: var(--text-color-secondary);
}

.last-reminder {
  font-size: 0.875rem;
  color: var(--text-color-secondary);
}

.template-dropdown {
  width: 100%;
}

/* Empty State */
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 3rem;
  color: var(--text-color-secondary);
  text-align: center;
}

.empty-state i {
  font-size: 3rem;
  margin-bottom: 1rem;
  opacity: 0.5;
}

.empty-state p {
  margin: 0 0 0.5rem 0;
  font-weight: 500;
}

/* Panel Actions */
.panel-actions {
  display: flex;
  justify-content: flex-end;
  padding-top: 0.75rem;
  margin-top: 0.75rem;
  border-top: 1px solid var(--surface-200);
}

/* Action Bar */
.action-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1rem 1.5rem;
  background: var(--surface-card);
  border-radius: 6px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
  position: sticky;
  bottom: 1rem;
}

.action-info {
  display: flex;
  gap: 2rem;
}

.selection-count,
.total-amount {
  font-size: 0.875rem;
  color: var(--text-color-secondary);
}

.selection-count strong,
.total-amount strong {
  color: var(--text-color);
  font-size: 1.125rem;
}

/* Confirm Dialog */
.confirm-content {
  display: flex;
  gap: 1rem;
  align-items: flex-start;
}

.confirm-icon {
  font-size: 2.5rem;
  color: var(--orange-500);
}

.confirm-details ul {
  margin: 0.5rem 0;
  padding-left: 1.25rem;
}

.confirm-details li {
  margin-bottom: 0.25rem;
}

.confirm-antispam {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
  margin-top: 1rem;
  padding-top: 1rem;
  border-top: 1px solid var(--surface-200);
}

/* Responsive */
@media (max-width: 768px) {
  .page-header {
    flex-direction: column;
    gap: 1rem;
  }
  
  .action-bar {
    flex-direction: column;
    gap: 1rem;
    align-items: stretch;
  }
  
  .action-info {
    justify-content: space-between;
  }
  
  .action-buttons {
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
  }
  
  .action-buttons button {
    width: 100%;
  }
}
</style>

<template>
  <div class="reminders-page">
    <!-- Header -->
    <div class="page-header">
      <div class="header-content">
        <h1>Payment Reminders</h1>
        <p class="subtitle">Send automated payment reminders with attached ledgers</p>
      </div>
      <div class="header-actions">
        <Button
          icon="pi pi-refresh"
          class="p-button-outlined"
          @click="refreshData"
          :loading="loading"
        />
        <Button
          icon="pi pi-cog"
          class="p-button-outlined ml-2"
          @click="showConfigPanel = true"
        />
      </div>
    </div>

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
          <div class="stat-label">Reminders Enabled</div>
        </template>
      </Card>
      <Card class="stat-card">
        <template #content>
          <div class="stat-value">{{ formatCurrency(stats?.total_amount_due || 0) }}</div>
          <div class="stat-label">Total Amount Due</div>
        </template>
      </Card>
      <Card class="stat-card">
        <template #content>
          <div class="stat-value" :class="schedulerStatusClass">
            {{ schedulerStatusText }}
          </div>
          <div class="stat-label">Scheduler Status</div>
        </template>
      </Card>
    </div>

    <!-- Configuration Panel -->
    <Card v-if="showConfigPanel" class="config-panel mb-4">
      <template #title>
        <div class="flex justify-content-between align-items-center">
          <span>Configuration</span>
          <Button icon="pi pi-times" class="p-button-text" @click="showConfigPanel = false" />
        </div>
      </template>
      <template #content>
        <div class="config-grid">
          <div class="config-section">
            <h4>Schedule Settings</h4>
            <div class="field">
              <label>Enable Scheduler</label>
              <InputSwitch v-model="config.schedule.enabled" @change="saveSchedule" />
            </div>
            <div class="field">
              <label>Frequency</label>
              <Dropdown
                v-model="config.schedule.frequency"
                :options="frequencyOptions"
                optionLabel="label"
                optionValue="value"
                @change="saveSchedule"
              />
            </div>
            <div class="field">
              <label>Day of Week</label>
              <Dropdown
                v-model="config.schedule.day_of_week"
                :options="dayOptions"
                optionLabel="label"
                optionValue="value"
                @change="saveSchedule"
              />
            </div>
            <div class="field">
              <label>Time</label>
              <InputMask
                v-model="config.schedule.time"
                mask="99:99"
                placeholder="HH:MM"
                @blur="saveSchedule"
              />
            </div>
          </div>
          <div class="config-section">
            <h4>Scheduler Control</h4>
            <div class="button-group">
              <Button
                label="Start"
                icon="pi pi-play"
                class="p-button-success"
                @click="startScheduler"
                :disabled="schedulerStatus?.is_running"
              />
              <Button
                label="Stop"
                icon="pi pi-stop"
                class="p-button-danger"
                @click="stopScheduler"
                :disabled="!schedulerStatus?.is_running"
              />
              <Button
                label="Trigger Now"
                icon="pi pi-send"
                class="p-button-primary"
                @click="triggerManualRun"
              />
            </div>
          </div>
        </div>
      </template>
    </Card>

    <!-- Template Selector -->
    <Card class="template-panel mb-4">
      <template #title>
        <div class="flex justify-content-between align-items-center">
          <span>Message Template</span>
          <div class="flex gap-2">
            <Button
              icon="pi pi-pencil"
              label="Edit Templates"
              class="p-button-outlined p-button-sm"
              @click="showTemplateEditor = true"
            />
          </div>
        </div>
      </template>
      <template #content>
        <div class="template-selector">
          <Dropdown
            v-model="selectedTemplateId"
            :options="templates"
            optionLabel="name"
            optionValue="id"
            placeholder="Select Template"
            class="w-full md:w-30rem"
            @change="onTemplateChange"
          />
          <div v-if="selectedTemplate" class="template-preview mt-3">
            <label>Preview:</label>
            <div class="preview-box">
              <pre>{{ selectedTemplate.content }}</pre>
            </div>
          </div>
        </div>
      </template>
    </Card>

    <!-- Party Selection -->
    <Card class="party-selection">
      <template #title>
        <div class="flex flex-wrap justify-content-between align-items-center gap-2">
          <span>Party Selection ({{ filteredParties.length }} eligible)</span>
          <div class="flex flex-wrap gap-2">
            <span class="p-input-icon-left">
              <i class="pi pi-search" />
              <InputText
                v-model="searchQuery"
                placeholder="Search parties..."
                class="p-inputtext-sm"
              />
            </span>
            <Dropdown
              v-model="sortBy"
              :options="sortOptions"
              optionLabel="label"
              optionValue="value"
              placeholder="Sort by"
              class="p-dropdown-sm"
            />
            <Dropdown
              v-model="filterBy"
              :options="filterOptions"
              optionLabel="label"
              optionValue="value"
              placeholder="Filter"
              class="p-dropdown-sm"
            />
          </div>
        </div>
      </template>
      <template #content>
        <div class="selection-actions mb-3">
          <Button
            label="Select All"
            icon="pi pi-check-square"
            class="p-button-outlined p-button-sm"
            @click="selectAll"
          />
          <Button
            label="Deselect All"
            icon="pi pi-minus-square"
            class="p-button-outlined p-button-sm ml-2"
            @click="deselectAll"
          />
          <span class="ml-3 text-muted">
            Selected: {{ selectedTempCount }} parties ({{ formatCurrency(selectedTotalAmount) }})
          </span>
        </div>

        <!-- Selected Parties Group -->
        <div v-if="selectedParties.length > 0" class="party-group">
          <h4 class="group-title">
            <i class="pi pi-check-circle text-green-500"></i>
            Selected for This Batch ({{ selectedParties.length }})
          </h4>
          <DataTable
            :value="selectedParties"
            class="p-datatable-sm"
            stripedRows
            responsiveLayout="scroll"
          >
            <Column style="width: 3rem">
              <template #body="{ data }">
                <Checkbox v-model="data.temp_enabled" :binary="true" @change="updateTempSelection(data)" />
              </template>
            </Column>
            <Column field="name" header="Party Name" sortable>
              <template #body="{ data }">
                <div class="party-name">
                  <span class="font-medium">{{ data.name }}</span>
                  <span class="text-xs text-secondary">Code: {{ data.code }}</span>
                </div>
              </template>
            </Column>
            <Column field="amount_due_formatted" header="Amount Due" sortable style="width: 150px">
              <template #body="{ data }">
                <span class="amount-due">{{ data.amount_due_formatted }}</span>
              </template>
            </Column>
            <Column field="sales_credit_days" header="Credit" sortable style="width: 100px">
              <template #body="{ data }">
                <span class="credit-days">{{ data.sales_credit_days }}d</span>
              </template>
            </Column>
            <Column header="Permanent" style="width: 120px">
              <template #body="{ data }">
                <ToggleButton
                  v-model="data.permanent_enabled"
                  onIcon="pi pi-check"
                  offIcon="pi pi-times"
                  onLabel="On"
                  offLabel="Off"
                  class="p-button-sm"
                  @change="updatePermanentSelection(data)"
                />
              </template>
            </Column>
            <Column header="Actions" style="width: 120px">
              <template #body="{ data }">
                <Button
                  icon="pi pi-file-pdf"
                  class="p-button-text p-button-sm"
                  @click="generateLedger(data.code)"
                  tooltip="Generate Ledger"
                />
              </template>
            </Column>
          </DataTable>
        </div>

        <!-- Unselected Parties Group -->
        <div v-if="unselectedParties.length > 0" class="party-group mt-4">
          <h4 class="group-title">
            <i class="pi pi-circle text-gray-400"></i>
            Not Selected ({{ unselectedParties.length }})
          </h4>
          <DataTable
            :value="unselectedParties"
            class="p-datatable-sm"
            stripedRows
            responsiveLayout="scroll"
          >
            <Column style="width: 3rem">
              <template #body="{ data }">
                <Checkbox v-model="data.temp_enabled" :binary="true" @change="updateTempSelection(data)" />
              </template>
            </Column>
            <Column field="name" header="Party Name" sortable>
              <template #body="{ data }">
                <div class="party-name">
                  <span class="font-medium">{{ data.name }}</span>
                  <span class="text-xs text-secondary">Code: {{ data.code }}</span>
                </div>
              </template>
            </Column>
            <Column field="amount_due_formatted" header="Amount Due" sortable style="width: 150px">
              <template #body="{ data }">
                <span class="amount-due">{{ data.amount_due_formatted }}</span>
              </template>
            </Column>
            <Column field="sales_credit_days" header="Credit" sortable style="width: 100px">
              <template #body="{ data }">
                <span class="credit-days">{{ data.sales_credit_days }}d</span>
              </template>
            </Column>
            <Column header="Permanent" style="width: 120px">
              <template #body="{ data }">
                <ToggleButton
                  v-model="data.permanent_enabled"
                  onIcon="pi pi-check"
                  offIcon="pi pi-times"
                  onLabel="On"
                  offLabel="Off"
                  class="p-button-sm"
                  @change="updatePermanentSelection(data)"
                />
              </template>
            </Column>
            <Column header="Actions" style="width: 120px">
              <template #body="{ data }">
                <Button
                  icon="pi pi-file-pdf"
                  class="p-button-text p-button-sm"
                  @click="generateLedger(data.code)"
                  tooltip="Generate Ledger"
                />
              </template>
            </Column>
          </DataTable>
        </div>
      </template>
    </Card>

    <!-- Action Buttons -->
    <div class="action-bar">
      <Button
        label="Send Now"
        icon="pi pi-send"
        class="p-button-primary p-button-lg"
        :disabled="selectedTempCount === 0"
        @click="confirmSend"
      />
      <Button
        label="Schedule for Later"
        icon="pi pi-calendar"
        class="p-button-outlined p-button-lg ml-3"
        :disabled="selectedTempCount === 0"
        @click="showScheduleDialog = true"
      />
      <Button
        label="Export CSV"
        icon="pi pi-download"
        class="p-button-outlined p-button-lg ml-3"
        @click="exportCsv"
      />
    </div>

    <!-- Schedule Dialog -->
    <Dialog
      v-model:visible="showScheduleDialog"
      header="Schedule Reminders"
      modal
      :style="{ width: '450px' }"
    >
      <div class="schedule-form">
        <div class="field">
          <label>Schedule Date</label>
          <Calendar v-model="scheduleDate" :minDate="new Date()" dateFormat="yy-mm-dd" />
        </div>
        <div class="field">
          <label>Schedule Time</label>
          <InputMask v-model="scheduleTime" mask="99:99" placeholder="HH:MM" />
        </div>
        <div class="summary">
          <p><strong>Selected:</strong> {{ selectedTempCount }} parties</p>
          <p><strong>Template:</strong> {{ selectedTemplate?.name }}</p>
          <p><strong>Total Amount:</strong> {{ formatCurrency(selectedTotalAmount) }}</p>
        </div>
      </div>
      <template #footer>
        <Button label="Cancel" icon="pi pi-times" class="p-button-text" @click="showScheduleDialog = false" />
        <Button label="Schedule" icon="pi pi-check" @click="scheduleReminders" />
      </template>
    </Dialog>

    <!-- Template Editor Dialog -->
    <Dialog
      v-model:visible="showTemplateEditor"
      header="Message Templates"
      modal
      maximizable
      :style="{ width: '800px', height: '600px' }"
    >
      <TemplateEditor @close="showTemplateEditor = false" @saved="loadTemplates" />
    </Dialog>

    <!-- Confirmation Dialog -->
    <ConfirmDialog />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useConfirm } from 'primevue/useconfirm'
import { useToast } from 'primevue/usetoast'
import { api } from '@/services/api'
import type { 
  PartyReminderInfo, 
  ReminderConfig, 
  MessageTemplate, 
  ReminderStats,
  SchedulerStatus 
} from '@/types'
import TemplateEditor from '@/components/TemplateEditor.vue'

const confirm = useConfirm()
const toast = useToast()

// State
const loading = ref(false)
const parties = ref<PartyReminderInfo[]>([])
const config = ref<ReminderConfig>({} as ReminderConfig)
const templates = ref<MessageTemplate[]>([])
const selectedTemplateId = ref<string>('')
const stats = ref<ReminderStats | null>(null)
const schedulerStatus = ref<SchedulerStatus | null>(null)

// UI State
const showConfigPanel = ref(false)
const showTemplateEditor = ref(false)
const showScheduleDialog = ref(false)
const searchQuery = ref('')
const sortBy = ref('amount_due')
const filterBy = ref('all')
const scheduleDate = ref(new Date())
const scheduleTime = ref('10:00')

// Options
const frequencyOptions = [
  { label: 'Weekly', value: 'weekly' },
  { label: 'Bi-weekly', value: 'biweekly' },
]

const dayOptions = [
  { label: 'Sunday', value: 0 },
  { label: 'Monday', value: 1 },
  { label: 'Tuesday', value: 2 },
  { label: 'Wednesday', value: 3 },
  { label: 'Thursday', value: 4 },
  { label: 'Friday', value: 5 },
  { label: 'Saturday', value: 6 },
]

const sortOptions = [
  { label: 'Amount Due', value: 'amount_due' },
  { label: 'Name', value: 'name' },
  { label: 'Credit Days', value: 'credit_days' },
  { label: 'Code', value: 'code' },
]

const filterOptions = [
  { label: 'All', value: 'all' },
  { label: 'Enabled', value: 'enabled' },
  { label: 'Disabled', value: 'disabled' },
]

// Computed
const selectedTemplate = computed(() => {
  return templates.value.find(t => t.id === selectedTemplateId.value)
})

const filteredParties = computed(() => {
  let result = parties.value

  // Search filter
  if (searchQuery.value) {
    const query = searchQuery.value.toLowerCase()
    result = result.filter(p => 
      p.name.toLowerCase().includes(query) ||
      p.code.toLowerCase().includes(query) ||
      (p.phone && p.phone.toLowerCase().includes(query))
    )
  }

  // Status filter
  if (filterBy.value === 'enabled') {
    result = result.filter(p => p.permanent_enabled)
  } else if (filterBy.value === 'disabled') {
    result = result.filter(p => !p.permanent_enabled)
  }

  // Sort
  result = [...result].sort((a, b) => {
    let comparison = 0
    switch (sortBy.value) {
      case 'amount_due':
        comparison = a.amount_due - b.amount_due
        break
      case 'name':
        comparison = a.name.localeCompare(b.name)
        break
      case 'credit_days':
        comparison = a.sales_credit_days - b.sales_credit_days
        break
      case 'code':
        comparison = a.code.localeCompare(b.code)
        break
    }
    return comparison
  })

  return result
})

const selectedParties = computed(() => {
  return filteredParties.value.filter(p => p.temp_enabled)
})

const unselectedParties = computed(() => {
  return filteredParties.value.filter(p => !p.temp_enabled)
})

const selectedTempCount = computed(() => selectedParties.value.length)

const selectedTotalAmount = computed(() => {
  return selectedParties.value.reduce((sum, p) => sum + p.amount_due, 0)
})

const schedulerStatusText = computed(() => {
  if (!schedulerStatus.value) return 'Unknown'
  return schedulerStatus.value.is_running ? 'Running' : 'Stopped'
})

const schedulerStatusClass = computed(() => {
  if (!schedulerStatus.value) return ''
  return schedulerStatus.value.is_running ? 'text-green-500' : 'text-red-500'
})

// Methods
const loadData = async () => {
  loading.value = true
  try {
    const [partiesData, configData, templatesData, statsData, schedulerData] = await Promise.all([
      api.getEligibleParties(),
      api.getReminderConfig(),
      api.getTemplates(),
      api.getReminderStats(),
      api.getSchedulerStatus(),
    ])

    parties.value = partiesData
    config.value = configData
    templates.value = templatesData
    selectedTemplateId.value = configData.active_template_id
    stats.value = statsData
    schedulerStatus.value = schedulerData
  } catch (error) {
    toast.add({
      severity: 'error',
      summary: 'Error',
      detail: 'Failed to load data',
      life: 3000,
    })
  } finally {
    loading.value = false
  }
}

const refreshData = () => {
  loadData()
}

const loadTemplates = async () => {
  try {
    templates.value = await api.getTemplates()
  } catch (error) {
    console.error('Failed to load templates:', error)
  }
}

const onTemplateChange = async () => {
  try {
    await api.setActiveTemplate(selectedTemplateId.value)
    toast.add({
      severity: 'success',
      summary: 'Success',
      detail: 'Active template updated',
      life: 2000,
    })
  } catch (error) {
    toast.add({
      severity: 'error',
      summary: 'Error',
      detail: 'Failed to update active template',
      life: 3000,
    })
  }
}

const updateTempSelection = (party: PartyReminderInfo) => {
  // Temp selection is stored in memory only
  // No API call needed
}

const updatePermanentSelection = async (party: PartyReminderInfo) => {
  try {
    await api.updatePartyConfig(party.code, {
      enabled: party.permanent_enabled,
    })
    toast.add({
      severity: 'success',
      summary: 'Success',
      detail: `${party.name} ${party.permanent_enabled ? 'enabled' : 'disabled'} permanently`,
      life: 2000,
    })
  } catch (error) {
    toast.add({
      severity: 'error',
      summary: 'Error',
      detail: 'Failed to update party configuration',
      life: 3000,
    })
    // Revert the change
    party.permanent_enabled = !party.permanent_enabled
  }
}

const selectAll = () => {
  filteredParties.value.forEach(p => p.temp_enabled = true)
}

const deselectAll = () => {
  filteredParties.value.forEach(p => p.temp_enabled = false)
}

const generateLedger = async (partyCode: string) => {
  try {
    const blob = await api.generateLedgerPdf(partyCode)
    const url = window.URL.createObjectURL(blob)
    window.open(url, '_blank')
  } catch (error) {
    toast.add({
      severity: 'error',
      summary: 'Error',
      detail: 'Failed to generate ledger',
      life: 3000,
    })
  }
}

const confirmSend = () => {
  confirm.require({
    message: `Are you sure you want to send reminders to ${selectedTempCount.value} parties?`,
    header: 'Send Reminders',
    icon: 'pi pi-exclamation-triangle',
    accept: async () => {
      await sendReminders()
    },
  })
}

const sendReminders = async () => {
  try {
    const partyCodes = selectedParties.value.map(p => p.code)
    const result = await api.sendReminders(partyCodes, selectedTemplateId.value)
    
    toast.add({
      severity: 'success',
      summary: 'Success',
      detail: result.message,
      life: 3000,
    })
    
    // Reset selections
    parties.value.forEach(p => p.temp_enabled = false)
    
    // Refresh stats
    loadData()
  } catch (error) {
    toast.add({
      severity: 'error',
      summary: 'Error',
      detail: 'Failed to send reminders',
      life: 3000,
    })
  }
}

const scheduleReminders = async () => {
  try {
    const partyCodes = selectedParties.value.map(p => p.code)
    const scheduleDateTime = new Date(scheduleDate.value)
    const [hours, minutes] = scheduleTime.value.split(':').map(Number)
    scheduleDateTime.setHours(hours, minutes)
    
    const result = await api.scheduleReminders(partyCodes, selectedTemplateId.value, scheduleDateTime)
    
    toast.add({
      severity: 'success',
      summary: 'Success',
      detail: result.message,
      life: 3000,
    })
    
    showScheduleDialog.value = false
    parties.value.forEach(p => p.temp_enabled = false)
  } catch (error) {
    toast.add({
      severity: 'error',
      summary: 'Error',
      detail: 'Failed to schedule reminders',
      life: 3000,
    })
  }
}

const exportCsv = () => {
  // TODO: Implement CSV export
  toast.add({
    severity: 'info',
    summary: 'Info',
    detail: 'CSV export not yet implemented',
    life: 3000,
  })
}

const saveSchedule = async () => {
  try {
    await api.updateScheduleConfig(config.value.schedule)
    toast.add({
      severity: 'success',
      summary: 'Success',
      detail: 'Schedule configuration saved',
      life: 2000,
    })
  } catch (error) {
    toast.add({
      severity: 'error',
      summary: 'Error',
      detail: 'Failed to save schedule configuration',
      life: 3000,
    })
  }
}

const startScheduler = async () => {
  try {
    await api.startScheduler()
    toast.add({
      severity: 'success',
      summary: 'Success',
      detail: 'Scheduler started',
      life: 2000,
    })
    schedulerStatus.value = await api.getSchedulerStatus()
  } catch (error) {
    toast.add({
      severity: 'error',
      summary: 'Error',
      detail: 'Failed to start scheduler',
      life: 3000,
    })
  }
}

const stopScheduler = async () => {
  try {
    await api.stopScheduler()
    toast.add({
      severity: 'success',
      summary: 'Success',
      detail: 'Scheduler stopped',
      life: 2000,
    })
    schedulerStatus.value = await api.getSchedulerStatus()
  } catch (error) {
    toast.add({
      severity: 'error',
      summary: 'Error',
      detail: 'Failed to stop scheduler',
      life: 3000,
    })
  }
}

const triggerManualRun = async () => {
  try {
    const result = await api.triggerManualRun()
    toast.add({
      severity: 'success',
      summary: 'Success',
      detail: result.message,
      life: 3000,
    })
  } catch (error) {
    toast.add({
      severity: 'error',
      summary: 'Error',
      detail: 'Failed to trigger manual run',
      life: 3000,
    })
  }
}

const formatCurrency = (amount: number): string => {
  return new Intl.NumberFormat('en-IN', {
    style: 'currency',
    currency: 'INR',
    minimumFractionDigits: 2,
  }).format(amount)
}

onMounted(() => {
  loadData()
})
</script>

<style scoped>
.reminders-page {
  padding: 1.5rem;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 1.5rem;
}

.header-content h1 {
  margin: 0 0 0.5rem 0;
}

.subtitle {
  color: var(--text-color-secondary);
  margin: 0;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 1rem;
  margin-bottom: 1.5rem;
}

.stat-card {
  text-align: center;
}

.stat-value {
  font-size: 1.75rem;
  font-weight: 600;
  color: var(--primary-color);
}

.stat-label {
  font-size: 0.875rem;
  color: var(--text-color-secondary);
  margin-top: 0.25rem;
}

.config-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 2rem;
}

.config-section h4 {
  margin-top: 0;
  margin-bottom: 1rem;
}

.config-section .field {
  margin-bottom: 1rem;
}

.config-section label {
  display: block;
  margin-bottom: 0.5rem;
  font-weight: 500;
}

.button-group {
  display: flex;
  gap: 0.5rem;
  flex-wrap: wrap;
}

.template-preview label {
  font-weight: 500;
  margin-bottom: 0.5rem;
  display: block;
}

.preview-box {
  background: var(--surface-ground);
  padding: 1rem;
  border-radius: 6px;
  font-family: monospace;
  font-size: 0.875rem;
  white-space: pre-wrap;
  max-height: 200px;
  overflow-y: auto;
}

.preview-box pre {
  margin: 0;
}

.party-selection {
  margin-bottom: 1.5rem;
}

.selection-actions {
  display: flex;
  align-items: center;
  padding: 0.5rem 0;
}

.party-group {
  border: 1px solid var(--surface-border);
  border-radius: 6px;
  padding: 1rem;
}

.group-title {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin: 0 0 1rem 0;
  font-size: 1rem;
  font-weight: 600;
}

.party-name {
  display: flex;
  flex-direction: column;
}

.amount-due {
  font-weight: 600;
  color: var(--primary-color);
}

.credit-days {
  color: var(--text-color-secondary);
  font-size: 0.875rem;
}

.action-bar {
  display: flex;
  justify-content: flex-end;
  padding: 1rem 0;
  gap: 0.5rem;
}

.schedule-form .field {
  margin-bottom: 1rem;
}

.schedule-form label {
  display: block;
  margin-bottom: 0.5rem;
  font-weight: 500;
}

.summary {
  background: var(--surface-ground);
  padding: 1rem;
  border-radius: 6px;
  margin-top: 1rem;
}

.summary p {
  margin: 0.25rem 0;
}

.text-muted {
  color: var(--text-color-secondary);
}

@media (max-width: 768px) {
  .config-grid {
    grid-template-columns: 1fr;
  }
  
  .stats-grid {
    grid-template-columns: 1fr 1fr;
  }
  
  .action-bar {
    flex-direction: column;
  }
  
  .action-bar button {
    width: 100%;
    margin-left: 0 !important;
    margin-bottom: 0.5rem;
  }
}
</style>

<template>
  <div class="template-manager">
    <div class="manager-header">
      <Button
        label="Create New Template"
        icon="pi pi-plus"
        class="p-button-success"
        @click="createNewTemplate"
      />
    </div>

    <DataTable
      :value="templates"
      class="p-datatable-sm"
      stripedRows
    >
      <Column field="name" header="Template Name" sortable>
        <template #body="{ data }">
          <div class="template-name-cell">
            <span class="name">{{ data.name }}</span>
            <Tag v-if="data.is_default" value="Default" severity="success" class="ml-2" />
          </div>
        </template>
      </Column>

      <Column field="description" header="Description">
        <template #body="{ data }">
          <span class="description-text">{{ data.description || 'No description' }}</span>
        </template>
      </Column>

      <Column field="variables" header="Variables">
        <template #body="{ data }">
          <div class="variables-list">
            <Tag 
              v-for="variable in data.variables.slice(0, 3)" 
              :key="variable"
              :value="variable"
              class="mr-1 mb-1"
              severity="info"
            />
            <span v-if="data.variables.length > 3" class="more-vars">+{{ data.variables.length - 3 }} more</span>
          </div>
        </template>
      </Column>

      <Column style="width: 200px">
        <template #body="{ data }">
          <div class="action-buttons">
            <Button
              icon="pi pi-pencil"
              class="p-button-text p-button-sm"
              @click="editTemplate(data)"
              tooltip="Edit"
            />
            <Button
              v-if="!data.is_default"
              icon="pi pi-star"
              class="p-button-text p-button-sm"
              @click="setAsDefault(data.id)"
              tooltip="Set as Default"
            />
            <Button
              v-if="!data.is_default"
              icon="pi pi-trash"
              class="p-button-text p-button-danger p-button-sm"
              @click="confirmDelete(data)"
              tooltip="Delete"
            />
          </div>
        </template>
      </Column>
    </DataTable>

    <!-- Template Editor Dialog -->
    <Dialog
      v-model:visible="showEditor"
      :header="editingTemplate ? 'Edit Template' : 'Create Template'"
      modal
      :style="{ width: '700px' }"
      :closable="!saving"
    >
      <div class="template-form">
        <div class="field">
          <label>Template Name *</label>
          <InputText
            v-model="form.name"
            placeholder="e.g., Standard Reminder"
            class="w-full"
            :class="{ 'p-invalid': errors.name }"
          />
          <small class="p-error" v-if="errors.name">{{ errors.name }}</small>
        </div>

        <div class="field">
          <label>Description</label>
          <InputText
            v-model="form.description"
            placeholder="Brief description of when to use this template"
            class="w-full"
          />
        </div>

        <div class="field">
          <label>Template Content *</label>
          <Textarea
            v-model="form.content"
            rows="8"
            class="w-full font-monospace"
            :class="{ 'p-invalid': errors.content }"
            placeholder="Enter your message template here... Use {variable_name} for dynamic content."
          />
          <small class="p-error" v-if="errors.content">{{ errors.content }}</small>
        </div>

        <div class="field">
          <label>Available Variables</label>
          <div class="variables-help">
            <p>Click to insert into template:</p>
            <div class="variables-grid">
              <Button
                v-for="variable in availableVariables"
                :key="variable"
                :label="variable"
                class="p-button-sm p-button-outlined"
                @click="insertVariable(variable)"
              />
            </div>
          </div>
        </div>

        <div class="field preview-field">
          <label>Preview</label>
          <div class="preview-box">
            <pre>{{ previewContent }}</pre>
          </div>
        </div>
      </div>

      <template #footer>
        <Button
          label="Cancel"
          icon="pi pi-times"
          class="p-button-text"
          @click="closeEditor"
          :disabled="saving"
        />
        <Button
          label="Save"
          icon="pi pi-check"
          class="p-button-primary"
          @click="saveTemplate"
          :loading="saving"
        />
      </template>
    </Dialog>

    <!-- Delete Confirmation -->
    <ConfirmDialog />
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import Button from 'primevue/button'
import Column from 'primevue/column'
import ConfirmDialog from 'primevue/confirmdialog'
import DataTable from 'primevue/datatable'
import Dialog from 'primevue/dialog'
import InputText from 'primevue/inputtext'
import Tag from 'primevue/tag'
import Textarea from 'primevue/textarea'
import { useConfirm } from 'primevue/useconfirm'
import { useToast } from 'primevue/usetoast'
import { api } from '@/services/api'
import type { MessageTemplate } from '@/types'

const confirm = useConfirm()
const toast = useToast()

const emit = defineEmits(['close', 'template-saved'])

// State
const templates = ref<MessageTemplate[]>([])
const loading = ref(false)
const saving = ref(false)
const showEditor = ref(false)
const editingTemplate = ref<MessageTemplate | null>(null)

const form = ref({
  name: '',
  description: '',
  content: '',
  variables: [] as string[]
})

const errors = ref({
  name: '',
  content: ''
})

const availableVariables = [
  'customer_name',
  'company_name',
  'amount_due',
  'currency_symbol',
  'credit_days',
  'contact_phone',
  'party_code',
  'phone'
]

// Computed
const previewContent = computed(() => {
  let content = form.value.content
  // Replace variables with sample values
  const sampleData: Record<string, string> = {
    customer_name: 'ABC Trading Co.',
    company_name: 'Your Company Name',
    amount_due: '₹50,000.00',
    currency_symbol: '₹',
    credit_days: '30',
    contact_phone: '+91 98765 43210',
    party_code: 'CUST001',
    phone: '+91 98765 43210'
  }
  
  availableVariables.forEach(variable => {
    content = content.replace(
      new RegExp(`{${variable}}`, 'g'),
      sampleData[variable] || `{${variable}}`
    )
  })
  
  return content
})

// Methods
async function loadTemplates() {
  loading.value = true
  try {
    templates.value = await api.getTemplates()
  } catch {
    toast.add({
      severity: 'error',
      summary: 'Error',
      detail: 'Failed to load templates',
      life: 3000
    })
  } finally {
    loading.value = false
  }
}

function createNewTemplate() {
  editingTemplate.value = null
  form.value = {
    name: '',
    description: '',
    content: 'Dear {customer_name},\n\nThis is a friendly reminder that an amount of {currency_symbol}{amount_due} is due for payment.\n\nPlease find attached your ledger statement for review.\n\nIf you have any questions, please contact us at {contact_phone}.\n\nBest regards,\n{company_name}',
    variables: availableVariables
  }
  errors.value = { name: '', content: '' }
  showEditor.value = true
}

function editTemplate(template: MessageTemplate) {
  editingTemplate.value = template
  form.value = {
    name: template.name,
    description: template.description || '',
    content: template.content,
    variables: template.variables
  }
  errors.value = { name: '', content: '' }
  showEditor.value = true
}

function insertVariable(variable: string) {
  const textarea = document.querySelector('textarea')
  if (!textarea) return
  
  const start = textarea.selectionStart
  const end = textarea.selectionEnd
  const text = form.value.content
  
  form.value.content = text.substring(0, start) + `{${variable}}` + text.substring(end)
  
  // Restore focus
  setTimeout(() => {
    textarea.focus()
    textarea.setSelectionRange(start + variable.length + 2, start + variable.length + 2)
  }, 0)
}

function validateForm(): boolean {
  errors.value = { name: '', content: '' }
  let valid = true
  
  if (!form.value.name.trim()) {
    errors.value.name = 'Template name is required'
    valid = false
  }
  
  if (!form.value.content.trim()) {
    errors.value.content = 'Template content is required'
    valid = false
  }
  
  return valid
}

async function saveTemplate() {
  if (!validateForm()) return
  
  saving.value = true
  try {
    if (editingTemplate.value) {
      await api.updateTemplate(editingTemplate.value.id, form.value)
    } else {
      await api.createTemplate(form.value)
    }
    
    toast.add({
      severity: 'success',
      summary: 'Success',
      detail: `Template ${editingTemplate.value ? 'updated' : 'created'} successfully`,
      life: 3000
    })
    
    showEditor.value = false
    await loadTemplates()
    emit('template-saved')
  } catch {
    toast.add({
      severity: 'error',
      summary: 'Error',
      detail: 'Failed to save template',
      life: 3000
    })
  } finally {
    saving.value = false
  }
}

async function setAsDefault(templateId: string) {
  try {
    await api.setDefaultTemplate(templateId)
    toast.add({
      severity: 'success',
      summary: 'Success',
      detail: 'Default template updated',
      life: 2000
    })
    await loadTemplates()
    emit('template-saved')
  } catch {
    toast.add({
      severity: 'error',
      summary: 'Error',
      detail: 'Failed to set default template',
      life: 3000
    })
  }
}

function confirmDelete(template: MessageTemplate) {
  confirm.require({
    message: `Are you sure you want to delete "${template.name}"?`,
    header: 'Delete Template',
    icon: 'pi pi-exclamation-triangle',
    acceptClass: 'p-button-danger',
    accept: () => deleteTemplate(template.id),
    reject: () => {}
  })
}

async function deleteTemplate(templateId: string) {
  try {
    await api.deleteTemplate(templateId)
    toast.add({
      severity: 'success',
      summary: 'Success',
      detail: 'Template deleted',
      life: 2000
    })
    await loadTemplates()
    emit('template-saved')
  } catch {
    toast.add({
      severity: 'error',
      summary: 'Error',
      detail: 'Failed to delete template',
      life: 3000
    })
  }
}

function closeEditor() {
  showEditor.value = false
}

// Lifecycle
onMounted(() => {
  loadTemplates()
})
</script>

<style scoped>
.template-manager {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.manager-header {
  display: flex;
  justify-content: flex-end;
}

.template-name-cell {
  display: flex;
  align-items: center;
}

.description-text {
  color: var(--text-color-secondary);
  font-size: 0.875rem;
}

.variables-list {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
}

.more-vars {
  font-size: 0.75rem;
  color: var(--text-color-secondary);
}

.action-buttons {
  display: flex;
  gap: 0.25rem;
  justify-content: flex-end;
}

.template-form {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.field {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.field label {
  font-weight: 500;
}

.variables-help {
  background: var(--surface-100);
  padding: 1rem;
  border-radius: 6px;
}

.variables-help p {
  margin: 0 0 0.5rem 0;
  font-size: 0.875rem;
  color: var(--text-color-secondary);
}

.variables-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
}

.preview-field {
  margin-top: 0.5rem;
}

.preview-box {
  background: var(--surface-100);
  padding: 1rem;
  border-radius: 6px;
  border: 1px solid var(--surface-300);
}

.preview-box pre {
  margin: 0;
  white-space: pre-wrap;
  word-wrap: break-word;
  font-size: 0.875rem;
}

.font-monospace {
  font-family: 'Courier New', monospace;
}
</style>

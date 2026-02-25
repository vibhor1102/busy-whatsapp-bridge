<template>
  <div class="template-editor">
    <div class="editor-layout">
      <!-- Template List -->
      <div class="template-list">
        <div class="list-header">
          <h4>Templates</h4>
          <Button
            icon="pi pi-plus"
            class="p-button-sm"
            @click="createNewTemplate"
            :disabled="templates.length >= 6"
          />
        </div>
        
        <div class="template-items">
          <div
            v-for="template in templates"
            :key="template.id"
            class="template-item"
            :class="{ active: selectedTemplate?.id === template.id, default: template.is_default }"
            @click="selectTemplate(template)"
          >
            <div class="template-info">
              <span class="template-name">
                {{ template.name }}
                <i v-if="template.is_default" class="pi pi-star-fill text-yellow-500 ml-2" />
              </span>
              <span class="template-desc">{{ template.description }}</span>
            </div>
            <Button
              v-if="!template.is_default"
              icon="pi pi-trash"
              class="p-button-text p-button-danger p-button-sm"
              @click.stop="confirmDelete(template)"
            />
          </div>
        </div>
      </div>

      <!-- Template Editor Form -->
      <div v-if="selectedTemplate" class="template-form">
        <div class="form-header">
          <h4>{{ isNew ? 'New Template' : 'Edit Template' }}</h4>
          <div class="form-actions">
            <Button
              v-if="!selectedTemplate.is_default"
              label="Set as Default"
              icon="pi pi-star"
              class="p-button-outlined p-button-sm"
              @click="setAsDefault"
            />
            <Button
              label="Preview"
              icon="pi pi-eye"
              class="p-button-outlined p-button-sm ml-2"
              @click="showPreview = true"
            />
          </div>
        </div>

        <div class="form-fields">
          <div class="field">
            <label>Template ID</label>
            <InputText
              v-model="selectedTemplate.id"
              :disabled="!isNew"
              placeholder="unique-template-id"
            />
          </div>

          <div class="field">
            <label>Name</label>
            <InputText v-model="selectedTemplate.name" placeholder="Template display name" />
          </div>

          <div class="field">
            <label>Description</label>
            <InputText v-model="selectedTemplate.description" placeholder="Brief description" />
          </div>

          <div class="field">
            <label>Message Content</label>
            <Textarea
              v-model="selectedTemplate.content"
              rows="10"
              autoResize
              placeholder="Enter message template..."
            />
          </div>

          <div class="variables-section">
            <h5>Available Variables</h5>
            <div class="variables-list">
              <Tag
                v-for="variable in availableVariables"
                :key="variable"
                :value="`{${variable}}`"
                class="mr-2 mb-2 cursor-pointer"
                @click="insertVariable(variable)"
              />
            </div>
          </div>
        </div>

        <div class="form-footer">
          <Button
            label="Cancel"
            icon="pi pi-times"
            class="p-button-text"
            @click="$emit('close')"
          />
          
          <Button
            label="Save"
            icon="pi pi-check"
            class="p-button-primary"
            @click="saveTemplate"
            :loading="saving"
          />
        </div>
      </div>

      <!-- Empty State -->
      <div v-else class="empty-state">
        <i class="pi pi-file-edit text-4xl text-secondary mb-3"></i>
        <p>Select a template to edit or create a new one</p>
      </div>
    </div>

    <!-- Preview Dialog -->
    <Dialog
      v-model:visible="showPreview"
      header="Template Preview"
      modal
      :style="{ width: '500px' }"
    >
      <div v-if="selectedTemplate" class="preview-content">
        <div class="preview-header">
          <strong>{{ selectedTemplate.name }}</strong>
        </div>
        <div class="preview-message">
          <pre>{{ previewText }}</pre>
        </div>
        <div class="preview-variables">
          <small>Variables used: {{ selectedTemplate.variables?.join(', ') || 'customer_name, company_name, amount_due' }}</small>
        </div>
      </div>
      <template #footer>
        <Button label="Close" @click="showPreview = false" />
      </template>
    </Dialog>

    <ConfirmDialog />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import Button from 'primevue/button'
import ConfirmDialog from 'primevue/confirmdialog'
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

const emit = defineEmits(['close', 'saved'])

// State
const templates = ref<MessageTemplate[]>([])
const selectedTemplate = ref<MessageTemplate | null>(null)
const isNew = ref(false)
const saving = ref(false)
const showPreview = ref(false)

const availableVariables = [
  'customer_name',
  'company_name',
  'amount_due',
  'credit_days',
  'party_code',
  'phone',
]

// Computed
const previewText = computed(() => {
  if (!selectedTemplate.value) return ''
  
  let text = selectedTemplate.value.content
  const sampleValues: Record<string, string> = {
    customer_name: 'ABC Textiles',
    company_name: 'Your Company Name',
    amount_due: '₹50,000.00',
    credit_days: '30',
    party_code: '1234',
    phone: '+91 98765 43210',
  }
  
  Object.entries(sampleValues).forEach(([key, value]) => {
    text = text.replace(new RegExp(`{${key}}`, 'g'), value)
  })
  
  return text
})

// Methods
const loadTemplates = async () => {
  try {
    templates.value = await api.getTemplates()
  } catch (error) {
    toast.add({
      severity: 'error',
      summary: 'Error',
      detail: 'Failed to load templates',
      life: 3000,
    })
  }
}

const selectTemplate = (template: MessageTemplate) => {
  selectedTemplate.value = { ...template }
  isNew.value = false
}

const createNewTemplate = () => {
  if (templates.value.length >= 6) {
    toast.add({
      severity: 'warn',
      summary: 'Warning',
      detail: 'Maximum 6 templates allowed',
      life: 3000,
    })
    return
  }
  
  selectedTemplate.value = {
    id: '',
    name: 'New Template',
    description: '',
    content: 'Payment Reminder from {company_name}:\n\nDear {customer_name}, your outstanding balance is ₹{amount_due}.\n\nPlease find your ledger statement attached for reference.\n\nFor any queries regarding this statement, please call or message us at 7206366664.\n\nThank you for your business.',
    variables: availableVariables,
    is_default: false,
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  }
  isNew.value = true
}

const insertVariable = (variable: string) => {
  if (!selectedTemplate.value) return
  
  const textarea = document.querySelector('textarea') as HTMLTextAreaElement
  if (textarea) {
    const start = textarea.selectionStart
    const end = textarea.selectionEnd
    const text = selectedTemplate.value.content
    const before = text.substring(0, start)
    const after = text.substring(end)
    
    selectedTemplate.value.content = before + `{${variable}}` + after
    
    // Restore cursor position
    setTimeout(() => {
      textarea.selectionStart = textarea.selectionEnd = start + variable.length + 2
      textarea.focus()
    }, 0)
  } else {
    selectedTemplate.value.content += `{${variable}}`
  }
}

const saveTemplate = async () => {
  if (!selectedTemplate.value) return
  
  // Validation
  if (!selectedTemplate.value.id.trim()) {
    toast.add({
      severity: 'error',
      summary: 'Error',
      detail: 'Template ID is required',
      life: 3000,
    })
    return
  }
  
  if (!selectedTemplate.value.name.trim()) {
    toast.add({
      severity: 'error',
      summary: 'Error',
      detail: 'Template name is required',
      life: 3000,
    })
    return
  }
  
  saving.value = true
  
  try {
    if (isNew.value) {
      await api.createTemplate(selectedTemplate.value)
      toast.add({
        severity: 'success',
        summary: 'Success',
        detail: 'Template created',
        life: 2000,
      })
    } else {
      await api.updateTemplate(selectedTemplate.value.id, selectedTemplate.value)
      toast.add({
        severity: 'success',
        summary: 'Success',
        detail: 'Template updated',
        life: 2000,
      })
    }
    
    await loadTemplates()
    emit('saved')
    
    // Select the saved template
    const saved = templates.value.find(t => t.id === selectedTemplate.value?.id)
    if (saved) {
      selectTemplate(saved)
      isNew.value = false
    }
  } catch (error) {
    toast.add({
      severity: 'error',
      summary: 'Error',
      detail: isNew.value ? 'Failed to create template' : 'Failed to update template',
      life: 3000,
    })
  } finally {
    saving.value = false
  }
}

const confirmDelete = (template: MessageTemplate) => {
  if (template.is_default) {
    toast.add({
      severity: 'error',
      summary: 'Error',
      detail: 'Cannot delete the default template',
      life: 3000,
    })
    return
  }
  
  confirm.require({
    message: `Are you sure you want to delete "${template.name}"?`,
    header: 'Delete Template',
    icon: 'pi pi-exclamation-triangle',
    acceptClass: 'p-button-danger',
    accept: () => deleteTemplate(template),
  })
}

const deleteTemplate = async (template: MessageTemplate) => {
  try {
    await api.deleteTemplate(template.id)
    toast.add({
      severity: 'success',
      summary: 'Success',
      detail: 'Template deleted',
      life: 2000,
    })
    
    if (selectedTemplate.value?.id === template.id) {
      selectedTemplate.value = null
    }
    
    await loadTemplates()
    emit('saved')
  } catch (error) {
    toast.add({
      severity: 'error',
      summary: 'Error',
      detail: 'Failed to delete template',
      life: 3000,
    })
  }
}

const setAsDefault = async () => {
  if (!selectedTemplate.value) return
  
  try {
    await api.updateTemplate(selectedTemplate.value.id, {
      ...selectedTemplate.value,
      is_default: true,
    })
    
    // Update other templates to not be default
    templates.value.forEach(t => {
      if (t.id !== selectedTemplate.value?.id) {
        t.is_default = false
      }
    })
    
    selectedTemplate.value.is_default = true
    
    toast.add({
      severity: 'success',
      summary: 'Success',
      detail: 'Default template updated',
      life: 2000,
    })
    
    await loadTemplates()
    emit('saved')
  } catch (error) {
    toast.add({
      severity: 'error',
      summary: 'Error',
      detail: 'Failed to set default template',
      life: 3000,
    })
  }
}

onMounted(() => {
  loadTemplates()
})
</script>

<style scoped>
.template-editor {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.editor-layout {
  display: grid;
  grid-template-columns: 300px 1fr;
  gap: 1rem;
  height: 100%;
  overflow: hidden;
}

.template-list {
  border-right: 1px solid var(--surface-border);
  display: flex;
  flex-direction: column;
}

.list-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1rem;
  border-bottom: 1px solid var(--surface-border);
}

.list-header h4 {
  margin: 0;
}

.template-items {
  overflow-y: auto;
  flex: 1;
}

.template-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.75rem 1rem;
  border-bottom: 1px solid var(--surface-border);
  cursor: pointer;
  transition: background-color 0.2s;
}

.template-item:hover {
  background-color: var(--surface-hover);
}

.template-item.active {
  background-color: var(--primary-color);
  color: var(--primary-color-text);
}

.template-item.default {
  border-left: 3px solid var(--yellow-500);
}

.template-info {
  display: flex;
  flex-direction: column;
  flex: 1;
  min-width: 0;
}

.template-name {
  font-weight: 500;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.template-desc {
  font-size: 0.75rem;
  opacity: 0.7;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.template-form {
  display: flex;
  flex-direction: column;
  padding: 1rem;
  overflow-y: auto;
}

.form-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1rem;
}

.form-header h4 {
  margin: 0;
}

.form-actions {
  display: flex;
  gap: 0.5rem;
}

.form-fields {
  flex: 1;
}

.form-fields .field {
  margin-bottom: 1rem;
}

.form-fields label {
  display: block;
  margin-bottom: 0.5rem;
  font-weight: 500;
}

.variables-section {
  margin-top: 1rem;
}

.variables-section h5 {
  margin: 0 0 0.5rem 0;
}

.variables-list {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
}

.form-footer {
  display: flex;
  justify-content: flex-end;
  gap: 0.5rem;
  margin-top: 1rem;
  padding-top: 1rem;
  border-top: 1px solid var(--surface-border);
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: var(--text-color-secondary);
  padding: 2rem;
}

.preview-content {
  display: flex;
  flex-direction: column;
}

.preview-header {
  padding: 0.5rem 0;
  border-bottom: 1px solid var(--surface-border);
  margin-bottom: 1rem;
}

.preview-message {
  background: var(--surface-ground);
  padding: 1rem;
  border-radius: 6px;
  margin-bottom: 1rem;
}

.preview-message pre {
  margin: 0;
  white-space: pre-wrap;
  font-family: inherit;
}

.preview-variables {
  color: var(--text-color-secondary);
}

@media (max-width: 768px) {
  .editor-layout {
    grid-template-columns: 1fr;
  }
  
  .template-list {
    border-right: none;
    border-bottom: 1px solid var(--surface-border);
    max-height: 200px;
  }
}
</style>

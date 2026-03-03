import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
    X,
    Plus,
    Trash2,
    Save,
    CheckCircle,
    AlignLeft,
    Settings2,
    FileText
} from 'lucide-react';
import { api } from '../../services/api';
import { toast } from 'sonner';
import { LoadingState } from '../ui/LoadingState';
import type { MessageTemplate } from '../../types';

const TEMPLATE_VARIABLES = [
    { key: '{customer_name}', label: 'Customer Name', desc: 'Party Name' },
    { key: '{amount_due}', label: 'Amount Due', desc: 'e.g. 5,000.00' },
    { key: '{currency_symbol}', label: 'Currency', desc: 'e.g. ₹' },
    { key: '{company_name}', label: 'Company', desc: 'Your Company' },
    { key: '{credit_days}', label: 'Credit Days', desc: 'e.g. 30' },
    { key: '{contact_phone}', label: 'Company Phone', desc: 'Support No' },
    { key: '{party_code}', label: 'Party Code', desc: 'Busy Code' },
    { key: '{phone}', label: 'Customer Phone', desc: 'Receiver No' }
];

interface TemplateEditorProps {
    isOpen: boolean;
    onClose: () => void;
    activeCompanyId: string;
}

export function TemplateEditor({ isOpen, onClose, activeCompanyId }: TemplateEditorProps) {
    const queryClient = useQueryClient();
    const [editingTemplate, setEditingTemplate] = useState<Partial<MessageTemplate> | null>(null);

    // Queries
    const { data: templates, isLoading } = useQuery({
        queryKey: ['reminder-templates', activeCompanyId],
        queryFn: () => api.getTemplates(),
        enabled: isOpen,
    });

    // Mutations
    const createMutation = useMutation({
        mutationFn: (template: Partial<MessageTemplate>) => api.createTemplate(template),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['reminder-templates', activeCompanyId] });
            toast.success('Template created');
            setEditingTemplate(null);
        },
        onError: (err: any) => toast.error(`Create failed: ${err.message}`)
    });

    const updateMutation = useMutation({
        mutationFn: ({ id, template }: { id: string, template: Partial<MessageTemplate> }) =>
            api.updateTemplate(id, template),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['reminder-templates', activeCompanyId] });
            toast.success('Template updated');
            setEditingTemplate(null);
        },
        onError: (err: any) => toast.error(`Update failed: ${err.message}`)
    });

    const deleteMutation = useMutation({
        mutationFn: (id: string) => api.deleteTemplate(id),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['reminder-templates', activeCompanyId] });
            toast.success('Template deleted');
        },
        onError: (err: any) => toast.error(`Delete failed: ${err.message}`)
    });

    const setDefaultMutation = useMutation({
        mutationFn: (id: string) => api.setDefaultTemplate(id),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['reminder-templates', activeCompanyId] });
            queryClient.invalidateQueries({ queryKey: ['reminder-config'] });
            toast.success('Default template updated');
        },
        onError: (err: any) => toast.error(`Failed to set default: ${err.message}`)
    });

    const handleSave = () => {
        if (!editingTemplate?.name?.trim() || !editingTemplate?.content?.trim()) {
            toast.error('Name and Content are required');
            return;
        }

        if (editingTemplate.id && !editingTemplate.id.startsWith('new_')) {
            updateMutation.mutate({ id: editingTemplate.id, template: editingTemplate });
        } else {
            createMutation.mutate({
                name: editingTemplate.name,
                content: editingTemplate.content
            });
        }
    };

    const handleCreateNew = () => {
        setEditingTemplate({
            id: `new_${Date.now()}`,
            name: 'New Template',
            content: 'Dear {customer_name},\n\nYour outstanding balance is {currency_symbol}{amount_due}.'
        });
    };

    const insertVariable = (variable: string) => {
        if (!editingTemplate) return;

        // Simple append to end of content for now, a full textarea caret insertion is complex in React
        // but good enough for UX improvements
        const currentContent = editingTemplate.content || '';
        setEditingTemplate({
            ...editingTemplate,
            content: currentContent + (currentContent.endsWith(' ') ? '' : ' ') + variable
        });
    };

    if (!isOpen) return null;

    return (
        <AnimatePresence>
            <div className="fixed inset-0 z-50 flex items-center justify-center p-4 sm:p-6">
                <motion.div
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    exit={{ opacity: 0 }}
                    className="absolute inset-0 bg-black/60 backdrop-blur-sm"
                    onClick={() => !editingTemplate && onClose()}
                />

                <motion.div
                    initial={{ opacity: 0, scale: 0.95, y: 10 }}
                    animate={{ opacity: 1, scale: 1, y: 0 }}
                    exit={{ opacity: 0, scale: 0.95, y: 10 }}
                    className="relative w-full max-w-4xl max-h-[90vh] flex flex-col rounded-2xl shadow-2xl overflow-hidden"
                    style={{ background: 'var(--bg-card)', border: '1px solid var(--border-default)' }}
                >
                    {/* Header */}
                    <div className="flex items-center justify-between p-4 sm:p-5 border-b shrink-0" style={{ borderColor: 'var(--border-default)' }}>
                        <div className="flex items-center gap-3">
                            <div className="p-2 rounded-lg" style={{ background: 'var(--brand-soft)', color: 'var(--brand-accent)' }}>
                                <FileText className="w-5 h-5" />
                            </div>
                            <div>
                                <h2 className="text-lg font-bold" style={{ color: 'var(--text-primary)' }}>Message Templates</h2>
                                <p className="text-xs" style={{ color: 'var(--text-tertiary)' }}>Manage reminder formats for this company</p>
                            </div>
                        </div>

                        <button
                            onClick={onClose}
                            disabled={!!editingTemplate}
                            className="p-2 rounded-lg transition-colors hover:bg-black/5 dark:hover:bg-white/5 disabled:opacity-50"
                        >
                            <X className="w-5 h-5" style={{ color: 'var(--text-secondary)' }} />
                        </button>
                    </div>

                    <div className="flex-1 overflow-hidden flex flex-col md:flex-row">
                        {/* Sidebar - Template List */}
                        <div className={`w-full md:w-1/3 flex flex-col border-r shrink-0 transition-transform ${editingTemplate ? 'hidden md:flex opacity-50 pointer-events-none' : ''}`} style={{ borderColor: 'var(--border-default)' }}>
                            <div className="p-4 border-b flex justify-between items-center" style={{ borderColor: 'var(--border-default)' }}>
                                <span className="text-sm font-semibold" style={{ color: 'var(--text-secondary)' }}>Saved Templates</span>
                                <button
                                    onClick={handleCreateNew}
                                    className="p-1.5 rounded-md bg-black/5 hover:bg-black/10 dark:bg-white/5 dark:hover:bg-white/10 transition-colors"
                                    title="Create New Template"
                                >
                                    <Plus className="w-4 h-4" />
                                </button>
                            </div>

                            <div className="flex-1 overflow-y-auto p-2 space-y-1">
                                {isLoading ? (
                                    <div className="py-8"><LoadingState size="sm" /></div>
                                ) : templates?.length === 0 ? (
                                    <div className="text-center py-8 px-4 text-sm" style={{ color: 'var(--text-tertiary)' }}>
                                        No templates found.<br />Create one to get started.
                                    </div>
                                ) : (
                                    templates?.map((t: MessageTemplate) => (
                                        <div
                                            key={t.id}
                                            className="group flex flex-col p-3 rounded-lg cursor-pointer transition-colors hover:bg-black/5 dark:hover:bg-white/5"
                                            onClick={() => setEditingTemplate(t)}
                                        >
                                            <div className="flex items-center justify-between mb-1">
                                                <span className="font-medium text-sm truncate pr-2" style={{ color: 'var(--text-primary)' }}>{t.name}</span>
                                                {t.is_default && (
                                                    <span className="text-[10px] px-1.5 py-0.5 rounded-full font-bold tracking-wider" style={{ background: 'var(--brand-soft)', color: 'var(--brand-accent)' }}>
                                                        DEFAULT
                                                    </span>
                                                )}
                                            </div>
                                            <p className="text-xs line-clamp-2" style={{ color: 'var(--text-tertiary)' }}>{t.content}</p>
                                        </div>
                                    ))
                                )}
                            </div>
                        </div>

                        {/* Main Editor Area */}
                        <div className={`flex-1 flex flex-col h-full bg-black/[0.02] dark:bg-white/[0.02] ${!editingTemplate ? 'hidden md:flex items-center justify-center' : ''}`}>
                            {!editingTemplate ? (
                                <div className="text-center p-6 lg:p-12">
                                    <Settings2 className="w-12 h-12 mx-auto mb-4 opacity-20" style={{ color: 'var(--text-primary)' }} />
                                    <h3 className="text-lg font-medium mb-2" style={{ color: 'var(--text-primary)' }}>Select a Template</h3>
                                    <p className="text-sm max-w-sm mx-auto mb-6" style={{ color: 'var(--text-tertiary)' }}>
                                        Choose a template from the sidebar to edit, or create a new one to customize your payment reminder messages.
                                    </p>
                                    <button onClick={handleCreateNew} className="btn-primary mx-auto">
                                        <Plus className="w-4 h-4 mr-2" />
                                        Create Template
                                    </button>
                                </div>
                            ) : (
                                <div className="flex-1 overflow-y-auto p-4 sm:p-6">
                                    <div className="space-y-5 max-w-2xl mx-auto">
                                        {/* Toolbar */}
                                        <div className="flex items-center justify-between pb-4 border-b" style={{ borderColor: 'var(--border-default)' }}>
                                            <h3 className="text-base font-semibold" style={{ color: 'var(--text-primary)' }}>
                                                {editingTemplate.id?.startsWith('new_') ? 'Drafting New Template' : 'Edit Template'}
                                            </h3>
                                            <div className="flex gap-2">
                                                {editingTemplate.id && !editingTemplate.id.startsWith('new_') && !editingTemplate.is_default && (
                                                    <button
                                                        onClick={() => setDefaultMutation.mutate(editingTemplate.id!)}
                                                        disabled={setDefaultMutation.isPending}
                                                        className="btn-secondary text-xs py-1.5"
                                                        title="Set as Default Template"
                                                    >
                                                        <CheckCircle className="w-3.5 h-3.5" />
                                                        <span className="hidden sm:inline">Set Default</span>
                                                    </button>
                                                )}
                                                {editingTemplate.id && !editingTemplate.id.startsWith('new_') && !editingTemplate.is_default && (
                                                    <button
                                                        onClick={() => {
                                                            if (confirm('Are you sure you want to delete this template?')) {
                                                                deleteMutation.mutate(editingTemplate.id!);
                                                                setEditingTemplate(null);
                                                            }
                                                        }}
                                                        className="btn-danger text-xs py-1.5 px-2"
                                                        title="Delete Template"
                                                    >
                                                        <Trash2 className="w-3.5 h-3.5" />
                                                    </button>
                                                )}
                                            </div>
                                        </div>

                                        {/* Form */}
                                        <div className="space-y-4">
                                            <div>
                                                <label className="block text-xs font-medium mb-1.5" style={{ color: 'var(--text-secondary)' }}>Template Name</label>
                                                <input
                                                    type="text"
                                                    value={editingTemplate.name || ''}
                                                    onChange={(e) => setEditingTemplate({ ...editingTemplate, name: e.target.value })}
                                                    placeholder="e.g. Standard Final Notice"
                                                    className="input w-full font-medium"
                                                />
                                            </div>

                                            <div>
                                                <div className="flex items-center justify-between mb-1.5">
                                                    <label className="block text-xs font-medium" style={{ color: 'var(--text-secondary)' }}>Message Content</label>
                                                    <span className="text-[10px]" style={{ color: 'var(--text-tertiary)' }}>Use variables below to personalize</span>
                                                </div>

                                                <div className="relative border rounded-xl overflow-hidden focus-within:ring-2 focus-within:border-transparent transition-all" style={{ borderColor: 'var(--border-default)', '--tw-ring-color': 'var(--brand-accent)' } as any}>
                                                    <textarea
                                                        value={editingTemplate.content || ''}
                                                        onChange={(e) => setEditingTemplate({ ...editingTemplate, content: e.target.value })}
                                                        className="w-full bg-transparent p-3 text-sm min-h-[160px] resize-y outline-none"
                                                        style={{ color: 'var(--text-primary)' }}
                                                        placeholder={"Hello {customer_name},\n\n..."}
                                                    />
                                                    <div className="bg-black/5 dark:bg-white/5 p-2 py-3 border-t flex flex-wrap gap-1.5 items-center" style={{ borderColor: 'var(--border-default)' }}>
                                                        {TEMPLATE_VARIABLES.map(v => (
                                                            <button
                                                                key={v.key}
                                                                type="button"
                                                                onClick={() => insertVariable(v.key)}
                                                                className="inline-flex items-center gap-1 px-2 py-1 bg-white dark:bg-black rounded-md border shadow-sm hover:border-blue-400 transition-colors text-[10px] sm:text-xs"
                                                                style={{ borderColor: 'var(--border-default)' }}
                                                                title={v.desc}
                                                            >
                                                                <span className="font-mono" style={{ color: 'var(--brand-accent)' }}>{v.key}</span>
                                                            </button>
                                                        ))}
                                                    </div>
                                                </div>
                                            </div>

                                            {/* Warning Banner */}
                                            <div className="flex items-start gap-2 p-3 rounded-lg mt-2" style={{ background: 'var(--info-soft)', color: 'var(--info)' }}>
                                                <AlignLeft className="w-4 h-4 shrink-0 mt-0.5" />
                                                <p className="text-xs">
                                                    <strong>Formatting tip:</strong> You can apply WhatsApp styles using asterisks (*bold*), underscores (_italic_), or tildes (~strikethrough~). The ledger PDF URL will be automatically appended to the very end of your message.
                                                </p>
                                            </div>

                                        </div>
                                    </div>
                                </div>
                            )}

                            {/* Footer Actions */}
                            {editingTemplate && (
                                <div className="p-4 border-t shrink-0 flex items-center justify-end gap-3 bg-black/5 dark:bg-white/5" style={{ borderColor: 'var(--border-default)' }}>
                                    <button
                                        onClick={() => setEditingTemplate(null)}
                                        className="btn px-4 text-sm"
                                    >
                                        Cancel
                                    </button>
                                    <button
                                        onClick={handleSave}
                                        disabled={createMutation.isPending || updateMutation.isPending}
                                        className="btn-primary px-6"
                                    >
                                        {(createMutation.isPending || updateMutation.isPending) ? (
                                            <span className="w-4 h-4 border-2 border-t-transparent border-current rounded-full animate-spin" />
                                        ) : (
                                            <>
                                                <Save className="w-4 h-4 mr-2" />
                                                Save Template
                                            </>
                                        )}
                                    </button>
                                </div>
                            )}
                        </div>
                    </div>
                </motion.div>
            </div>
        </AnimatePresence>
    );
}

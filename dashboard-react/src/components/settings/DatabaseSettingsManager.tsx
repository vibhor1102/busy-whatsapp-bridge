import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
    Database,
    Plus,
    Trash2,
    FolderSearch,
    AlertCircle,
    Building2,
    KeyRound
} from 'lucide-react';
import { api } from '../../services/api';
import { toast } from 'sonner';

interface CompanyConfig {
    bds_file_path: string;
    bds_password?: string;
}

interface DatabaseSettingsManagerProps {
    companies: Record<string, CompanyConfig>;
    onChange: (companies: Record<string, CompanyConfig>) => void;
}

export function DatabaseSettingsManager({ companies, onChange }: DatabaseSettingsManagerProps) {
    const [newCompanyId, setNewCompanyId] = useState('');
    const [isAdding, setIsAdding] = useState(false);
    const [isBrowsingFile, setIsBrowsingFile] = useState<string | null>(null);

    const handleUpdateCompany = (id: string, field: keyof CompanyConfig, value: string) => {
        onChange({
            ...companies,
            [id]: {
                ...companies[id],
                [field]: value
            }
        });
    };

    const handleRemoveCompany = (id: string) => {
        // Prevent removing the last company
        if (Object.keys(companies).length <= 1) {
            toast.error('You must have at least one database configuration');
            return;
        }

        // Warn if removing the active company
        if (id === api.getCompanyId()) {
            toast.warning('You are removing your currently active database connection');
        }

        const newCompanies = { ...companies };
        delete newCompanies[id];
        onChange(newCompanies);
    };

    const handleAddCompany = () => {
        const id = newCompanyId.trim().toLowerCase().replace(/[^a-z0-9_-]/g, '');

        if (!id) {
            toast.error('Company ID cannot be empty');
            return;
        }

        if (companies[id]) {
            toast.error('A company with this ID already exists');
            return;
        }

        onChange({
            ...companies,
            [id]: {
                bds_file_path: '',
                bds_password: 'ILoveMyINDIA'
            }
        });

        setNewCompanyId('');
        setIsAdding(false);
    };

    const handleBrowseFile = async (id: string) => {
        setIsBrowsingFile(id);
        try {
            const response = await api.browseSystemFile();
            if (response.success && response.path) {
                handleUpdateCompany(id, 'bds_file_path', response.path);
                toast.success(`Selected file for ${id}`);
            } else if (response.message !== "No file selected") {
                toast.error(`Failed to open file browser: ${response.message}`);
            }
        } catch (err: any) {
            toast.error(`Error opening file browser: ${err.message || 'Unknown error'}`);
            console.error(err);
        } finally {
            setIsBrowsingFile(null);
        }
    };

    return (
        <div className="pb-6 border-b" style={{ borderColor: 'var(--border-default)' }}>
            <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-2.5">
                    <div className="p-2 rounded-lg" style={{ background: 'var(--info-soft)', border: '1px solid var(--info-soft-border)' }}>
                        <Database className="w-4 h-4" style={{ color: 'var(--info)' }} />
                    </div>
                    <div>
                        <h3 className="text-sm font-semibold" style={{ color: 'var(--text-primary)' }}>
                            Database Connections
                        </h3>
                        <p className="text-xs mt-0.5" style={{ color: 'var(--text-tertiary)' }}>
                            Configure your multiple Busy Account database bindings
                        </p>
                    </div>
                </div>

                <button
                    onClick={() => setIsAdding(!isAdding)}
                    className="btn-secondary text-xs py-1.5 px-3"
                    type="button"
                >
                    <Plus className="w-3.5 h-3.5 mr-1" />
                    Add Connection
                </button>
            </div>

            <AnimatePresence>
                {isAdding && (
                    <motion.div
                        initial={{ opacity: 0, height: 0 }}
                        animate={{ opacity: 1, height: 'auto' }}
                        exit={{ opacity: 0, height: 0 }}
                        className="mb-4 p-4 rounded-xl border border-dashed"
                        style={{ borderColor: 'var(--border-default)', background: 'var(--bg-input)' }}
                    >
                        <div className="flex gap-3">
                            <div className="flex-1">
                                <label className="block text-xs font-medium mb-1.5" style={{ color: 'var(--text-secondary)' }}>
                                    New Company ID
                                </label>
                                <input
                                    type="text"
                                    value={newCompanyId}
                                    onChange={(e) => setNewCompanyId(e.target.value)}
                                    onKeyDown={(e) => e.key === 'Enter' && (e.preventDefault(), handleAddCompany())}
                                    placeholder="e.g. branch1"
                                    className="input text-sm"
                                    autoFocus
                                />
                                <p className="text-[10px] mt-1.5" style={{ color: 'var(--text-tertiary)' }}>
                                    Alphanumeric characters, hyphens, and underscores only. No spaces.
                                </p>
                            </div>
                            <div className="flex items-end gap-2">
                                <button
                                    onClick={() => setIsAdding(false)}
                                    className="btn text-sm py-2 px-4"
                                    type="button"
                                >
                                    Cancel
                                </button>
                                <button
                                    onClick={handleAddCompany}
                                    className="btn-primary text-sm py-2 px-4"
                                    type="button"
                                >
                                    Add Config
                                </button>
                            </div>
                        </div>
                    </motion.div>
                )}
            </AnimatePresence>

            <div className="space-y-4">
                <AnimatePresence>
                    {Object.entries(companies).map(([id, config]) => (
                        <motion.div
                            layout
                            key={id}
                            initial={{ opacity: 0, scale: 0.98 }}
                            animate={{ opacity: 1, scale: 1 }}
                            exit={{ opacity: 0, scale: 0.98 }}
                            className="p-4 rounded-xl relative overflow-hidden group border"
                            style={{
                                background: 'var(--bg-card)',
                                borderColor: id === api.getCompanyId() ? 'var(--brand-accent)' : 'var(--border-default)'
                            }}
                        >
                            {id === api.getCompanyId() && (
                                <div
                                    className="absolute top-0 right-0 px-2 py-0.5 text-[10px] font-bold tracking-wider rounded-bl-lg"
                                    style={{ background: 'var(--brand-soft)', color: 'var(--brand-accent)' }}
                                >
                                    ACTIVE
                                </div>
                            )}

                            <div className="flex items-start justify-between mb-3">
                                <div className="flex items-center gap-2">
                                    <div className="p-1.5 rounded-md" style={{ background: 'var(--bg-input)' }}>
                                        <Building2 className="w-4 h-4" style={{ color: 'var(--text-secondary)' }} />
                                    </div>
                                    <h4 className="font-semibold text-sm" style={{ color: 'var(--text-primary)' }}>{id}</h4>
                                </div>

                                <button
                                    type="button"
                                    onClick={() => handleRemoveCompany(id)}
                                    className="opacity-0 group-hover:opacity-100 p-1.5 transition-colors rounded-lg bg-transparent hover:bg-red-50 text-red-400 hover:text-red-500"
                                    title="Remove Connection"
                                >
                                    <Trash2 className="w-4 h-4" />
                                </button>
                            </div>

                            <div className="grid grid-cols-1 md:grid-cols-12 gap-4">
                                <div className="md:col-span-8">
                                    <label className="block text-xs font-medium mt-1 mb-1.5" style={{ color: 'var(--text-secondary)' }}>
                                        Busy Database File Path (.bds)
                                    </label>
                                    <div className="flex gap-2">
                                        <input
                                            type="text"
                                            value={config.bds_file_path || ''}
                                            onChange={(e) => handleUpdateCompany(id, 'bds_file_path', e.target.value)}
                                            placeholder="e.g. C:\Path\To\Your\Database.bds or \\Server\Folder\Database.bds"
                                            className="input font-mono text-sm"
                                        />
                                        <button
                                            type="button"
                                            onClick={() => handleBrowseFile(id)}
                                            disabled={isBrowsingFile === id}
                                            className="btn-secondary px-3 flex-shrink-0"
                                            title="Browse filesystem"
                                        >
                                            {isBrowsingFile === id ? (
                                                <div className="w-4 h-4 border-2 border-t-transparent border-current rounded-full animate-spin" />
                                            ) : (
                                                <FolderSearch className="w-4 h-4" />
                                            )}
                                        </button>
                                    </div>
                                    {!config.bds_file_path && (
                                        <div className="flex items-center gap-1.5 mt-2" style={{ color: 'var(--warning)' }}>
                                            <AlertCircle className="w-3.5 h-3.5" />
                                            <p className="text-[10px] font-medium">Path is required</p>
                                        </div>
                                    )}
                                </div>

                                <div className="md:col-span-4">
                                    <label className="block text-xs font-medium mt-1 mb-1.5" style={{ color: 'var(--text-secondary)' }}>
                                        Database Password
                                    </label>
                                    <div className="relative">
                                        <input
                                            type="password"
                                            value={config.bds_password || ''}
                                            onChange={(e) => handleUpdateCompany(id, 'bds_password', e.target.value)}
                                            placeholder="ILoveMyINDIA"
                                            className="input pl-8"
                                        />
                                        <KeyRound className="w-3.5 h-3.5 absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
                                    </div>
                                </div>
                            </div>
                        </motion.div>
                    ))}

                    {Object.keys(companies).length === 0 && !isAdding && (
                        <div className="text-center py-8" style={{ color: 'var(--text-tertiary)' }}>
                            <Database className="w-8 h-8 mx-auto mb-2 opacity-30" />
                            <p className="text-sm">No database connections configured</p>
                            <button
                                type="button"
                                onClick={() => setIsAdding(true)}
                                className="btn-primary mt-4 py-1.5 px-4 text-xs mx-auto"
                            >
                                Add One Now
                            </button>
                        </div>
                    )}
                </AnimatePresence>
            </div>
        </div>
    );
}

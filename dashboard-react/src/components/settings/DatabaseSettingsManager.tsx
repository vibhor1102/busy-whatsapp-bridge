import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
    Database,
    Plus,
    Trash2,
    FolderSearch,
    AlertCircle,
    Building2,
    KeyRound,
    Wand2
} from 'lucide-react';
import { api } from '../../services/api';
import { toast } from 'sonner';

interface CompanyConfig {
    bds_file_path: string;
    bds_password?: string;
    company_name?: string;
    contact_phone?: string;
    company_address?: string;
}

interface DatabaseSettingsManagerProps {
    companies: Record<string, CompanyConfig>;
    onChange: (companies: Record<string, CompanyConfig>) => void;
}

export function DatabaseSettingsManager({ companies, onChange }: DatabaseSettingsManagerProps) {
    const [isBrowsingFile, setIsBrowsingFile] = useState<string | null>(null);
    const [isAutoDetecting, setIsAutoDetecting] = useState(false);

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
        if (Object.keys(companies).length <= 1) {
            toast.error('You must have at least one database configuration');
            return;
        }

        if (id === api.getCompanyId()) {
            toast.warning('You are removing your currently active database connection');
        }

        const newCompanies = { ...companies };
        delete newCompanies[id];
        onChange(newCompanies);
    };

    const getNextDatabaseId = () => {
        let maxId = 0;
        Object.keys(companies).forEach(id => {
            const match = id.match(/^database_(\d+)$/);
            if (match) {
                maxId = Math.max(maxId, parseInt(match[1], 10));
            }
        });
        return `database_${maxId + 1}`;
    };

    const handleAutoDetect = async () => {
        setIsAutoDetecting(true);
        try {
            const response = await api.browseSystemFile();
            if (response.success && response.path) {
                const toastId = toast.loading('Identifying database and extracting financial year...');
                const identify = await api.identifyDatabase(response.path, 'ILoveMyINDIA');

                if (identify.success) {
                    const newId = getNextDatabaseId();

                    onChange({
                        ...companies,
                        [newId]: {
                            bds_file_path: response.path,
                            bds_password: 'ILoveMyINDIA',
                            company_name: identify.company_name || ''
                        }
                    });
                    let successMsg = `Successfully configured database: ${identify.company_name || 'Database'}`;
                    if (identify.financial_year) successMsg += ` (${identify.financial_year})`;
                    toast.success(successMsg, { id: toastId });
                } else {
                    toast.error(`Auto-detect failed: ${identify.message}. Adding manually.`, { id: toastId });
                    handleAddBlank(response.path);
                }
            } else if (response.message !== "No file selected") {
                toast.error(`File browser failed: ${response.message}`);
            }
        } catch (err: any) {
            toast.error(err.message || 'Error configuring database');
        } finally {
            setIsAutoDetecting(false);
        }
    };

    const handleAddBlank = (defaultPath: string = '') => {
        const id = getNextDatabaseId();
        onChange({
            ...companies,
            [id]: {
                bds_file_path: defaultPath,
                bds_password: 'ILoveMyINDIA',
                company_name: ''
            }
        });
    };

    const handleBrowseFile = async (id: string) => {
        setIsBrowsingFile(id);
        try {
            const response = await api.browseSystemFile();
            if (response.success && response.path) {
                handleUpdateCompany(id, 'bds_file_path', response.path);
                toast.success(`Selected file path updated`);
            } else if (response.message !== "No file selected") {
                toast.error(`Failed to open file browser: ${response.message}`);
            }
        } catch (err: any) {
            toast.error(`Error opening file browser: ${err.message || 'Unknown error'}`);
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

                <div className="flex items-center gap-2">
                    <button
                        onClick={() => handleAddBlank()}
                        className="btn-secondary text-xs py-1.5 px-3"
                        type="button"
                        disabled={isAutoDetecting}
                    >
                        <Plus className="w-3.5 h-3.5 mr-1" />
                        Manual Setup
                    </button>
                    <button
                        onClick={handleAutoDetect}
                        className="btn-primary text-xs py-1.5 px-3"
                        type="button"
                        disabled={isAutoDetecting}
                    >
                        {isAutoDetecting ? (
                            <div className="w-3.5 h-3.5 mr-1 border-2 border-t-transparent border-current rounded-full animate-spin" />
                        ) : (
                            <FolderSearch className="w-3.5 h-3.5 mr-1" />
                        )}
                        Browse
                    </button>
                </div>
            </div>

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
                                    <h4 className="font-semibold text-sm" style={{ color: 'var(--text-primary)' }}>
                                        {config.company_name || id}
                                    </h4>
                                    {config.company_name && (
                                        <span className="text-xs px-2 py-0.5 rounded bg-gray-100 text-gray-500 font-mono hidden sm:inline-block">
                                            ID: {id}
                                        </span>
                                    )}
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
                                <div className="md:col-span-4">
                                    <label className="block text-xs font-medium mt-1 mb-1.5" style={{ color: 'var(--text-secondary)' }}>
                                        Display Name (Optional)
                                    </label>
                                    <input
                                        type="text"
                                        value={config.company_name || ''}
                                        onChange={(e) => handleUpdateCompany(id, 'company_name', e.target.value)}
                                        placeholder={id}
                                        className="input text-sm"
                                    />
                                </div>
                                <div className="md:col-span-8">
                                    <label className="block text-xs font-medium mt-1 mb-1.5" style={{ color: 'var(--text-secondary)' }}>
                                        Busy Database File Path (.bds)
                                    </label>
                                    <div className="flex gap-2">
                                        <input
                                            type="text"
                                            value={config.bds_file_path || ''}
                                            onChange={(e) => handleUpdateCompany(id, 'bds_file_path', e.target.value)}
                                            placeholder="e.g. C:\Path\To\Your\Database.bds"
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
                                            className="input pl-8 text-sm"
                                        />
                                        <KeyRound className="w-3.5 h-3.5 absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
                                    </div>
                                </div>

                                <div className="md:col-span-4">
                                    <label className="block text-xs font-medium mt-1 mb-1.5" style={{ color: 'var(--text-secondary)' }}>
                                        Contact Phone (Optional)
                                    </label>
                                    <input
                                        type="text"
                                        value={config.contact_phone || ''}
                                        onChange={(e) => handleUpdateCompany(id, 'contact_phone', e.target.value)}
                                        placeholder="e.g. +91 9876543210"
                                        className="input text-sm"
                                    />
                                </div>
                                <div className="md:col-span-12">
                                    <label className="block text-xs font-medium mt-1 mb-1.5" style={{ color: 'var(--text-secondary)' }}>
                                        Registered Address (Optional)
                                    </label>
                                    <textarea
                                        value={config.company_address || ''}
                                        onChange={(e) => handleUpdateCompany(id, 'company_address', e.target.value)}
                                        placeholder="Full company address..."
                                        className="input text-sm min-h-[60px] resize-y py-2"
                                    />
                                </div>
                            </div>
                        </motion.div>
                    ))}

                    {Object.keys(companies).length === 0 && (
                        <div className="text-center py-8" style={{ color: 'var(--text-tertiary)' }}>
                            <Database className="w-8 h-8 mx-auto mb-2 opacity-30" />
                            <p className="text-sm">No database connections configured</p>
                            <button
                                type="button"
                                onClick={handleAutoDetect}
                                className="btn-primary mt-4 py-1.5 px-4 text-xs mx-auto"
                            >
                                <Wand2 className="w-3.5 h-3.5 mr-1" />
                                Auto Detect Now
                            </button>
                        </div>
                    )}
                </AnimatePresence>
            </div>
        </div>
    );
}

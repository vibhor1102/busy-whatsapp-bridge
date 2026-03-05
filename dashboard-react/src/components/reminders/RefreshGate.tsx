import React, { useState, useEffect, useRef, useCallback } from 'react';
import { RefreshCw, Clock, AlertTriangle, X, Database, CheckCircle2, Loader2 } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import api from '../../services/api';
import type { RefreshStats } from '../../types';

interface RefreshGateProps {
    refreshStats: RefreshStats | null;
    onRefreshComplete: () => void;
    onCancel: () => void;
}

/**
 * RefreshGate component.
 *
 * Displays a "Data Refresh Required" overlay when snapshot data is stale (>1 hour).
 * Shows a progress bar that estimates completion based on the rolling average of the last
 * five refresh durations.  The user can cancel the refresh at any time.
 */
const RefreshGate: React.FC<RefreshGateProps> = ({ refreshStats, onRefreshComplete, onCancel }) => {
    const [isRefreshing, setIsRefreshing] = useState(false);
    const [elapsedMs, setElapsedMs] = useState(0);
    const [error, setError] = useState<string | null>(null);
    const [completed, setCompleted] = useState(false);
    const abortRef = useRef<AbortController | null>(null);
    const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);

    const estimatedMs = refreshStats?.rolling_avg_ms || 1_800_000; // fallback 30 min

    // --- progress calculation ------------------------------------------------
    const progress = Math.min(95, (elapsedMs / estimatedMs) * 100);
    const displayProgress = completed ? 100 : progress;

    const formatTime = (ms: number) => {
        const totalSec = Math.round(ms / 1000);
        const m = Math.floor(totalSec / 60);
        const s = totalSec % 60;
        return m > 0 ? `${m}m ${s}s` : `${s}s`;
    };

    const remainingMs = Math.max(0, estimatedMs - elapsedMs);

    // --- start refresh -------------------------------------------------------
    const startRefresh = useCallback(async () => {
        setIsRefreshing(true);
        setElapsedMs(0);
        setError(null);
        setCompleted(false);

        // Start elapsed timer
        const start = Date.now();
        timerRef.current = setInterval(() => {
            setElapsedMs(Date.now() - start);
        }, 250);

        const controller = new AbortController();
        abortRef.current = controller;

        try {
            await api.refreshReminderSnapshotWithSignal(controller.signal);
            const snapshot = await api.getReminderSnapshotStatus();
            await api.getEligibleParties({ limit: 1, filter_by: 'all' });
            if (!snapshot?.has_snapshot || !snapshot?.last_refreshed_at) {
                throw new Error('Refresh finished but snapshot metadata is not available. Please retry.');
            }
            setCompleted(true);
            // Wait a tick for the 100% animation
            setTimeout(() => {
                onRefreshComplete();
            }, 800);
        } catch (err: unknown) {
            if (controller.signal.aborted) {
                // User cancelled — do nothing, onCancel is already called
                return;
            }
            const message = err instanceof Error ? err.message : 'Refresh failed. Please try again.';
            setError(message);
        } finally {
            if (timerRef.current) clearInterval(timerRef.current);
            setIsRefreshing(false);
        }
    }, [onRefreshComplete]);

    // Cleanup on unmount
    useEffect(() => {
        return () => {
            if (timerRef.current) clearInterval(timerRef.current);
            if (abortRef.current) abortRef.current.abort();
        };
    }, []);

    const handleCancel = () => {
        if (abortRef.current) abortRef.current.abort();
        if (timerRef.current) clearInterval(timerRef.current);
        setIsRefreshing(false);
        onCancel();
    };

    // --- staleness info ------------------------------------------------------
    const lastRefreshAt = refreshStats?.last_refresh_at;
    const stalenessText = lastRefreshAt
        ? (() => {
            const diff = Date.now() - new Date(lastRefreshAt).getTime();
            const hours = Math.floor(diff / 3_600_000);
            const minutes = Math.floor((diff % 3_600_000) / 60_000);
            if (hours > 0) return `${hours}h ${minutes}m ago`;
            return `${minutes}m ago`;
        })()
        : 'Never';

    return (
        <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -20 }}
            className="flex items-center justify-center min-h-[60vh]"
        >
            <div className="w-full max-w-lg mx-auto">
                <div className="bg-white dark:bg-gray-800 rounded-2xl shadow-xl border border-gray-200 dark:border-gray-700 overflow-hidden">
                    {/* Header */}
                    <div className="bg-gradient-to-r from-amber-500 to-orange-500 p-6 text-white">
                        <div className="flex items-center gap-3">
                            <div className="p-2 bg-white/20 rounded-lg">
                                <Database className="w-6 h-6" />
                            </div>
                            <div>
                                <h2 className="text-xl font-bold">Data Refresh Required</h2>
                                <p className="text-amber-100 text-sm mt-1">
                                    Snapshot data must be refreshed before you can proceed
                                </p>
                            </div>
                        </div>
                    </div>

                    {/* Content */}
                    <div className="p-6 space-y-5">
                        {/* Staleness Info */}
                        <div className="flex items-center gap-3 p-3 bg-amber-50 dark:bg-amber-900/20 rounded-lg border border-amber-200 dark:border-amber-800">
                            <AlertTriangle className="w-5 h-5 text-amber-600 dark:text-amber-400 shrink-0" />
                            <div className="text-sm">
                                <span className="font-medium text-amber-800 dark:text-amber-300">Last refreshed: </span>
                                <span className="text-amber-700 dark:text-amber-400">{stalenessText}</span>
                            </div>
                        </div>

                        {/* Estimated Time */}
                        {!isRefreshing && !error && !completed && (
                            <div className="flex items-center gap-3 p-3 bg-blue-50 dark:bg-blue-900/20 rounded-lg border border-blue-200 dark:border-blue-800">
                                <Clock className="w-5 h-5 text-blue-600 dark:text-blue-400 shrink-0" />
                                <div className="text-sm">
                                    <span className="font-medium text-blue-800 dark:text-blue-300">Estimated time: </span>
                                    <span className="text-blue-700 dark:text-blue-400">~{formatTime(estimatedMs)}</span>
                                    {refreshStats && refreshStats.last_5_durations_ms.length > 0 && (
                                        <span className="text-blue-500 dark:text-blue-500 ml-1">
                                            (based on {refreshStats.last_5_durations_ms.length} previous refresh{refreshStats.last_5_durations_ms.length > 1 ? 'es' : ''})
                                        </span>
                                    )}
                                </div>
                            </div>
                        )}

                        {/* Progress Bar & Timer (during refresh) */}
                        <AnimatePresence>
                            {isRefreshing && (
                                <motion.div
                                    initial={{ opacity: 0, height: 0 }}
                                    animate={{ opacity: 1, height: 'auto' }}
                                    exit={{ opacity: 0, height: 0 }}
                                    className="space-y-3"
                                >
                                    {/* Progress bar */}
                                    <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-3 overflow-hidden">
                                        <motion.div
                                            className="h-full rounded-full bg-gradient-to-r from-blue-500 to-indigo-500"
                                            initial={{ width: '0%' }}
                                            animate={{ width: `${displayProgress}%` }}
                                            transition={{ duration: 0.3, ease: 'easeOut' }}
                                        />
                                    </div>

                                    {/* Timer info */}
                                    <div className="flex justify-between text-sm text-gray-500 dark:text-gray-400">
                                        <span className="flex items-center gap-1.5">
                                            <Loader2 className="w-3.5 h-3.5 animate-spin" />
                                            Elapsed: {formatTime(elapsedMs)}
                                        </span>
                                        <span>
                                            {displayProgress < 95
                                                ? `~${formatTime(remainingMs)} remaining`
                                                : 'Almost done...'}
                                        </span>
                                    </div>

                                    <p className="text-xs text-gray-400 dark:text-gray-500 text-center">
                                        Querying MS Access database — this may take a few minutes
                                    </p>
                                </motion.div>
                            )}
                        </AnimatePresence>

                        {/* Completion message */}
                        <AnimatePresence>
                            {completed && (
                                <motion.div
                                    initial={{ opacity: 0, scale: 0.9 }}
                                    animate={{ opacity: 1, scale: 1 }}
                                    className="flex items-center gap-3 p-3 bg-green-50 dark:bg-green-900/20 rounded-lg border border-green-200 dark:border-green-800"
                                >
                                    <CheckCircle2 className="w-5 h-5 text-green-600 dark:text-green-400 shrink-0" />
                                    <div className="text-sm text-green-700 dark:text-green-300 font-medium">
                                        Refresh complete! Loading data...
                                    </div>
                                </motion.div>
                            )}
                        </AnimatePresence>

                        {/* Error message */}
                        {error && (
                            <div className="flex items-center gap-3 p-3 bg-red-50 dark:bg-red-900/20 rounded-lg border border-red-200 dark:border-red-800">
                                <AlertTriangle className="w-5 h-5 text-red-600 dark:text-red-400 shrink-0" />
                                <div className="text-sm text-red-700 dark:text-red-300">{error}</div>
                            </div>
                        )}

                        {/* Actions */}
                        <div className="flex gap-3 pt-2">
                            {!isRefreshing && !completed ? (
                                <>
                                    <button
                                        onClick={startRefresh}
                                        className="flex-1 flex items-center justify-center gap-2 px-4 py-2.5 bg-gradient-to-r from-blue-600 to-indigo-600 text-white rounded-lg font-medium hover:from-blue-700 hover:to-indigo-700 transition-all shadow-sm"
                                    >
                                        <RefreshCw className="w-4 h-4" />
                                        Refresh Now
                                    </button>
                                    <button
                                        onClick={onCancel}
                                        className="px-4 py-2.5 text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors"
                                    >
                                        Back
                                    </button>
                                </>
                            ) : isRefreshing ? (
                                <button
                                    onClick={handleCancel}
                                    className="flex-1 flex items-center justify-center gap-2 px-4 py-2.5 bg-red-50 dark:bg-red-900/30 text-red-600 dark:text-red-400 border border-red-200 dark:border-red-800 rounded-lg font-medium hover:bg-red-100 dark:hover:bg-red-900/50 transition-colors"
                                >
                                    <X className="w-4 h-4" />
                                    Cancel Refresh
                                </button>
                            ) : null}
                        </div>
                    </div>
                </div>
            </div>
        </motion.div>
    );
};

export default RefreshGate;

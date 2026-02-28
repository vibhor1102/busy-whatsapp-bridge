// Refetch intervals in milliseconds
export const REFETCH_INTERVALS = {
  DASHBOARD_STATS: 30000,  // 30 seconds
  BAILEYS_STATUS: 5000,    // 5 seconds
  QUEUE_STATS: 5000,       // 5 seconds
  LIVE_LOGS: 3000,         // 3 seconds
  REMINDER_STATS: 30000,   // 30 seconds
} as const;

// Limits and pagination
export const LIMITS = {
  MAX_LOGS: 1000,
  DEFAULT_PAGE_SIZE: 50,
  MAX_PAGE_SIZE: 100,
} as const;

// Retry and delay configurations in milliseconds
export const RETRY_DELAYS = {
  SESSION_POLLING: 2000,   // 2 seconds
  SESSION_CLEANUP: 5000,   // 5 seconds
} as const;

// Polling intervals in milliseconds
export const POLLING = {
  SESSION_INTERVAL: 2000,  // 2 seconds
} as const;

const LOG_LEVELS = {
  debug: 0,
  info: 1,
  warn: 2,
  error: 3,
  none: 4,
};

const currentLevel = (import.meta.env.VITE_LOG_LEVEL || 'error').toLowerCase();
const currentLevelValue = LOG_LEVELS[currentLevel] ?? LOG_LEVELS.error;

const logger = {
  debug: (...args) => {
    if (currentLevelValue <= LOG_LEVELS.debug) console.debug('[DEBUG]', ...args);
  },
  info: (...args) => {
    if (currentLevelValue <= LOG_LEVELS.info) console.info('[INFO]', ...args);
  },
  warn: (...args) => {
    if (currentLevelValue <= LOG_LEVELS.warn) console.warn('[WARN]', ...args);
  },
  error: (...args) => {
    if (currentLevelValue <= LOG_LEVELS.error) console.error('[ERROR]', ...args);
  },
};

export default logger;

/**
 * CodeSynth 全域設定常數
 */

/** Python 後端伺服器基礎 URL */
export const SERVER_URL = 'http://127.0.0.1:8000';

/** API 路徑前綴 */
export const API = {
    HEALTH_CHECK: `${SERVER_URL}/api/health_check`,
    SNAPSHOT: `${SERVER_URL}/api/snapshot`,
    BATCH_SNAPSHOT: `${SERVER_URL}/api/batch_snapshot`,
    DASHBOARD: `${SERVER_URL}/api/dashboard`,
    GET_VERSION: `${SERVER_URL}/api/get_version_content`,
    UPDATE_STATUS: `${SERVER_URL}/api/update_status`,
    UPDATE_TAG: `${SERVER_URL}/api/update_tag`,
    SCREENSHOTS: `${SERVER_URL}/api/screenshots`,
    SIMULATION: `${SERVER_URL}/api/simulation/start`,
    AI_CONTEXT: `${SERVER_URL}/api/ai/context`,
    AI_MEMORY: `${SERVER_URL}/api/ai/memory`,
    AI_CONDENSE: `${SERVER_URL}/api/ai/condense_memory`,
    STAGE_CREATE: `${SERVER_URL}/api/stage/create`,
    STAGE_LIST: `${SERVER_URL}/api/stage/list`,
    STAGE_ITEMS: `${SERVER_URL}/api/stage/items`,
    SKILL_LIST: `${SERVER_URL}/api/skill/list`,
    SKILL_INSTALL: `${SERVER_URL}/api/skill/install`,
    WIZARD_TEMPLATES: `${SERVER_URL}/api/wizard/templates`,
    WIZARD_CREATE: `${SERVER_URL}/api/wizard/create`,
    PREVIEW_INIT: `${SERVER_URL}/api/preview/init`,
    PREVIEW_BASE: `${SERVER_URL}/api/preview`,
} as const;

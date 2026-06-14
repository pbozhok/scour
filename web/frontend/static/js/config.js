// ============================================
// Settings Modal
// ============================================

const MASK = '••••••••';

// Schema — drives the entire UI
const SECTIONS = [
    {
        key: 'api_keys',
        title: 'API Keys',
        icon: `<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m21 2-2 2m-7.61 7.61a5.5 5.5 0 1 1-7.778 7.778 5.5 5.5 0 0 1 7.777-7.777zm0 0L15.5 7.5m0 0 3 3L22 7l-3-3m-3.5 3.5L19 4"/></svg>`,
        fields: [
            {
                key: 'mistral',
                label: 'Mistral API Key',
                type: 'secret',
                help: 'AI filtering & scoring — console.mistral.ai',
                placeholder: 'sk-…',
            },
            {
                key: 'gemini',
                label: 'Gemini API Key',
                type: 'secret',
                help: 'Alternative AI backend — aistudio.google.com',
                placeholder: 'AIza…',
            },
            {
                key: 'serpapi',
                label: 'SerpAPI Key',
                type: 'secret',
                help: 'Fetches product reviews — serpapi.com',
                placeholder: 'your-serpapi-key',
            },
        ],
    },
    {
        key: 'search',
        title: 'Search',
        icon: `<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35"/></svg>`,
        fields: [
            {
                key: 'default_max_results',
                label: 'Max results',
                type: 'number',
                min: 1, max: 200, step: 1,
                help: 'Items returned per search',
                defaultKey: 40,
            },
            {
                key: 'default_currency',
                label: 'Currency',
                type: 'select',
                options: ['EUR', 'DKK', 'SEK'],
                help: 'Display currency for prices',
            },
            {
                key: 'default_max_keywords',
                label: 'Keyword variants',
                type: 'number',
                min: 1, max: 10, step: 1,
                help: 'AI-generated query expansions',
            },
        ],
    },
    {
        key: 'pipeline',
        title: 'Performance',
        icon: `<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M13 2L3 14h9l-1 8 10-12h-9l1-8z"/></svg>`,
        fields: [
            {
                key: 'scraper_timeout',
                label: 'Scraper timeout',
                type: 'number',
                min: 5, max: 120, step: 1,
                help: 'Seconds before giving up on a marketplace',
                unit: 's',
            },
            {
                key: 'max_retries',
                label: 'Max retries',
                type: 'number',
                min: 1, max: 10, step: 1,
                help: 'Network error retry attempts',
            },
            {
                key: 'batch_size',
                label: 'AI batch size',
                type: 'number',
                min: 10, max: 200, step: 10,
                help: 'Items sent per AI filtering round',
            },
            {
                key: 'delay_between_batches',
                label: 'Batch delay',
                type: 'number',
                min: 0, max: 5, step: 0.1,
                help: 'Pause between batches (rate limit buffer)',
                unit: 's',
            },
        ],
    },
    {
        key: 'reviews',
        title: 'Reviews',
        icon: `<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/></svg>`,
        fields: [
            {
                key: 'max_review_results',
                label: 'Reviews per item',
                type: 'number',
                min: 1, max: 10, step: 1,
                help: 'Review sources fetched per product',
            },
            {
                key: 'review_delay',
                label: 'Review search delay',
                type: 'number',
                min: 0, max: 30, step: 0.5,
                help: 'Pause between review lookups',
                unit: 's',
            },
        ],
    },
];

const EYE_OPEN = `<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M2 12s3-7 10-7 10 7 10 7-3 7-10 7-10-7-10-7Z"/><circle cx="12" cy="12" r="3"/></svg>`;
const EYE_CLOSED = `<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M9.88 9.88a3 3 0 1 0 4.24 4.24"/><path d="M10.73 5.08A10.43 10.43 0 0 1 12 5c7 0 10 7 10 7a13.16 13.16 0 0 1-1.67 2.68"/><path d="M6.61 6.61A13.526 13.526 0 0 0 2 12s3 7 10 7a9.74 9.74 0 0 0 5.39-1.61"/><line x1="2" x2="22" y1="2" y2="22"/></svg>`;

let _config = null;
let _defaults = null;

// ── Open / close ─────────────────────────────────────────────────────────────

function openSettingsModal() {
    const overlay = document.getElementById('config-modal');
    if (!overlay) return;
    loadAndRender();
    overlay.classList.add('open');
    document.body.style.overflow = 'hidden';
}

function closeSettingsModal() {
    const overlay = document.getElementById('config-modal');
    if (!overlay) return;
    overlay.classList.remove('open');
    document.body.style.overflow = '';
}

// ── Data ─────────────────────────────────────────────────────────────────────

async function loadAndRender() {
    const body = document.getElementById('config-modal-body');
    if (!body) return;
    body.innerHTML = '<div class="config-loading">loading…</div>';

    try {
        const res = await fetch('/api/v1/config');
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json();
        _config = data.config;
        _defaults = data.defaults;
        renderSections(body);
    } catch (e) {
        body.innerHTML = `<div class="config-error">Could not load settings: ${e.message}</div>`;
    }
}

async function saveConfig() {
    const btn = document.getElementById('config-save-btn');
    if (btn) { btn.disabled = true; btn.textContent = 'Saving…'; }

    try {
        const res = await fetch('/api/v1/config', {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ config: collectValues() }),
        });
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        toast('settings saved');
        closeSettingsModal();
        if (typeof initUserConfig === 'function') initUserConfig();
    } catch (e) {
        toast(`save failed: ${e.message}`, true);
    } finally {
        if (btn) { btn.disabled = false; btn.textContent = 'Save'; }
    }
}

async function resetConfig() {
    if (!confirm('Reset all settings to defaults?')) return;
    try {
        const res = await fetch('/api/v1/config', { method: 'DELETE' });
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        toast('reset to defaults');
        loadAndRender();
    } catch (e) {
        toast(`reset failed: ${e.message}`, true);
    }
}

// ── Rendering ─────────────────────────────────────────────────────────────────

function renderSections(container) {
    container.innerHTML = '';
    for (const section of SECTIONS) {
        container.appendChild(buildSection(section));
    }
}

function buildSection(section) {
    const sectionData = (_config || {})[section.key] || {};
    const sectionDefaults = (_defaults || {})[section.key] || {};

    const wrap = document.createElement('div');
    wrap.className = 'config-section';

    // Header
    const header = document.createElement('div');
    header.className = 'config-section-header';
    header.innerHTML = `
        <span class="config-section-icon">${section.icon}</span>
        <span class="config-section-title">${section.title}</span>`;
    wrap.appendChild(header);

    // Fields
    for (const field of section.fields) {
        const value = sectionData[field.key] ?? sectionDefaults[field.key] ?? '';
        const defVal = sectionDefaults[field.key];
        wrap.appendChild(buildField(section.key, field, value, defVal));
    }

    return wrap;
}

function buildField(sectionKey, field, value, defaultValue) {
    const isSecret = field.type === 'secret';
    const row = document.createElement('div');
    row.className = `config-field${isSecret ? ' is-secret' : ''}`;

    // Left: label + help
    const left = document.createElement('div');
    left.className = 'config-field-left';

    const labelEl = document.createElement('label');
    labelEl.className = 'config-label';
    labelEl.setAttribute('for', `cfg-${sectionKey}-${field.key}`);
    labelEl.textContent = field.label;

    // Status badge for API keys
    if (isSecret) {
        const isSet = value && value !== MASK && value !== '';
        const badge = document.createElement('span');
        badge.className = `config-key-status ${isSet ? 'is-set' : 'is-unset'}`;
        badge.textContent = isSet ? '✓ set' : 'not set';
        labelEl.appendChild(badge);
    }

    left.appendChild(labelEl);

    if (field.help) {
        const helpEl = document.createElement('div');
        helpEl.className = 'config-help';
        helpEl.textContent = field.help;
        left.appendChild(helpEl);
    }

    row.appendChild(left);

    // Input wrapper
    const wrapper = document.createElement('div');
    wrapper.className = 'config-input-wrapper';

    let inputEl;

    if (isSecret) {
        inputEl = document.createElement('input');
        inputEl.type = 'password';
        inputEl.value = value || '';
        inputEl.placeholder = field.placeholder || '';
        inputEl.autocomplete = 'off';
        inputEl.spellcheck = false;

        const eyeBtn = document.createElement('button');
        eyeBtn.type = 'button';
        eyeBtn.className = 'config-eye-btn';
        eyeBtn.title = 'Show / hide';
        eyeBtn.innerHTML = EYE_OPEN;
        eyeBtn.addEventListener('click', () => {
            const isHidden = inputEl.type === 'password';
            inputEl.type = isHidden ? 'text' : 'password';
            eyeBtn.innerHTML = isHidden ? EYE_CLOSED : EYE_OPEN;
        });

        wrapper.appendChild(inputEl);
        wrapper.appendChild(eyeBtn);

    } else if (field.type === 'select') {
        inputEl = document.createElement('select');
        inputEl.className = 'config-input config-select';
        for (const opt of field.options) {
            const o = document.createElement('option');
            o.value = opt;
            o.textContent = opt;
            if (String(opt) === String(value)) o.selected = true;
            inputEl.appendChild(o);
        }
        wrapper.appendChild(inputEl);

    } else {
        // number
        inputEl = document.createElement('input');
        inputEl.type = 'number';
        if (field.min !== undefined) inputEl.min = field.min;
        if (field.max !== undefined) inputEl.max = field.max;
        if (field.step !== undefined) inputEl.step = field.step;
        inputEl.value = value ?? '';

        if (field.unit) {
            const unitEl = document.createElement('span');
            unitEl.className = 'config-default-hint';
            unitEl.textContent = field.unit;
            wrapper.appendChild(inputEl);
            wrapper.appendChild(unitEl);
        } else {
            wrapper.appendChild(inputEl);
        }

        // Default hint
        if (defaultValue !== undefined && defaultValue !== null) {
            const hint = document.createElement('span');
            hint.className = 'config-default-hint';
            hint.textContent = `(default: ${defaultValue}${field.unit || ''})`;
            wrapper.appendChild(hint);
        }
    }

    if (inputEl) {
        inputEl.id = `cfg-${sectionKey}-${field.key}`;
        inputEl.className = (inputEl.className ? inputEl.className + ' ' : '') + 'config-input';
        inputEl.dataset.section = sectionKey;
        inputEl.dataset.field = field.key;
        inputEl.dataset.ftype = field.type;
    }

    row.appendChild(wrapper);
    return row;
}

// ── Collect form values ───────────────────────────────────────────────────────

function collectValues() {
    const result = {};
    document.querySelectorAll('.config-input').forEach(el => {
        const section = el.dataset.section;
        const field = el.dataset.field;
        const ftype = el.dataset.ftype;
        if (!section || !field) return;
        if (!result[section]) result[section] = {};

        let val = el.value;
        if (ftype === 'number') val = val === '' ? null : Number(val);
        result[section][field] = val;
    });
    return result;
}

// ── Toast ─────────────────────────────────────────────────────────────────────

function toast(msg, isError = false) {
    let el = document.getElementById('config-toast');
    if (!el) {
        el = document.createElement('div');
        el.id = 'config-toast';
        document.body.appendChild(el);
    }
    el.textContent = msg;
    el.className = 'config-toast' + (isError ? ' config-toast-error' : '');
    el.classList.add('visible');
    clearTimeout(el._t);
    el._t = setTimeout(() => el.classList.remove('visible'), 2800);
}

// ── Init ──────────────────────────────────────────────────────────────────────

document.addEventListener('DOMContentLoaded', () => {
    document.getElementById('config-btn')
        ?.addEventListener('click', openSettingsModal);

    document.getElementById('config-modal-close')
        ?.addEventListener('click', closeSettingsModal);

    document.getElementById('config-modal')
        ?.addEventListener('click', e => { if (e.target.id === 'config-modal') closeSettingsModal(); });

    document.getElementById('config-save-btn')
        ?.addEventListener('click', saveConfig);

    document.getElementById('config-reset-btn')
        ?.addEventListener('click', resetConfig);

    document.addEventListener('keydown', e => {
        if (e.key === 'Escape') closeSettingsModal();
    });
});

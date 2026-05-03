/**
 * Accessibility settings: font toggle, high contrast, localStorage persistence.
 */
(function() {
    const SETTINGS_KEY = 'ot_accessibility_settings';

    const defaults = {
        font: 'default',      // 'default' | 'atkinson' | 'opendyslexic'
        highContrast: false,
    };

    function loadSettings() {
        try {
            const raw = localStorage.getItem(SETTINGS_KEY);
            return raw ? { ...defaults, ...JSON.parse(raw) } : { ...defaults };
        } catch (e) {
            return { ...defaults };
        }
    }

    function saveSettings(settings) {
        localStorage.setItem(SETTINGS_KEY, JSON.stringify(settings));
    }

    function applySettings(settings) {
        const body = document.body;

        // Font
        body.classList.remove('font-atkinson', 'font-opendyslexic');
        if (settings.font === 'atkinson') {
            body.classList.add('font-atkinson');
        } else if (settings.font === 'opendyslexic') {
            body.classList.add('font-opendyslexic');
        }

        // High contrast
        body.classList.toggle('high-contrast', settings.highContrast);

        // Update controls if they exist
        const fontRadios = document.querySelectorAll('input[name="a11y-font"]');
        fontRadios.forEach(r => {
            r.checked = (r.value === settings.font);
        });

        const hcCheckbox = document.getElementById('a11y-high-contrast');
        if (hcCheckbox) {
            hcCheckbox.checked = settings.highContrast;
        }
    }

    function init() {
        const settings = loadSettings();
        applySettings(settings);

        // Settings toggle button
        const toggleBtn = document.getElementById('a11y-toggle-btn');
        const panel = document.getElementById('a11y-panel');

        if (toggleBtn && panel) {
            toggleBtn.addEventListener('click', () => {
                panel.classList.toggle('open');
            });

            // Close when clicking outside
            document.addEventListener('click', (e) => {
                if (!panel.contains(e.target) && e.target !== toggleBtn) {
                    panel.classList.remove('open');
                }
            });
        }

        // Font radios
        const fontRadios = document.querySelectorAll('input[name="a11y-font"]');
        fontRadios.forEach(radio => {
            radio.addEventListener('change', () => {
                const settings = loadSettings();
                settings.font = radio.value;
                saveSettings(settings);
                applySettings(settings);
            });
        });

        // High contrast checkbox
        const hcCheckbox = document.getElementById('a11y-high-contrast');
        if (hcCheckbox) {
            hcCheckbox.addEventListener('change', () => {
                const settings = loadSettings();
                settings.highContrast = hcCheckbox.checked;
                saveSettings(settings);
                applySettings(settings);
            });
        }
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();

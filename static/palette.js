// static/palette.js
document.addEventListener('DOMContentLoaded', () => {
    const form = document.getElementById('palette-form');
    const globalLoader = document.getElementById('global-loader-container');
    const resultsContainer = document.getElementById('results-container');
    const errorMessage = document.getElementById('error-message');
    const paletteContainer = document.getElementById('palette-container');
    const themeSwitcher = document.getElementById('theme-switcher');
    const fileInput = document.getElementById('file');
    const imagePreview = document.getElementById('image-preview');
    const imagePreviewContainer = document.querySelector('.image-preview-container');
    const fileInputLabel = document.getElementById('file-input-filename');
    const dropZone = document.querySelector('.drop-zone');
    const submitBtn = document.getElementById('palette-submit-btn');

    // Canvas and Inspector Elements
    const canvas = document.getElementById('palette-canvas');
    const ctx = canvas.getContext('2d', { willReadFrequently: true });
    const inspector = document.getElementById('color-inspector');
    const inspectorSwatch = document.getElementById('inspector-swatch');
    const inspectorHex = document.getElementById('inspector-hex');
    const copiedMsg = document.getElementById('inspector-copied-msg');
    const imgForCanvas = new Image();
    imgForCanvas.crossOrigin = "Anonymous";

    // --- vvv NEW: Gemini Color Finder Elements vvv ---
    const colorNameInput = document.getElementById('color-name-input');
    const colorNameBtn = document.getElementById('color-name-btn');
    const colorNameResultContainer = document.getElementById('color-name-result-container');
    const colorNameLoader = document.getElementById('color-name-loader');
    const colorNameResult = document.getElementById('color-name-result');
    // --- ^^^ END OF NEW ELEMENTS ^^^ ---


    // --- Theme Switcher ---
    if (themeSwitcher) {
        themeSwitcher.addEventListener('change', () => {
            const theme = themeSwitcher.checked ? 'dark' : 'light';
            document.documentElement.setAttribute('data-theme', theme);
            localStorage.setItem('theme', theme);
        });
        const savedTheme = localStorage.getItem('theme') || 'light';
        document.documentElement.setAttribute('data-theme', savedTheme);
        themeSwitcher.checked = savedTheme === 'dark';
    }

    // --- Drag and Drop Logic ---
    if (dropZone) {
        dropZone.addEventListener('dragover', (e) => {
            e.preventDefault();
            dropZone.classList.add('drag-over');
        });
        dropZone.addEventListener('dragleave', () => {
            dropZone.classList.remove('drag-over');
        });
        dropZone.addEventListener('drop', (e) => {
            e.preventDefault();
            dropZone.classList.remove('drag-over');
            if (e.dataTransfer.files.length > 0 && e.dataTransfer.files[0].type.startsWith('image/')) {
                handleFileSelect(e.dataTransfer.files[0]);
            } else {
                alert('Please drop an image file.');
            }
        });
    }

    // --- File Preview Logic ---
    function handleFileSelect(file) {
        const previewUrl = URL.createObjectURL(file);
        imagePreview.src = previewUrl;
        imagePreviewContainer.classList.remove('hidden');
        fileInputLabel.textContent = file.name;
        const dataTransfer = new DataTransfer();
        dataTransfer.items.add(file);
        fileInput.files = dataTransfer.files;
    }

    fileInput.addEventListener('change', (e) => {
        if (e.target.files && e.target.files.length > 0) handleFileSelect(e.target.files[0]);
    });

    // --- Form Submit Logic (with Loader) ---
    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        if (!fileInput.files || fileInput.files.length === 0) {
            errorMessage.textContent = 'Error: Please select an image file first.';
            errorMessage.classList.remove('hidden'); return;
        }
        const formData = new FormData(form);

        // Reset UI and show loader
        resultsContainer.classList.add('hidden');
        errorMessage.classList.add('hidden');
        paletteContainer.innerHTML = '';
        globalLoader.classList.remove('hidden');
        submitBtn.disabled = true;
        inspector.classList.add('hidden');

        // --- vvv NEW: Reset Gemini tool on new palette generation vvv ---
        colorNameResultContainer.classList.add('hidden');
        colorNameResult.textContent = '';
        colorNameInput.value = '';
        // --- ^^^ END OF RESET ^^^ ---

        try {
            const response = await fetch('/palette', { method: 'POST', body: formData });
            const data = await response.json();
            if (!response.ok) throw new Error(data.error);

            // Load image into canvas
            imgForCanvas.onload = () => {
                const aspectRatio = imgForCanvas.naturalHeight / imgForCanvas.naturalWidth;
                const maxWidth = canvas.parentElement.clientWidth;
                canvas.width = maxWidth; canvas.height = maxWidth * aspectRatio;
                ctx.drawImage(imgForCanvas, 0, 0, canvas.width, canvas.height);
            };
            imgForCanvas.src = data.image_url;

            // --- vvv REVERTED to handle simple hex string list vvv ---
            if (data.palette && data.palette.length > 0) {
                data.palette.forEach(hexCode => {
                    const swatchWrapper = document.createElement('div'); swatchWrapper.className = 'minimal-swatch-wrapper';
                    const swatch = document.createElement('div'); swatch.className = 'minimal-swatch'; swatch.style.backgroundColor = hexCode;

                    const hexText = document.createElement('span'); hexText.className = 'minimal-swatch-hex'; hexText.textContent = hexCode;

                    swatchWrapper.appendChild(swatch);
                    swatchWrapper.appendChild(hexText); // Only append hex text

                    swatchWrapper.addEventListener('click', () => {
                        navigator.clipboard.writeText(hexCode).then(() => {
                            hexText.textContent = 'Copied!'; swatchWrapper.classList.add('copied');
                            setTimeout(() => { hexText.textContent = hexCode; swatchWrapper.classList.remove('copied'); }, 1000);
                        });
                    });
                    paletteContainer.appendChild(swatchWrapper);
                });
            }
            // --- ^^^ END OF REVERT ^^^ ---

            resultsContainer.classList.remove('hidden'); // Show results section
        } catch (error) {
            errorMessage.textContent = `Error: ${error.message}`;
            errorMessage.classList.remove('hidden');
        } finally {
            globalLoader.classList.add('hidden');
            submitBtn.disabled = false;
        }
    });

    // --- vvv NEW: Gemini Color Finder Logic vvv ---
    if (colorNameBtn) {
        colorNameBtn.addEventListener('click', async () => {
            const hexCode = colorNameInput.value.trim();

            // Basic validation
            if (!hexCode.startsWith('#') || (hexCode.length !== 7 && hexCode.length !== 4)) {
                alert('Please enter a valid hex code (e.g., #FF0000 or #F00).');
                return;
            }

            colorNameLoader.classList.remove('hidden');
            colorNameResult.textContent = '';
            colorNameResultContainer.classList.remove('hidden');
            colorNameBtn.disabled = true;

            try {
                const response = await fetch('/get-color-name', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ hex_code: hexCode })
                });

                const data = await response.json();
                if (!response.ok) {
                    throw new Error(data.error || 'Failed to get name');
                }

                // Success! Display the name.
                colorNameResult.innerHTML = `<strong>${data.color_name}</strong>`;
                colorNameResult.style.color = 'var(--pico-primary)';

            } catch (error) {
                colorNameResult.textContent = `Error: ${error.message}`;
                colorNameResult.style.color = 'var(--error-color)';
            } finally {
                colorNameLoader.classList.add('hidden');
                colorNameBtn.disabled = false;
            }
        });
    }
    // --- ^^^ END OF NEW LOGIC ^^^ ---


    // --- Canvas MouseMove logic (unchanged) ---
    canvas.addEventListener('mousemove', (e) => {
        const rect = canvas.getBoundingClientRect(); const scaleX = canvas.width / rect.width; const scaleY = canvas.height / rect.height;
        const x = Math.floor((e.clientX - rect.left) * scaleX); const y = Math.floor((e.clientY - rect.top) * scaleY);
        try {
            const pixel = ctx.getImageData(x, y, 1, 1).data; const hex = `#${("0" + pixel[0].toString(16)).slice(-2)}${("0" + pixel[1].toString(16)).slice(-2)}${("0" + pixel[2].toString(16)).slice(-2)}`;
            inspector.classList.remove('hidden'); inspectorSwatch.style.backgroundColor = hex; inspectorHex.textContent = hex;
            inspector.style.left = `${e.clientX + 15}px`; inspector.style.top = `${e.clientY + 15}px`;
        } catch (ex) { inspector.classList.add('hidden'); }
    });
    canvas.addEventListener('mouseleave', () => { inspector.classList.add('hidden'); copiedMsg.classList.add('hidden'); });
    canvas.addEventListener('click', () => {
        const hex = inspectorHex.textContent; navigator.clipboard.writeText(hex).then(() => {
            copiedMsg.classList.remove('hidden'); setTimeout(() => { copiedMsg.classList.add('hidden'); }, 1500);
        });
    });

    // --- Export Buttons Logic ---
    let currentPalette = []; // Store current palette for export

    // Helper: Convert HEX to RGB
    function hexToRgb(hex) {
        const result = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex);
        return result ? {
            r: parseInt(result[1], 16),
            g: parseInt(result[2], 16),
            b: parseInt(result[3], 16)
        } : null;
    }

    // Helper: Convert RGB to HSL
    function rgbToHsl(r, g, b) {
        r /= 255; g /= 255; b /= 255;
        const max = Math.max(r, g, b), min = Math.min(r, g, b);
        let h, s, l = (max + min) / 2;
        if (max === min) { h = s = 0; }
        else {
            const d = max - min;
            s = l > 0.5 ? d / (2 - max - min) : d / (max + min);
            switch (max) {
                case r: h = ((g - b) / d + (g < b ? 6 : 0)) / 6; break;
                case g: h = ((b - r) / d + 2) / 6; break;
                case b: h = ((r - g) / d + 4) / 6; break;
            }
        }
        return { h: Math.round(h * 360), s: Math.round(s * 100), l: Math.round(l * 100) };
    }

    // Copy CSS Variables
    document.getElementById('copy-css-btn')?.addEventListener('click', () => {
        if (currentPalette.length === 0) { alert('Generate a palette first!'); return; }
        const css = currentPalette.map((hex, i) => `  --color-${i + 1}: ${hex};`).join('\n');
        const fullCss = `:root {\n${css}\n}`;
        navigator.clipboard.writeText(fullCss).then(() => {
            showCopyFeedback('copy-css-btn', 'Copied!');
        });
    });

    // Copy Tailwind Config
    document.getElementById('copy-tailwind-btn')?.addEventListener('click', () => {
        if (currentPalette.length === 0) { alert('Generate a palette first!'); return; }
        const colors = currentPalette.map((hex, i) => `      '${i + 1}': '${hex}',`).join('\n');
        const tailwind = `// tailwind.config.js\ncolors: {\n  palette: {\n${colors}\n  }\n}`;
        navigator.clipboard.writeText(tailwind).then(() => {
            showCopyFeedback('copy-tailwind-btn', 'Copied!');
        });
    });

    // Copy JSON
    document.getElementById('copy-json-btn')?.addEventListener('click', () => {
        if (currentPalette.length === 0) { alert('Generate a palette first!'); return; }
        const json = JSON.stringify({ palette: currentPalette }, null, 2);
        navigator.clipboard.writeText(json).then(() => {
            showCopyFeedback('copy-json-btn', 'Copied!');
        });
    });

    function showCopyFeedback(btnId, msg) {
        const btn = document.getElementById(btnId);
        const originalText = btn.innerHTML;
        btn.innerHTML = `<i class="fa-solid fa-check"></i> ${msg}`;
        btn.classList.add('copied');
        setTimeout(() => { btn.innerHTML = originalText; btn.classList.remove('copied'); }, 1500);
    }

    // --- Format Toggle Logic ---
    let currentFormat = 'hex';
    document.querySelectorAll('.format-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            document.querySelectorAll('.format-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            currentFormat = btn.dataset.format;
            updatePaletteDisplay();
        });
    });

    function updatePaletteDisplay() {
        const swatches = document.querySelectorAll('.minimal-swatch-wrapper');
        swatches.forEach((wrapper, i) => {
            const hexText = wrapper.querySelector('.minimal-swatch-hex');
            const hex = currentPalette[i];
            if (!hex) return;

            let displayText = hex;
            if (currentFormat === 'rgb') {
                const rgb = hexToRgb(hex);
                if (rgb) displayText = `rgb(${rgb.r}, ${rgb.g}, ${rgb.b})`;
            } else if (currentFormat === 'hsl') {
                const rgb = hexToRgb(hex);
                if (rgb) {
                    const hsl = rgbToHsl(rgb.r, rgb.g, rgb.b);
                    displayText = `hsl(${hsl.h}, ${hsl.s}%, ${hsl.l}%)`;
                }
            }
            hexText.textContent = displayText;

            // Update click handler for new format
            wrapper.onclick = () => {
                navigator.clipboard.writeText(displayText).then(() => {
                    hexText.textContent = 'Copied!';
                    wrapper.classList.add('copied');
                    setTimeout(() => {
                        hexText.textContent = displayText;
                        wrapper.classList.remove('copied');
                    }, 1000);
                });
            };
        });
    }

    // Store palette when generated (hook into existing logic)
    const originalSubmit = form.onsubmit;
    form.addEventListener('submit', () => {
        // This runs after the original handler via event propagation
        setTimeout(() => {
            currentPalette = Array.from(document.querySelectorAll('.minimal-swatch')).map(el => {
                const rgb = el.style.backgroundColor;
                const match = rgb.match(/rgb\((\d+),\s*(\d+),\s*(\d+)\)/);
                if (match) {
                    const hex = '#' + [match[1], match[2], match[3]].map(x => parseInt(x).toString(16).padStart(2, '0')).join('');
                    return hex;
                }
                return null;
            }).filter(Boolean);
        }, 1500);
    });

});
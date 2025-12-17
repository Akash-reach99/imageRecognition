// static/generate.js
document.addEventListener('DOMContentLoaded', () => {

    // --- Selectors ---
    const t2iForm = document.getElementById('generate-form');
    const promptInput = document.getElementById('prompt');
    const t2iBtn = document.getElementById('generate-submit-btn');
    const i2iForm = document.getElementById('generate-from-image-form');
    const i2iInput = document.getElementById('image-file-input');
    const i2iBtn = document.getElementById('generate-from-image-btn');
    const i2iPreview = document.getElementById('image-upload-preview');
    const i2iPreviewContainer = document.getElementById('image-upload-preview-container');
    
    // Result Areas
    const resultsContainer = document.getElementById('results-container');
    const generatedImage = document.getElementById('generated-image');
    const i2iResults = document.getElementById('image-to-image-results-container');
    const i2iOriginal = document.getElementById('i2i-original-image');
    const i2iGenerated = document.getElementById('i2i-generated-image');
    const loader = document.getElementById('loader');
    const i2iLoader = document.getElementById('image-to-image-loader');
    const errorMsg = document.getElementById('error-message');
    const i2iError = document.getElementById('image-to-image-error');

    // Prompt Helper
    const ideaInput = document.getElementById('prompt-idea-input');
    const ideaBtn = document.getElementById('prompt-idea-btn');
    const suggestionContainer = document.getElementById('prompt-suggestion-container');
    const suggestionBox = document.getElementById('prompt-suggestion-box');
    const useSuggestionBtn = document.getElementById('use-suggestion-btn');

    // Editor
    const editorSection = document.getElementById('image-editor-section');
    const editBtn = document.getElementById('edit-generated-image-btn');
    const canvas = document.getElementById('image-editor-canvas');
    const ctx = canvas.getContext('2d');
    const resetEditorBtn = document.getElementById('reset-editor-btn');
    const downloadEditedBtn = document.getElementById('download-edited-image-btn');
    const addTextBtn = document.getElementById('add-text-btn');
    const applyFilterBtn = document.getElementById('apply-filter-btn');

    let currentImage = new Image();
    let currentImageSrc = "";

    // --- 1. Text to Image Logic ---
    t2iForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const prompt = promptInput.value.trim();
        if(!prompt) return;

        loader.classList.remove('hidden');
        resultsContainer.classList.add('hidden');
        errorMsg.classList.add('hidden');
        t2iBtn.disabled = true;

        try {
            const formData = new FormData();
            formData.append('prompt', prompt);

            const res = await fetch('/generate-image', { method: 'POST', body: formData });
            const data = await res.json();
            if(data.error) throw new Error(data.error);

            generatedImage.src = data.image_url;
            currentImageSrc = data.image_url;
            resultsContainer.classList.remove('hidden');
            
            // Setup Download Button
            document.getElementById('download-generated-image-btn').onclick = () => {
                const link = document.createElement('a');
                link.href = data.image_url;
                link.download = `generated_${Date.now()}.png`;
                link.click();
            };

            updateCounter('imageGen');

        } catch (err) {
            errorMsg.textContent = err.message;
            errorMsg.classList.remove('hidden');
        } finally {
            loader.classList.add('hidden');
            t2iBtn.disabled = false;
        }
    });

    // --- 2. Image to Image Logic ---
    i2iInput.addEventListener('change', (e) => {
        const file = e.target.files[0];
        if(file) {
            i2iPreview.src = URL.createObjectURL(file);
            i2iPreviewContainer.classList.remove('hidden');
            document.getElementById('image-file-input-filename').textContent = file.name;
            i2iBtn.disabled = false;
        }
    });

    i2iForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        if(!i2iInput.files[0]) return;

        i2iLoader.classList.remove('hidden');
        i2iResults.classList.add('hidden');
        i2iError.classList.add('hidden');
        i2iBtn.disabled = true;

        const formData = new FormData(i2iForm);
        
        try {
            const res = await fetch('/generate-image-from-image', { method: 'POST', body: formData });
            const data = await res.json();
            if(data.error) throw new Error(data.error);

            i2iOriginal.src = data.original_image_url;
            i2iGenerated.src = data.generated_image_url;
            i2iResults.classList.remove('hidden');
            
            document.getElementById('i2i-download-btn').href = data.generated_image_url;
            
            updateCounter('gemini'); // Prompt gen
            updateCounter('imageGen'); // Image gen

        } catch (err) {
            i2iError.textContent = err.message;
            i2iError.classList.remove('hidden');
        } finally {
            i2iLoader.classList.add('hidden');
            i2iBtn.disabled = false;
        }
    });

    // --- 3. Prompt Idea Logic ---
    ideaBtn.addEventListener('click', async () => {
        const idea = ideaInput.value.trim();
        if(!idea) return;
        
        ideaBtn.disabled = true;
        ideaBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i>';
        
        try {
            const res = await fetch('/generate-prompt-idea', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ idea })
            });
            const data = await res.json();
            
            suggestionBox.textContent = data.prompt;
            suggestionContainer.classList.remove('hidden');
            updateCounter('gemini');

        } catch (e) {
            alert("Failed to generate idea");
        } finally {
            ideaBtn.disabled = false;
            ideaBtn.innerHTML = '<i class="fa-solid fa-magic"></i>';
        }
    });

    useSuggestionBtn.addEventListener('click', () => {
        promptInput.value = suggestionBox.textContent;
        suggestionContainer.classList.add('hidden');
    });

    // --- 4. Editor Logic ---
    editBtn.addEventListener('click', () => {
        if(!currentImageSrc) return;
        editorSection.classList.remove('hidden');
        
        currentImage.onload = () => {
            canvas.width = currentImage.width;
            canvas.height = currentImage.height;
            ctx.drawImage(currentImage, 0, 0);
        };
        currentImage.crossOrigin = "Anonymous";
        currentImage.src = currentImageSrc;
        
        // Scroll to editor
        editorSection.scrollIntoView({ behavior: 'smooth' });
    });

    addTextBtn.addEventListener('click', () => {
        const text = document.getElementById('text-overlay-input').value;
        const color = document.getElementById('text-color').value;
        const size = document.getElementById('text-size').value;
        
        if(!text) return;
        
        // Redraw image to clear previous text/filters if needed, 
        // NOTE: A real editor would use layers. This is a simple destructive edit.
        // For now, we draw on top of whatever is there.
        
        ctx.fillStyle = color;
        ctx.font = `bold ${size}px sans-serif`;
        ctx.fillText(text, 50, parseInt(size) + 50);
    });

    applyFilterBtn.addEventListener('click', () => {
        const type = document.getElementById('filter-select').value;
        if(type === 'none') {
            ctx.drawImage(currentImage, 0, 0);
            return;
        }
        
        const imageData = ctx.getImageData(0, 0, canvas.width, canvas.height);
        const data = imageData.data;
        
        for (let i = 0; i < data.length; i += 4) {
            const r = data[i], g = data[i + 1], b = data[i + 2];
            if (type === 'grayscale') {
                const v = 0.3 * r + 0.59 * g + 0.11 * b;
                data[i] = data[i + 1] = data[i + 2] = v;
            } else if (type === 'invert') {
                data[i] = 255 - r; data[i + 1] = 255 - g; data[i + 2] = 255 - b;
            } else if (type === 'sepia') {
                data[i] = (r * .393) + (g *.769) + (b * .189);
                data[i+1] = (r * .349) + (g *.686) + (b * .168);
                data[i+2] = (r * .272) + (g *.534) + (b * .131);
            }
        }
        ctx.putImageData(imageData, 0, 0);
    });

    resetEditorBtn.addEventListener('click', () => {
        ctx.drawImage(currentImage, 0, 0);
    });

    downloadEditedBtn.addEventListener('click', () => {
        const link = document.createElement('a');
        link.download = `edited_${Date.now()}.png`;
        link.href = canvas.toDataURL();
        link.click();
    });

    // --- 5. API Counter Widget (Simple Implementation) ---
    function updateCounter(type) {
        let count = parseInt(localStorage.getItem(`api_${type}`) || 0);
        count++;
        localStorage.setItem(`api_${type}`, count);
        renderCounters();
    }
    
    function renderCounters() {
        const widget = document.getElementById('api-counter-widget');
        const gemini = localStorage.getItem('api_gemini') || 0;
        const img = localStorage.getItem('api_imageGen') || 0;
        
        if(gemini > 0 || img > 0) {
            widget.innerHTML = `
                <div style="background: var(--pico-card-background-color); border: 1px solid var(--pico-card-border-color); padding: 0.5rem 1rem; border-radius: 20px; font-size: 0.8em; box-shadow: var(--shadow-md);">
                    <i class="fa-solid fa-bolt" style="color: var(--warning-color);"></i> 
                    Gemini: <b>${gemini}</b> | Gen: <b>${img}</b>
                </div>`;
        }
    }
    renderCounters(); // Init on load
    
    // Init Clipboard
    new ClipboardJS('.copy-btn');
});
// static/script.js
document.addEventListener('DOMContentLoaded', () => {

    // --- Element Selectors ---
    const fileInput = document.getElementById('file');
    const analyzeBtn = document.getElementById('analyze-btn');
    const form = document.getElementById('upload-form');
    const globalLoader = document.getElementById('global-loader-container');
    const errorMessage = document.getElementById('error-message');
    const themeSwitcher = document.getElementById('theme-switcher');

    // --- Result Area Selectors ---
    const resultsSection = document.getElementById('results-section');
    const resultsContainer = document.getElementById('results-container');
    const startOverBtn = document.getElementById('start-over-btn');
    const qaSection = document.getElementById('qa-section');
    const askForm = document.getElementById('ask-form');
    const qaLoader = document.getElementById('qa-loader');
    const answerContainer = document.getElementById('answer-container');
    const qaReferenceImage = document.getElementById('qa-reference-image');
    const questionTextarea = document.getElementById('question'); 
    const suggestionBtns = document.querySelectorAll('.qa-suggestion-btn');

    // --- Upload Area Selectors ---
    const uploadArticle = document.getElementById('upload-article');
    const imagePreview = document.getElementById('image-preview');
    const imagePreviewContainer = document.querySelector('.image-preview-container');
    const fileInputLabel = document.getElementById('file-input-filename');
    const dropZone = document.querySelector('.drop-zone');
    
    // --- SEGMENTATION TOOLBOX SELECTORS ---
    const yoloVisionAnalysisSection = document.getElementById('yolo-vision-analysis');
    const segmentationToolbox = document.getElementById('segmentation-toolbox');
    const yoloPlotsGrid = document.getElementById('yolo-plots-grid');
    const segLoader = document.getElementById('seg-loader');
    const segBtnRemoveBg = document.getElementById('seg-btn-remove-bg');
    const segBtnBlurBg = document.getElementById('seg-btn-blur-bg');
    const segBtnSpotlight = document.getElementById('seg-btn-spotlight');
    const segBtnSmartCrop = document.getElementById('seg-btn-smart-crop');
    const segImageAfterPlaceholder = document.getElementById('seg-image-after-placeholder');
    const segDownloadBtn = document.getElementById('seg-download-btn');
    const segPlotPreview = document.getElementById('seg-plot-preview'); // Plot preview
    
    // --- NEW Selectors for Simple Image Result (REPLACED SLIDER) ---
    const segImageAfterContainer = document.getElementById('seg-image-after-container');
    const segImageAfter = document.getElementById('seg-image-after');
    // --- END OF SELECTORS ---

    let currentFilename = '';
    let selectedFile = null;
    const storageKey = 'analyzerLastAnalysis';
    
    let currentOriginalUrl = '';
    let currentMaskUrl = '';

    // --- Theme Switcher ---
    if (themeSwitcher) { 
        themeSwitcher.addEventListener('change', () => { const theme = themeSwitcher.checked ? 'dark' : 'light'; document.documentElement.setAttribute('data-theme', theme); localStorage.setItem('theme', theme); }); const savedTheme = localStorage.getItem('theme') || 'light'; document.documentElement.setAttribute('data-theme', savedTheme); themeSwitcher.checked = savedTheme === 'dark';
     }

    // --- Drag and Drop ---
    if (dropZone) { 
        dropZone.addEventListener('dragover', (e) => { e.preventDefault(); dropZone.classList.add('drag-over'); }); dropZone.addEventListener('dragleave', () => { dropZone.classList.remove('drag-over'); }); dropZone.addEventListener('drop', (e) => { e.preventDefault(); dropZone.classList.remove('drag-over'); if (e.dataTransfer.files.length > 0) { const file = e.dataTransfer.files[0]; if (file.type.startsWith('image/')) handleFileSelect(file); else alert('Please drop an image file.'); } });
     }

    // --- File Selection ---
    function handleFileSelect(file) { 
        if (!file.type.startsWith('image/')) { alert('Please select an image file.'); return; } selectedFile = file; const previewUrl = URL.createObjectURL(file); imagePreview.src = previewUrl; imagePreviewContainer.classList.remove('hidden'); if (fileInputLabel) fileInputLabel.textContent = file.name; analyzeBtn.disabled = false; const dataTransfer = new DataTransfer(); dataTransfer.items.add(selectedFile); fileInput.files = dataTransfer.files;
     }
    if (fileInput) { fileInput.addEventListener('change', (e) => { if (e.target.files && e.target.files.length > 0) handleFileSelect(e.target.files[0]); }); }

    // --- Start Over ---
    if (startOverBtn) {
         startOverBtn.addEventListener('click', () => { 
            uploadArticle.classList.remove('hidden'); resultsSection.classList.add('hidden'); resultsContainer.classList.add('hidden'); qaSection.classList.add('hidden');
            fileInput.value = ''; if (fileInputLabel) fileInputLabel.textContent = 'No file selected'; imagePreview.src = ''; imagePreviewContainer.classList.add('hidden'); qaReferenceImage.src = ''; 
            currentFilename = ''; selectedFile = null; analyzeBtn.disabled = true; localStorage.removeItem(storageKey);
            
            yoloVisionAnalysisSection.classList.add('hidden');
            segmentationToolbox.classList.add('hidden');
            yoloPlotsGrid.innerHTML = '';
            currentOriginalUrl = '';
            currentMaskUrl = '';
            if (segImageAfterContainer) segImageAfterContainer.classList.add('hidden'); // MODIFIED
         });
    }

    // --- Main Analysis Form Handler ---
    if (form) { form.addEventListener('submit', async (e) => { 
        e.preventDefault(); if (!selectedFile) { alert("Please select a file first."); return; } const formData = new FormData(form); const tasks = formData.getAll('tasks'); if (tasks.length === 0) { alert("Please select at least one analysis task."); return; }
        globalLoader.classList.remove('hidden'); errorMessage.classList.add('hidden'); analyzeBtn.disabled = true;
        try { 
            const response = await fetch('/analyze', { method: 'POST', body: formData }); 
            const data = await response.json(); 
            if (!response.ok) throw new Error(data.error || 'An unknown server error occurred.'); 
            currentFilename = data.filename; 
            localStorage.setItem(storageKey, JSON.stringify(data)); 
            
            currentOriginalUrl = data.original_image_url;
            
            displayResults(data); 
            uploadArticle.classList.add('hidden'); 
            resultsSection.classList.remove('hidden'); 
        } catch (error) { 
            errorMessage.textContent = `Error: ${error.message}`; 
            errorMessage.classList.remove('hidden'); 
            resultsSection.classList.add('hidden'); 
        } finally { 
            globalLoader.classList.add('hidden'); 
            analyzeBtn.disabled = false; 
        }
     }); }

    // --- Follow-up Question Handler ---
    if (askForm) { askForm.addEventListener('submit', async (e) => { 
        e.preventDefault(); const question = questionTextarea.value.trim(); if (!question || !currentFilename) { alert("An image must be analyzed first."); return; } qaLoader.classList.remove('hidden'); answerContainer.classList.add('hidden'); try { const response = await fetch('/ask', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ question, filename: currentFilename }) }); const data = await response.json(); if (data.error) throw new Error(data.error); document.getElementById('answer-text').textContent = data.answer; answerContainer.classList.remove('hidden'); questionTextarea.value = ''; } catch (error) { alert(`Q&A Error: ${error.message}`); } finally { qaLoader.classList.add('hidden'); }
    }); }

    // --- Q&A Suggestion Button Handler ---
    suggestionBtns.forEach(btn => { btn.addEventListener('click', () => { questionTextarea.value = btn.textContent; questionTextarea.focus(); }); });

    // --- Function to Display Full Analysis Results ---
    function displayResults(data) {
        
        // --- 1. Reset all result areas ---
        yoloPlotsGrid.innerHTML = '';
        segmentationToolbox.classList.add('hidden');
        yoloVisionAnalysisSection.classList.add('hidden');
        if (segImageAfterContainer) segImageAfterContainer.classList.add('hidden'); // MODIFIED
        if (segImageAfter) segImageAfter.src = ''; // MODIFIED
        segImageAfterPlaceholder.classList.remove('hidden'); 
        segDownloadBtn.classList.add('hidden');
        if (segPlotPreview) segPlotPreview.src = ''; 
        currentMaskUrl = ''; 

        const geminiContainer = document.getElementById('gemini-results');
        const ocrContainer = document.getElementById('ocr-results');
        const tagsContainer = document.getElementById('tags-results');
        const sdPromptsSection = document.getElementById('gemini-sd-prompts-section');
        const imaggaContainer = document.getElementById('imagga-results');
        const imaggaTagsContent = document.getElementById('imagga-tags-container');

        geminiContainer.classList.add('hidden');
        ocrContainer.classList.add('hidden');
        tagsContainer.classList.add('hidden');
        sdPromptsSection.classList.add('hidden');
        imaggaContainer.classList.add('hidden');
        if (imaggaTagsContent) imaggaTagsContent.innerHTML = '';

        // --- 2. Show main containers & images ---
        resultsContainer.classList.remove('hidden');
        document.getElementById('original-image').src = data.original_image_url;
        qaReferenceImage.src = data.original_image_url; 
        displayMetadata(data.metadata);

        // --- 3. Populate Gemini sections ---
        if (data.results.gemini) {
            const gemini = data.results.gemini;
            document.getElementById('gemini-caption-content').textContent = gemini.caption || 'N/A';
            document.getElementById('gemini-summary-content').textContent = gemini.summary || 'N/A';
            let detailedDescription = gemini.detailed_prompt || 'N/A';
            let sdPrompts = '';
            const promptMarker = '**Stable Diffusion Prompt Suggestions:**';
            const markerIndex = detailedDescription.indexOf(promptMarker);
            if (markerIndex !== -1) {
                sdPrompts = detailedDescription.substring(markerIndex + promptMarker.length).trim();
                detailedDescription = detailedDescription.substring(0, markerIndex).trim();
                sdPrompts = sdPrompts.replace(/^\s*[\*\-]\s*/gm, ''); 
            }
            document.getElementById('gemini-detailed-description-content').textContent = detailedDescription; 
            if (sdPrompts) {
                 document.getElementById('gemini-sd-prompts-content').textContent = sdPrompts; 
                 sdPromptsSection.classList.remove('hidden'); 
            }
            document.getElementById('gemini-social-post-content').textContent = gemini.social_post || 'N/A';
            const hiddenDetailsEl = document.getElementById('gemini-hidden-details-content');
            hiddenDetailsEl.innerHTML = ''; 
            if (gemini.hidden_details && gemini.hidden_details !== 'No specific hidden details noted.') { 
                const detailsList = gemini.hidden_details.split('\n').map(item => item.trim().replace(/^\* /, '')).filter(Boolean); if(detailsList.length > 0) { const ul = document.createElement('ul'); ul.style.paddingLeft = '1.5rem'; detailsList.forEach(detail => { const li = document.createElement('li'); li.textContent = detail; ul.appendChild(li); }); hiddenDetailsEl.appendChild(ul); } else { hiddenDetailsEl.textContent = gemini.hidden_details; }
             } else { hiddenDetailsEl.textContent = 'No specific hidden details noted.'; }
            geminiContainer.classList.remove('hidden');
        }

        // --- 4. Populate Combined Tags ---
        if (data.tags && data.tags.length > 0) { 
            const tagsContent = document.getElementById('tags-container'); 
            tagsContent.innerHTML = ''; 
            data.tags.forEach(tag => { 
                const tagElement = document.createElement('span'); 
                tagElement.className = 'tag'; 
                tagElement.textContent = tag; 
                tagsContent.appendChild(tagElement); 
            }); 
            tagsContainer.classList.remove('hidden'); 
        }
        
        // --- 5. Populate Imagga Tags ---
        if (data.results.imagga && data.results.imagga.length > 0) {
            data.results.imagga.forEach(tag => {
                const tagElement = document.createElement('span');
                tagElement.className = 'tag tag-imagga'; 
                tagElement.textContent = `${tag.name} (${tag.confidence}%)`;
                imaggaTagsContent.appendChild(tagElement);
            });
            imaggaContainer.classList.remove('hidden');
        }

        // --- 6. Populate OCR ---
        if (data.results.ocr) { document.getElementById('ocr-text-content').textContent = data.results.ocr; ocrContainer.classList.remove('hidden'); }

        // --- 7. Populate YOLO Vision Analysis ---
        if (data.results.yolo) {
            let yoloTaskFound = false;
            
            for (const task in data.results.yolo) {
                const result = data.results.yolo[task];
                
                if (result.type === 'segmentation_data') {
                    currentMaskUrl = result.mask_url; 
                    if(segPlotPreview) segPlotPreview.src = result.plot_url; 
                    segmentationToolbox.classList.remove('hidden');
                    yoloTaskFound = true;
                
                } else if (result.type === 'annotated_image') {
                    // (Pose, etc.)
                    const card = document.createElement('article'); 
                    card.className = 'yolo-card'; 
                    let content = `<h4>YOLOv8: ${task.charAt(0).toUpperCase() + task.slice(1)}</h4>`;
                    content += `<img src="${result.processed_image_url}" alt="Processed for ${task}" class="zoomable">`;
                    card.innerHTML = content; 
                    yoloPlotsGrid.appendChild(card);
                    yoloTaskFound = true;
                
                } else if (result.type === 'classification') {
                    // (Classification)
                    const card = document.createElement('article'); 
                    card.className = 'yolo-card'; 
                    let content = `<h4>YOLOv8: ${task.charAt(0).toUpperCase() + task.slice(1)}</h4>`;
                    content += `<p><strong>Class:</strong> ${result.class_name}</p><p><strong>Confidence:</strong> ${result.confidence}</p>`;
                    card.innerHTML = content; 
                    yoloPlotsGrid.appendChild(card);
                    yoloTaskFound = true;
                }
            }
            
            if (yoloTaskFound) {
                yoloVisionAnalysisSection.classList.remove('hidden');
            }
        }

        // --- 8. Show Q&A section ---
        qaSection.classList.remove('hidden');
        questionTextarea.value = '';
        answerContainer.classList.add('hidden');
        document.getElementById('answer-text').textContent = '';
    }

    // --- Helper for metadata (unchanged) ---
    function displayMetadata(metadata) { 
        const metadataContainer = document.getElementById('metadata-content'); metadataContainer.innerHTML = ''; if (metadata) { for (const sectionTitle in metadata) { const section = metadata[sectionTitle]; const titleElement = document.createElement('h6'); titleElement.textContent = sectionTitle; metadataContainer.appendChild(titleElement); const listElement = document.createElement('ul'); listElement.className = 'metadata-list'; for (const key in section) { const listItem = document.createElement('li'); listItem.innerHTML = `<strong>${key}:</strong> ${section[key]}`; listElement.appendChild(listItem); } metadataContainer.appendChild(listElement); } }
     }

    // --- Load Saved Results ---
    const savedData = localStorage.getItem(storageKey);
    if (savedData) {
        try {
            const data = JSON.parse(savedData);
            currentFilename = data.filename;
            currentOriginalUrl = data.original_image_url; 
            selectedFile = { name: data.metadata?.["File Properties"]?.Filename || "unknown file" };
            if (fileInputLabel) fileInputLabel.textContent = selectedFile.name;
            analyzeBtn.disabled = false;
            uploadArticle.classList.add('hidden');
            resultsSection.classList.remove('hidden');
            displayResults(data);
        } catch (e) { console.error("Could not parse saved data.", e); localStorage.removeItem(storageKey); }
    }

    // --- Global Zoom Logic (unchanged) ---
    const zoomModal = document.getElementById('zoom-modal-backdrop');
    const zoomImg = document.getElementById('zoom-modal-img');
    document.addEventListener('click', (e) => { 
        const zoomableTarget = e.target.closest('.zoomable'); if (zoomableTarget) { zoomImg.src = zoomableTarget.src; zoomModal.classList.remove('hidden'); } if (e.target.id === 'zoom-modal-backdrop') { zoomModal.classList.add('hidden'); zoomImg.src = ''; }
     });

    // --- Initialize ClipboardJS ---
    const clipboard = new ClipboardJS('.copy-btn');
    clipboard.on('success', function(e) { 
        const originalIcon = e.trigger.innerHTML; e.trigger.innerHTML = '<i class="fa-solid fa-check"></i>'; e.trigger.classList.add('copied'); setTimeout(() => { e.trigger.innerHTML = originalIcon; e.trigger.classList.remove('copied'); }, 1500); e.clearSelection();
     });
    clipboard.on('error', function(e) { console.error('ClipboardJS error:', e); alert('Failed to copy text.'); });
    
    
    // --- vvvv THIS IS THE MODIFIED FUNCTION vvvv ---
    async function performAdvancedEdit(effectType) {
        if (!currentOriginalUrl || !currentMaskUrl) {
            alert("Error: Original image or mask URL is missing. Please re-run analysis.");
            return;
        }

        segLoader.classList.remove('hidden');
        errorMessage.classList.add('hidden');
        if (segImageAfterContainer) segImageAfterContainer.classList.add('hidden'); // MODIFIED
        segImageAfterPlaceholder.classList.remove('hidden'); 
        
        [segBtnRemoveBg, segBtnBlurBg, segBtnSpotlight, segBtnSmartCrop].forEach(btn => btn.disabled = true);

        let endpoint = '';
        switch(effectType) {
            case 'remove-bg': endpoint = '/edit/remove-bg'; break;
            case 'blur-bg': endpoint = '/edit/blur-bg'; break;
            case 'spotlight': endpoint = '/edit/spotlight'; break;
            case 'smart-crop': endpoint = '/edit/smart-crop'; break;
            default:
                alert('Unknown effect type.');
                segLoader.classList.add('hidden'); // Stop loader on error
                [segBtnRemoveBg, segBtnBlurBg, segBtnSpotlight, segBtnSmartCrop].forEach(btn => btn.disabled = false);
                return;
        }

        try {
            const response = await fetch(endpoint, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    original_url: currentOriginalUrl,
                    mask_url: currentMaskUrl
                })
            });

            const data = await response.json();
            if (!response.ok) {
                throw new Error(data.error || 'Failed to apply effect.');
            }
            
            // --- vvvv THIS IS THE FIX & MODIFICATION vvvv ---
            // This adds a unique timestamp to the URL (e.g., ?t=123456789)
            // It forces the browser to download the new image
            // instead of showing the old one from its cache.
            const cacheBuster = '?t=' + new Date().getTime();

            // Success! Populate the simple image result
            segImageAfter.src = data.processed_image_url + cacheBuster; // Add cache-buster
            
            segImageAfterPlaceholder.classList.add('hidden');
            segImageAfterContainer.classList.remove('hidden'); // Show the new container
            
            segDownloadBtn.href = data.processed_image_url + cacheBuster; // Add cache-buster
            segDownloadBtn.download = data.filename;
            segDownloadBtn.classList.remove('hidden');
            // --- ^^^^ END OF FIX & MODIFICATION ^^^^ ---

        } catch (error) {
            errorMessage.textContent = `Error: ${error.message}`;
            errorMessage.classList.remove('hidden');
        } finally {
            segLoader.classList.add('hidden');
            [segBtnRemoveBg, segBtnBlurBg, segBtnSpotlight, segBtnSmartCrop].forEach(btn => btn.disabled = false);
        }
    }
    
    // --- SLIDER LOGIC (REMOVED) ---
    
    // --- EVENT LISTENERS FOR TOOLBOX BUTTONS (Unchanged) ---
    if (segBtnRemoveBg) {
        segBtnRemoveBg.addEventListener('click', () => performAdvancedEdit('remove-bg'));
    }
    if (segBtnBlurBg) {
        segBtnBlurBg.addEventListener('click', () => performAdvancedEdit('blur-bg'));
    }
    if (segBtnSpotlight) {
        segBtnSpotlight.addEventListener('click', () => performAdvancedEdit('spotlight'));
    }
    if (segBtnSmartCrop) {
        segBtnSmartCrop.addEventListener('click', () => performAdvancedEdit('smart-crop'));
    }
    // --- END OF EVENT LISTENERS ---

});
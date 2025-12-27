// static/analyzer.js
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
    const preCropBtn = document.getElementById('pre-crop-btn'); // NEW BUTTON
    
    // --- SEGMENTATION TOOLBOX SELECTORS ---
    const yoloVisionAnalysisSection = document.getElementById('yolo-vision-analysis');
    const segmentationToolbox = document.getElementById('segmentation-toolbox');
    const yoloPlotsGrid = document.getElementById('yolo-plots-grid');
    const segLoader = document.getElementById('seg-loader');
    
    // Toolbox Buttons
    const segBtnRemoveBg = document.getElementById('seg-btn-remove-bg');
    const segBtnBlurBg = document.getElementById('seg-btn-blur-bg');
    const segBtnSpotlight = document.getElementById('seg-btn-spotlight');
    const segBtnSmartCrop = document.getElementById('seg-btn-smart-crop');
    
    // Results & Preview Elements
    const segImageAfterPlaceholder = document.getElementById('seg-image-after-placeholder');
    const segDownloadBtn = document.getElementById('seg-download-btn');
    const segPlotPreview = document.getElementById('seg-plot-preview');
    const segResultImage = document.getElementById('seg-result-image');
    
    // --- Effect Settings ---
    const effectSettings = document.getElementById('effect-settings');
    const intensitySlider = document.getElementById('effect-intensity');
    const intensityValue = document.getElementById('intensity-value');
    const applyEffectBtn = document.getElementById('apply-effect-btn');
    
    const comparisonWrapper = document.getElementById('comparison-wrapper');
    const sliderBefore = document.getElementById('slider-before');
    const sliderAfter = document.getElementById('slider-after');
    const sliderOverlay = document.querySelector('.slider-image-overlay');
    const sliderDivider = document.querySelector('.slider-divider');

    // --- YOLO Detection Counts ---
    const yoloDetectionResults = document.getElementById('yolo-detection-results');
    const yoloCountContainer = document.getElementById('yolo-count-container');

    // --- MANUAL CROP SELECTORS ---
    const manualCropTrigger = document.getElementById('manual-crop-trigger');
    const cropModal = document.getElementById('crop-modal-backdrop');
    const cropModalImg = document.getElementById('crop-modal-img');
    const cropCancelBtn = document.getElementById('crop-cancel-btn');
    const cropApplyBtn = document.getElementById('crop-apply-btn');

    // --- State Variables ---
    let currentFilename = '';
    let selectedFile = null; // IMPORTANT: This holds the file (original or cropped) to be analyzed
    const storageKey = 'analyzerLastAnalysis';
    let cropperInstance = null;
    let isPreCrop = false; // Flag to know if we are cropping BEFORE or AFTER analysis
    
    let currentOriginalUrl = '';
    let currentMaskUrl = '';
    let currentEffect = null; 

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

    // --- Drag and Drop ---
    if (dropZone) { 
        dropZone.addEventListener('dragover', (e) => { e.preventDefault(); dropZone.classList.add('drag-over'); }); 
        dropZone.addEventListener('dragleave', () => { dropZone.classList.remove('drag-over'); }); 
        dropZone.addEventListener('drop', (e) => { 
            e.preventDefault(); 
            dropZone.classList.remove('drag-over'); 
            if (e.dataTransfer.files.length > 0) { 
                const file = e.dataTransfer.files[0]; 
                if (file.type.startsWith('image/')) handleFileSelect(file); 
                else alert('Please drop an image file.'); 
            } 
        });
    }

    // --- File Selection ---
    function handleFileSelect(file) { 
        if (!file.type.startsWith('image/')) { alert('Please select an image file.'); return; } 
        selectedFile = file; 
        const previewUrl = URL.createObjectURL(file); 
        imagePreview.src = previewUrl; 
        imagePreviewContainer.classList.remove('hidden'); 
        if (fileInputLabel) fileInputLabel.textContent = file.name; 
        analyzeBtn.disabled = false; 
        
        // We do NOT set fileInput.files here because we might send a cropped blob later
    }
    if (fileInput) { 
        fileInput.addEventListener('change', (e) => { 
            if (e.target.files && e.target.files.length > 0) handleFileSelect(e.target.files[0]); 
        }); 
    }

    // --- Start Over ---
    if (startOverBtn) {
         startOverBtn.addEventListener('click', () => { 
            uploadArticle.classList.remove('hidden'); 
            resultsSection.classList.add('hidden'); 
            resultsContainer.classList.add('hidden'); 
            qaSection.classList.add('hidden');
            fileInput.value = ''; 
            if (fileInputLabel) fileInputLabel.textContent = 'No file selected'; 
            imagePreview.src = ''; 
            imagePreviewContainer.classList.add('hidden'); 
            qaReferenceImage.src = ''; 
            currentFilename = ''; 
            selectedFile = null; 
            analyzeBtn.disabled = true; 
            localStorage.removeItem(storageKey);
            
            yoloVisionAnalysisSection.classList.add('hidden');
            segmentationToolbox.classList.add('hidden');
            yoloPlotsGrid.innerHTML = '';
            yoloDetectionResults.classList.add('hidden');
            yoloCountContainer.innerHTML = '';
            
            currentOriginalUrl = '';
            currentMaskUrl = '';
            resetToolboxUI();
         });
    }
    
    function resetToolboxUI() {
        segResultImage.classList.add('hidden'); 
        segResultImage.src = '';
        comparisonWrapper.classList.add('hidden');
        segImageAfterPlaceholder.classList.remove('hidden'); 
        segDownloadBtn.classList.add('hidden');
        effectSettings.classList.add('hidden');
        if (segPlotPreview) segPlotPreview.src = ''; 
        document.querySelectorAll('.seg-tool-btn').forEach(b => b.classList.add('outline'));
    }

    // --- Shared Analysis Logic ---
    async function performAnalysis(formData) {
        globalLoader.classList.remove('hidden'); 
        errorMessage.classList.add('hidden'); 
        analyzeBtn.disabled = true;
        
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
            
            // Scroll to top
            window.scrollTo({ top: 0, behavior: 'smooth' });

        } catch (error) { 
            errorMessage.textContent = `Error: ${error.message}`; 
            errorMessage.classList.remove('hidden'); 
            resultsSection.classList.add('hidden'); 
        } finally { 
            globalLoader.classList.add('hidden'); 
            analyzeBtn.disabled = false; 
        }
    }

    // --- Main Analysis Form Handler ---
    if (form) { 
        form.addEventListener('submit', async (e) => { 
            e.preventDefault(); 
            if (!selectedFile) { alert("Please select a file first."); return; } 
            
            // Construct FormData manually to support potential Blob (cropped image)
            const formData = new FormData();
            
            // Append the file (either original File or cropped Blob)
            // If it's a blob, we give it a name
            const fileName = selectedFile.name || 'cropped_image.jpg';
            formData.append('file', selectedFile, fileName);
            
            // Append checked tasks
            const taskCheckboxes = document.querySelectorAll('input[name="tasks"]:checked');
            taskCheckboxes.forEach(cb => formData.append('tasks', cb.value));
            
            if (taskCheckboxes.length === 0) { alert("Please select at least one analysis task."); return; }
            
            performAnalysis(formData);
        }); 
    }

    // --- CROPPER & MANUAL LABELING LOGIC ---

    // 1. Trigger from "Pre-Analysis" (Upload Screen)
    if (preCropBtn) {
        preCropBtn.addEventListener('click', () => {
            if (!selectedFile) return;
            isPreCrop = true; 
            const reader = new FileReader();
            reader.onload = (e) => {
                cropModalImg.src = e.target.result;
                cropModal.classList.remove('hidden');
                initCropper();
            };
            reader.readAsDataURL(selectedFile);
        });
    }

    // 2. Trigger from "Post-Analysis" (Result Screen)
    if (manualCropTrigger) {
        manualCropTrigger.addEventListener('click', () => {
            if (!currentOriginalUrl) return;
            isPreCrop = false;
            cropModalImg.src = currentOriginalUrl;
            cropModal.classList.remove('hidden');
            initCropper();
        });
    }

    function initCropper() {
        if (cropperInstance) cropperInstance.destroy();
        cropperInstance = new Cropper(cropModalImg, {
            viewMode: 1,
            autoCropArea: 0.5,
            background: false 
        });
    }

    // Cancel Button
    if (cropCancelBtn) {
        cropCancelBtn.addEventListener('click', () => {
            cropModal.classList.add('hidden');
            if (cropperInstance) { cropperInstance.destroy(); cropperInstance = null; }
        });
    }

    // Button A: Analyze Selection (AI Focus)
    if (cropApplyBtn) {
        cropApplyBtn.addEventListener('click', () => {
            if (!cropperInstance) return;
            cropModal.classList.add('hidden');
            
            cropperInstance.getCroppedCanvas().toBlob((blob) => {
                if (isPreCrop) {
                    selectedFile = blob;
                    imagePreview.src = URL.createObjectURL(blob);
                    if (fileInputLabel) fileInputLabel.textContent += " (Cropped)";
                } else {
                    const formData = new FormData();
                    formData.append('file', blob, 'manual_focus.jpg');
                    const taskCheckboxes = document.querySelectorAll('input[name="tasks"]:checked');
                    taskCheckboxes.forEach(cb => formData.append('tasks', cb.value));
                    performAnalysis(formData);
                }
                cropperInstance.destroy(); cropperInstance = null;
            }, 'image/jpeg');
        });
    }

    // Button B: Label Selection (Manual Visual Box) -- NEW FEATURE
    const cropLabelBtn = document.getElementById('crop-label-btn');
    if (cropLabelBtn) {
        cropLabelBtn.addEventListener('click', async () => {
            if (!cropperInstance || isPreCrop) {
                alert("Please analyze the image first before adding manual labels.");
                return;
            }

            const labelName = prompt("Enter the name for this object:");
            if (!labelName) return;

            // 1. Get Coordinates from Cropper
            const cropData = cropperInstance.getData(); // x, y, width, height (natural size)
            const imageData = cropperInstance.getImageData(); // Display size info

            // 2. Close Modal
            cropModal.classList.add('hidden');
            cropperInstance.destroy(); cropperInstance = null;

            // 3. Draw Box on UI (Visual)
            // We need to map "natural" image coordinates to the "displayed" image size
            const originalImage = document.getElementById('original-image');
            const wrapper = document.getElementById('original-image-wrapper');
            
            // Calculate scaling factor
            const scaleX = originalImage.clientWidth / originalImage.naturalWidth;
            const scaleY = originalImage.clientHeight / originalImage.naturalHeight;

            const box = document.createElement('div');
            box.className = 'manual-box';
            box.style.position = 'absolute';
            box.style.border = '2px solid #ff0000'; // Red box
            box.style.backgroundColor = 'rgba(255, 0, 0, 0.1)';
            box.style.color = 'white';
            box.style.fontWeight = 'bold';
            box.style.fontSize = '12px';
            box.style.padding = '2px';
            box.innerText = labelName;
            
            // Position
            box.style.left = (cropData.x * scaleX) + 'px';
            box.style.top = (cropData.y * scaleY) + 'px';
            box.style.width = (cropData.width * scaleX) + 'px';
            box.style.height = (cropData.height * scaleY) + 'px';
            
            wrapper.appendChild(box);

            // 4. Add Text Tag to List (UI)
            const tagsContainer = document.getElementById('tags-container');
            const tagElement = document.createElement('span'); 
            tagElement.className = 'tag'; 
            tagElement.textContent = labelName; 
            tagElement.style.border = '1px solid #ff0000'; 
            tagsContainer.appendChild(tagElement);
            if(tagsContainer.parentElement.classList.contains('hidden')) {
                tagsContainer.parentElement.classList.remove('hidden');
            }

            // 5. Save Tag to Backend (DB)
            try {
                await fetch('/add_custom_tag', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ tag: labelName, filename: currentFilename })
                });
            } catch (e) { console.error("Failed to save tag", e); }
        });
    }


    // --- Follow-up Question Handler ---
    if (askForm) { 
        askForm.addEventListener('submit', async (e) => { 
            e.preventDefault(); 
            const question = questionTextarea.value.trim(); 
            if (!question || !currentFilename) { alert("An image must be analyzed first."); return; } 
            qaLoader.classList.remove('hidden'); 
            answerContainer.classList.add('hidden'); 
            try { 
                const response = await fetch('/ask', { 
                    method: 'POST', 
                    headers: { 'Content-Type': 'application/json' }, 
                    body: JSON.stringify({ question, filename: currentFilename }) 
                }); 
                const data = await response.json(); 
                if (data.error) throw new Error(data.error); 
                document.getElementById('answer-text').textContent = data.answer; 
                answerContainer.classList.remove('hidden'); 
                questionTextarea.value = ''; 
            } catch (error) { 
                alert(`Q&A Error: ${error.message}`); 
            } finally { 
                qaLoader.classList.add('hidden'); 
            }
        }); 
    }

    suggestionBtns.forEach(btn => { 
        btn.addEventListener('click', () => { 
            questionTextarea.value = btn.textContent; 
            questionTextarea.focus(); 
        }); 
    });

    // --- Function to Display Full Analysis Results ---
    function displayResults(data) {
        // 1. Reset
        yoloPlotsGrid.innerHTML = '';
        segmentationToolbox.classList.add('hidden');
        yoloVisionAnalysisSection.classList.add('hidden');
        resetToolboxUI();
        currentMaskUrl = ''; 
        yoloDetectionResults.classList.add('hidden');
        yoloCountContainer.innerHTML = '';

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

        // 2. Show containers
        resultsContainer.classList.remove('hidden');
        document.getElementById('original-image').src = data.original_image_url;
        qaReferenceImage.src = data.original_image_url; 
        displayMetadata(data.metadata);

        // 3. Populate Gemini
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
                const detailsList = gemini.hidden_details.split('\n').map(item => item.trim().replace(/^\* /, '')).filter(Boolean); 
                if(detailsList.length > 0) { 
                    const ul = document.createElement('ul'); 
                    ul.style.paddingLeft = '1.5rem'; 
                    detailsList.forEach(detail => { 
                        const li = document.createElement('li'); 
                        li.textContent = detail; 
                        ul.appendChild(li); 
                    }); 
                    hiddenDetailsEl.appendChild(ul); 
                } else { 
                    hiddenDetailsEl.textContent = gemini.hidden_details; 
                }
             } else { 
                hiddenDetailsEl.textContent = 'No specific hidden details noted.'; 
            }
            geminiContainer.classList.remove('hidden');
        }

        // 4. Combined Tags
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
        
        // 5. Imagga Tags
        if (data.results.imagga && data.results.imagga.length > 0) {
            imaggaTagsContent.className = 'bar-chart-container'; 
            data.results.imagga.forEach(tag => {
                const row = document.createElement('div');
                row.className = 'bar-chart-row';
                const label = document.createElement('span');
                label.className = 'bar-chart-label';
                label.textContent = tag.name;
                const barContainer = document.createElement('div');
                barContainer.className = 'bar-chart-bar-container';
                const bar = document.createElement('div');
                bar.className = 'bar-chart-bar';
                bar.style.width = `${tag.confidence}%`; 
                const percent = document.createElement('span');
                percent.className = 'bar-chart-percent';
                percent.textContent = `${tag.confidence}%`;

                barContainer.appendChild(bar);
                row.appendChild(label);
                row.appendChild(barContainer);
                row.appendChild(percent);
                imaggaTagsContent.appendChild(row);
            });
            imaggaContainer.classList.remove('hidden');
        }

        // 6. OCR
        if (data.results.ocr) {
            const ocr = data.results.ocr;
            document.getElementById('ocr-annotated-image').src = ocr.annotated_image_url;
            document.getElementById('ocr-text-content').textContent = ocr.extracted_text;
            
            const listContainer = document.getElementById('ocr-detections-list');
            listContainer.innerHTML = ''; 
            if (ocr.detections && Array.isArray(ocr.detections)) {
                ocr.detections.forEach(text => {
                    const itemDiv = document.createElement('div');
                    itemDiv.className = 'ocr-item';
                    const textSpan = document.createElement('span');
                    textSpan.className = 'ocr-item-text';
                    textSpan.textContent = text;
                    textSpan.title = text; 
                    const copyBtn = document.createElement('button');
                    copyBtn.className = 'ocr-copy-btn-small';
                    copyBtn.innerHTML = '<i class="fa-regular fa-copy"></i>';
                    copyBtn.type = 'button';
                    copyBtn.addEventListener('click', () => {
                        navigator.clipboard.writeText(text).then(() => {
                            const originalIcon = copyBtn.innerHTML;
                            copyBtn.innerHTML = '<i class="fa-solid fa-check"></i>';
                            copyBtn.style.color = 'var(--success-color)';
                            copyBtn.style.borderColor = 'var(--success-color)';
                            setTimeout(() => {
                                copyBtn.innerHTML = originalIcon;
                                copyBtn.style.color = '';
                                copyBtn.style.borderColor = '';
                            }, 1500);
                        });
                    });
                    itemDiv.appendChild(textSpan);
                    itemDiv.appendChild(copyBtn);
                    listContainer.appendChild(itemDiv);
                });
            }
            ocrContainer.classList.remove('hidden');
        }

        // 7. YOLO
        if (data.results.yolo) {
            let yoloTaskFound = false;
            for (const task in data.results.yolo) {
                const result = data.results.yolo[task];
                
                if (result.type === 'segmentation_data') {
                    currentMaskUrl = result.mask_url; 
                    if(segPlotPreview) segPlotPreview.src = result.plot_url; 
                    segmentationToolbox.classList.remove('hidden');
                    yoloTaskFound = true;
                
                } else if (task === 'detection' && result.type === 'annotated_image') {
                    if (result.detection_counts && result.total_objects > 0) {
                        const totalElement = document.createElement('p');
                        totalElement.className = 'yolo-count-total';
                        totalElement.textContent = `Total Objects Detected: ${result.total_objects}`;
                        yoloCountContainer.appendChild(totalElement);
                        const sortedCounts = Object.entries(result.detection_counts).sort(([,a],[,b]) => b - a);
                        for (const [name, count] of sortedCounts) {
                            const countElement = document.createElement('span');
                            countElement.className = 'yolo-count-item';
                            countElement.textContent = `${name} (${count})`;
                            yoloCountContainer.appendChild(countElement);
                        }
                        yoloDetectionResults.classList.remove('hidden');
                    }
                    const card = document.createElement('article'); 
                    card.className = 'yolo-card'; 
                    let content = `<h4>YOLOv8: Detection Plot</h4>`;
                    content += `<img src="${result.processed_image_url}" alt="Processed for ${task}" class="zoomable">`;
                    card.innerHTML = content; 
                    yoloPlotsGrid.appendChild(card);
                    yoloTaskFound = true;
                
                } else if (result.type === 'annotated_image') { 
                    const card = document.createElement('article'); 
                    card.className = 'yolo-card'; 
                    let content = `<h4>YOLOv8: ${task.charAt(0).toUpperCase() + task.slice(1)}</h4>`;
                    content += `<img src="${result.processed_image_url}" alt="Processed for ${task}" class="zoomable">`;
                    card.innerHTML = content; 
                    yoloPlotsGrid.appendChild(card);
                    yoloTaskFound = true;
                } else if (result.type === 'classification') {
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

        // 8. Q&A
        qaSection.classList.remove('hidden');
        questionTextarea.value = '';
        answerContainer.classList.add('hidden');
        document.getElementById('answer-text').textContent = '';
    }

    // --- Helper for metadata ---
    function displayMetadata(metadata) { 
        const metadataCard = document.getElementById('metadata-result-card');
        const metadataContainer = document.getElementById('metadata-content');
        const mapContainer = document.getElementById('map-container');
        
        metadataContainer.innerHTML = '';
        mapContainer.innerHTML = '';
        mapContainer.classList.add('hidden');

        if (metadata && Object.keys(metadata).length > 0) {
            if (metadataCard) metadataCard.classList.remove('hidden');

            for (const sectionTitle in metadata) {
                if (sectionTitle === 'gps_info') continue;
                const section = metadata[sectionTitle]; 
                const titleElement = document.createElement('h6'); 
                titleElement.textContent = sectionTitle; 
                metadataContainer.appendChild(titleElement); 
                const listElement = document.createElement('ul'); 
                listElement.className = 'metadata-list'; 
                for (const key in section) { 
                    const listItem = document.createElement('li'); 
                    listItem.innerHTML = `<strong>${key}:</strong> ${section[key]}`; 
                    listElement.appendChild(listItem); 
                } 
                metadataContainer.appendChild(listElement); 
            } 
            
            if (metadata.gps_info && metadata.gps_info.latitude && metadata.gps_info.longitude) {
                const lat = metadata.gps_info.latitude;
                const lng = metadata.gps_info.longitude;
                const mapUrl = `https://maps.google.com/maps?q=${lat},${lng}&t=&z=15&ie=UTF8&iwloc=&output=embed`;
                mapContainer.innerHTML = `<iframe width="100%" height="300" src="${mapUrl}" frameborder="0" scrolling="no" marginheight="0" marginwidth="0" style="border:0; border-radius: var(--border-radius-lg);"></iframe>`;
                mapContainer.classList.remove('hidden');
            }
        } else {
            if (metadataCard) metadataCard.classList.add('hidden');
        }
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
        } catch (e) { 
            console.error("Could not parse saved data.", e); 
            localStorage.removeItem(storageKey); 
        }
    }

    // --- Global Zoom Logic ---
    const zoomModal = document.getElementById('zoom-modal-backdrop');
    const zoomImg = document.getElementById('zoom-modal-img');
    document.addEventListener('click', (e) => { 
        const zoomableTarget = e.target.closest('.zoomable'); 
        if (zoomableTarget) { 
            zoomImg.src = zoomableTarget.src; 
            zoomModal.classList.remove('hidden'); 
        } 
        if (e.target.id === 'zoom-modal-backdrop') { 
            zoomModal.classList.add('hidden'); 
            zoomImg.src = ''; 
        }
     });

    // --- ClipboardJS ---
    const clipboard = new ClipboardJS('.copy-btn, .copy-btn-mini');
    clipboard.on('success', function(e) { 
        const originalIcon = e.trigger.innerHTML; 
        e.trigger.innerHTML = '<i class="fa-solid fa-check"></i>'; 
        e.trigger.classList.add('copied'); 
        setTimeout(() => { e.trigger.innerHTML = originalIcon; e.trigger.classList.remove('copied'); }, 1500); 
        e.clearSelection();
     });
    clipboard.on('error', function(e) { console.error('ClipboardJS error:', e); alert('Failed to copy text.'); });
    
    // --- MAGIC TOOLBOX INTERACTION LOGIC (REVERT1) ---

    // 1. Slider Value Display
    if(intensitySlider) {
        intensitySlider.addEventListener('input', (e) => {
            intensityValue.textContent = e.target.value;
        });
    }

    // 2. Effect Selection UI
    window.selectEffect = function(effect) {
        currentEffect = effect;
        effectSettings.classList.remove('hidden');
        document.querySelectorAll('.seg-tool-btn').forEach(b => b.classList.add('outline'));
        if(effect === 'blur') segBtnBlurBg.classList.remove('outline');
        if(effect === 'spotlight') segBtnSpotlight.classList.remove('outline');
    }

    // 3. Apply Button Handler
    if(applyEffectBtn) {
        applyEffectBtn.addEventListener('click', () => {
            if(currentEffect === 'blur') performAdvancedEdit('blur-bg');
            if(currentEffect === 'spotlight') performAdvancedEdit('spotlight');
        });
    }

    // 4. One-Click Button Handlers
    if (segBtnRemoveBg) {
        segBtnRemoveBg.addEventListener('click', () => {
             document.querySelectorAll('.seg-tool-btn').forEach(b => b.classList.add('outline'));
             segBtnRemoveBg.classList.remove('outline');
             effectSettings.classList.add('hidden'); 
             performAdvancedEdit('remove-bg');
        });
    }
    if (segBtnSmartCrop) {
        segBtnSmartCrop.addEventListener('click', () => {
             document.querySelectorAll('.seg-tool-btn').forEach(b => b.classList.add('outline'));
             segBtnSmartCrop.classList.remove('outline');
             effectSettings.classList.add('hidden'); 
             performAdvancedEdit('smart-crop');
        });
    }

    // 5. Main Edit Function (Clean Revert1 Version)
    async function performAdvancedEdit(effectType) {
        if (!currentOriginalUrl) {
            showToast("Error: Original image missing.", "error");
            return;
        }

        segLoader.classList.remove('hidden');
        errorMessage.classList.add('hidden');
        
        // Disable buttons
        [segBtnRemoveBg, segBtnBlurBg, segBtnSpotlight, segBtnSmartCrop, applyEffectBtn].forEach(btn => {
            if(btn) btn.disabled = true;
        });

        let endpoint = '';
        let successMessage = 'Effect Applied!';
        switch(effectType) {
            case 'remove-bg': endpoint = '/edit/remove-bg'; successMessage = 'Background Removed!'; break;
            case 'blur-bg': endpoint = '/edit/blur-bg'; successMessage = 'Background Blurred!'; break;
            case 'spotlight': endpoint = '/edit/spotlight'; successMessage = 'Spotlight Applied!'; break;
            case 'smart-crop': endpoint = '/edit/smart-crop'; successMessage = 'Smart Crop Complete!'; break;
            default: showToast('Unknown effect.', 'error'); return;
        }
        
        const intensity = intensitySlider ? parseInt(intensitySlider.value) : 50;

        try {
            const response = await fetch(endpoint, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    original_url: currentOriginalUrl,
                    mask_url: currentMaskUrl, // Kept for compatibility, though mostly unused now
                    intensity: intensity 
                    // Note: No bg_color is sent here
                })
            });

            const data = await response.json();
            if (!response.ok) throw new Error(data.error || 'Failed to apply effect.');
            
            const cacheBuster = '?t=' + new Date().getTime();

            // Display Logic
            if (effectType === 'remove-bg' || effectType === 'smart-crop') {
                comparisonWrapper.classList.add('hidden');
                segResultImage.src = data.processed_image_url + cacheBuster;
                segResultImage.classList.remove('hidden');
                segImageAfterPlaceholder.classList.add('hidden');
            } else {
                segResultImage.classList.add('hidden');
                comparisonWrapper.classList.remove('hidden');
                segImageAfterPlaceholder.classList.add('hidden');
                sliderBefore.src = currentOriginalUrl;
                sliderAfter.src = data.processed_image_url + cacheBuster;
                setupComparisonSlider();
            }
            
            segDownloadBtn.href = data.processed_image_url + cacheBuster;
            segDownloadBtn.download = data.filename;
            segDownloadBtn.classList.remove('hidden');
            
            showToast(successMessage, 'success');

        } catch (error) {
            errorMessage.textContent = `Error: ${error.message}`;
            errorMessage.classList.remove('hidden');
            showToast(`Error: ${error.message}`, 'error');
        } finally {
            segLoader.classList.add('hidden');
            [segBtnRemoveBg, segBtnBlurBg, segBtnSpotlight, segBtnSmartCrop, applyEffectBtn].forEach(btn => {
                if(btn) btn.disabled = false;
            });
        }
    }

    // 6. Comparison Slider Logic
    function setupComparisonSlider() {
        if(!comparisonWrapper) return;
        
        let isDragging = false;
        
        const onMove = (clientX) => {
            const rect = comparisonWrapper.getBoundingClientRect();
            let x = clientX - rect.left;
            let percent = (x / rect.width) * 100;
            percent = Math.max(0, Math.min(100, percent));
            
            if(sliderOverlay) sliderOverlay.style.clipPath = `inset(0 ${100 - percent}% 0 0)`;
            if(sliderDivider) sliderDivider.style.left = `${percent}%`;
        };

        comparisonWrapper.addEventListener('mousedown', () => isDragging = true);
        window.addEventListener('mouseup', () => isDragging = false);
        comparisonWrapper.addEventListener('mousemove', (e) => {
            if (!isDragging) return;
            requestAnimationFrame(() => onMove(e.clientX));
        });
        
        comparisonWrapper.addEventListener('touchstart', () => isDragging = true);
        window.addEventListener('touchend', () => isDragging = false);
        comparisonWrapper.addEventListener('touchmove', (e) => {
            if (!isDragging) return;
            e.preventDefault(); 
            requestAnimationFrame(() => onMove(e.touches[0].clientX));
        });
    }

    // 7. Toast Notification Helper
    function showToast(message, type = 'success') {
        let container = document.getElementById('toast-container');
        if (!container) {
            container = document.createElement('div');
            container.id = 'toast-container';
            document.body.appendChild(container);
        }

        const toast = document.createElement('div');
        toast.className = `toast ${type}`;
        
        const icon = type === 'success' ? 'fa-check' : (type === 'error' ? 'fa-exclamation-circle' : 'fa-info-circle');
        
        toast.innerHTML = `<i class="fa-solid ${icon}"></i> <span>${message}</span>`;
        container.appendChild(toast);

        // Remove after 3 seconds
        setTimeout(() => {
            toast.style.animation = 'toastOut 0.3s forwards';
            toast.addEventListener('animationend', () => {
                toast.remove();
            });
        }, 3000);
    }

// --- MANUAL TAGGING LOGIC ---
    const manualTagInput = document.getElementById('manual-tag-input');
    const addTagBtn = document.getElementById('add-tag-btn');
    const tagsContainer = document.getElementById('tags-container');

    if (addTagBtn && manualTagInput) {
        addTagBtn.addEventListener('click', async () => {
            const newTag = manualTagInput.value.trim();
            if (!newTag) return;
            
            if (!currentFilename) {
                alert("No active analysis found.");
                return;
            }

            // 1. Optimistically add to UI immediately
            const tagElement = document.createElement('span'); 
            tagElement.className = 'tag'; 
            tagElement.textContent = newTag; 
            tagElement.style.border = '1px solid var(--pico-primary)'; // Highlight manual tags
            tagsContainer.appendChild(tagElement);
            
            manualTagInput.value = ''; // Clear input

            // 2. Save to Backend (Database)
            try {
                const response = await fetch('/add_custom_tag', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        tag: newTag,
                        filename: currentFilename
                    })
                });
                const data = await response.json();
                if (!response.ok) console.error("Failed to save tag:", data.error);
                
            } catch (error) {
                console.error("Error saving manual tag:", error);
            }
        });
        
        // Allow pressing "Enter" to add
        manualTagInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') addTagBtn.click();
        });
    }

});
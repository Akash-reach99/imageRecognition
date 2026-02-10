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
    // Results & Preview Elements
    // const segImageAfterPlaceholder = document.getElementById('seg-image-after-placeholder'); // REMOVED

    const segDownloadBtn = document.getElementById('seg-download-btn');
    const segPlotPreview = document.getElementById('seg-plot-preview');
    const segResultImage = document.getElementById('seg-result-image');
    const segDefaultImage = document.getElementById('seg-default-image'); // NEW: Default Preview Image


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
        updateProgressStepper(2); // Move to "Select" step

        // Sync the file input for consistency (helper for drag-and-drop)
        if (fileInput && file instanceof File) {
            const dataTransfer = new DataTransfer();
            dataTransfer.items.add(file);
            fileInput.files = dataTransfer.files;
        }
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
            uploadArticle.classList.add('fade-in'); // Add animation
            resultsSection.classList.add('hidden');
            resultsSection.classList.remove('fade-in'); // Reset animation
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
            updateProgressStepper(1); // Reset to step 1
        });
    }

    function resetToolboxUI() {
        segResultImage.classList.add('hidden');
        segResultImage.src = '';
        comparisonWrapper.classList.add('hidden');
        // segImageAfterPlaceholder.classList.remove('hidden'); // REMOVED
        segDownloadBtn.classList.add('hidden');
        effectSettings.classList.add('hidden');
        if (segPlotPreview) segPlotPreview.src = '';

        // Reset to Default Image State
        if (segDefaultImage) {
            segDefaultImage.parentElement.classList.remove('hidden');
            segDefaultImage.src = currentOriginalUrl;
        }

        document.querySelectorAll('.seg-tool-btn').forEach(b => b.classList.add('outline'));
    }

    // --- Progress Stepper Logic ---
    function updateProgressStepper(stepNumber) {
        const steps = document.querySelectorAll('.progress-stepper .step');
        const connectors = document.querySelectorAll('.progress-stepper .step-connector');

        steps.forEach((step, index) => {
            const stepNum = index + 1;
            step.classList.remove('active', 'completed');

            if (stepNum < stepNumber) {
                step.classList.add('completed');
            } else if (stepNum === stepNumber) {
                step.classList.add('active');
            }
        });

        connectors.forEach((conn, index) => {
            conn.classList.remove('completed');
            if (index < stepNumber - 1) {
                conn.classList.add('completed');
            }
        });
    }

    // --- Results Summary Card Logic ---
    function updateSummaryCard(data) {
        const summaryCard = document.getElementById('results-summary-card');
        if (!summaryCard) return;

        // AI Description
        const aiStatus = document.getElementById('summary-ai-status');
        if (data.results.gemini && data.results.gemini.caption) {
            aiStatus.textContent = '✓';
            aiStatus.classList.add('success');
        } else {
            aiStatus.textContent = '—';
            aiStatus.classList.remove('success');
        }

        // Objects
        const objStatus = document.getElementById('summary-objects-status');
        if (data.results.yolo && data.results.yolo.detection && data.results.yolo.detection.total_objects > 0) {
            objStatus.textContent = data.results.yolo.detection.total_objects;
            objStatus.classList.add('success');
        } else {
            objStatus.textContent = '—';
            objStatus.classList.remove('success');
        }

        // OCR
        const ocrStatus = document.getElementById('summary-ocr-status');
        if (data.results.ocr && data.results.ocr.detections && data.results.ocr.detections.length > 0) {
            ocrStatus.textContent = data.results.ocr.detections.length;
            ocrStatus.classList.add('success');
        } else {
            ocrStatus.textContent = '—';
            ocrStatus.classList.remove('success');
        }

        // Tags
        const tagsStatus = document.getElementById('summary-tags-status');
        let tagCount = 0;
        if (data.tags && data.tags.length > 0) {
            tagCount = data.tags.length;
        }
        if (tagCount > 0) {
            tagsStatus.textContent = tagCount;
            tagsStatus.classList.add('success');
        } else {
            tagsStatus.textContent = '—';
            tagsStatus.classList.remove('success');
        }

        // Edit Tools
        const editStatus = document.getElementById('summary-edit-status');
        if (data.results.yolo && data.results.yolo.segmentation) {
            editStatus.textContent = '✓';
            editStatus.classList.add('success');
        } else {
            editStatus.textContent = '—';
            editStatus.classList.remove('success');
        }
    }

    // --- Shared Analysis Logic ---
    async function performAnalysis(formData) {
        globalLoader.classList.remove('hidden');
        errorMessage.classList.add('hidden');
        analyzeBtn.disabled = true;
        updateProgressStepper(3); // Move to "Analyze" step

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
            resultsSection.classList.add('fade-in'); // Add animation
            updateProgressStepper(4); // Move to "Results" step
            updateSummaryCard(data); // Populate summary

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
            if (tagsContainer.parentElement.classList.contains('hidden')) {
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
            // --- REPLACE THE ENTIRE TRY/CATCH BLOCK WITH THIS ---
            try {
                const response = await fetch('/ask', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ question, filename: currentFilename })
                });

                const data = await response.json();
                if (data.error) throw new Error(data.error);

                // 1. Convert Markdown to HTML (Requires marked.js library)
                // If you haven't added <script src="...marked.min.js"> to analyzer.html, do that!
                const rawHTML = marked.parse(data.answer);

                // 2. Get the answer text element
                const answerText = document.getElementById('answer-text');

                // 3. Set the HTML content (instead of textContent)
                answerText.innerHTML = rawHTML;

                // 4. Apply "Typewriter/Fade" Animation
                answerContainer.classList.remove('hidden');
                answerText.style.animation = 'none';
                answerText.offsetHeight; /* Trigger reflow to restart animation */
                answerText.style.animation = 'fadeInUp 0.5s ease forwards';

                questionTextarea.value = '';

            } catch (error) {
                alert(`Q&A Error: ${error.message}`);
            } finally {
                qaLoader.classList.add('hidden');
            }
            // ----------------------------------------------------
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
        const aiAnalyticsContainer = document.getElementById('ai-analytics-results');
        const statsContainer = document.getElementById('image-stats-results');

        geminiContainer.classList.add('hidden');
        ocrContainer.classList.add('hidden');
        tagsContainer.classList.add('hidden');
        sdPromptsSection.classList.add('hidden');
        imaggaContainer.classList.add('hidden');
        if (aiAnalyticsContainer) aiAnalyticsContainer.classList.add('hidden');
        if (statsContainer) statsContainer.classList.add('hidden');
        if (imaggaTagsContent) imaggaTagsContent.innerHTML = '';

        // 2. Show containers
        resultsContainer.classList.remove('hidden');
        resultsContainer.classList.remove('hidden');
        document.getElementById('original-image').src = data.original_image_url;
        if (segDefaultImage) segDefaultImage.src = data.original_image_url; // Set default preview
        qaReferenceImage.src = data.original_image_url;
        displayMetadata(data.metadata);

        // 3. Populate Gemini
        if (data.results.gemini) {
            const suggestionContainer = document.getElementById('qa-suggestions');

            // 2. Check if the backend sent us suggestions
            if (data.results.gemini.suggestions) {
                suggestionContainer.innerHTML = ''; // Clear the old "static" buttons

                // 3. Loop through each suggestion and create a button
                data.results.gemini.suggestions.forEach((question, index) => {
                    const btn = document.createElement('button');
                    btn.type = 'button';
                    btn.className = 'qa-suggestion-btn secondary outline small'; // Same style as before
                    btn.textContent = question;

                    // Optional: Add a small pop-in animation style
                    btn.style.animation = `popIn 0.3s ease forwards ${index * 0.1}s`;
                    btn.style.opacity = '0';

                    // 4. When clicked, put text in the box and focus
                    btn.addEventListener('click', () => {
                        const questionTextarea = document.getElementById('question');
                        questionTextarea.value = question;
                        questionTextarea.focus();
                    });

                    suggestionContainer.appendChild(btn);
                });
            }


            const gemini = data.results.gemini;

            // 1. Caption - Plain text with emphasis
            document.getElementById('gemini-caption-content').textContent = gemini.caption || 'Image Analysis';

            // 2. Summary Section - Brief description below caption
            const summaryEl = document.getElementById('gemini-summary-content');
            const summaryContent = gemini.summary || gemini.overview || '';
            if (summaryContent) {
                summaryEl.textContent = summaryContent;
            } else {
                summaryEl.textContent = 'No summary available.';
            }

            // 3. Key Details Section (inside Detailed Analysis)
            const detailsEl = document.getElementById('gemini-details-content');
            const detailsContent = gemini.details || '';
            if (detailsContent) {
                detailsEl.innerHTML = marked.parse(detailsContent);
            } else {
                // Fallback: parse detailed_prompt if no details field
                const legacyDetails = gemini.detailed_prompt || '';
                if (legacyDetails) {
                    // Remove SD prompts from legacy format
                    const promptMarker = '**Stable Diffusion Prompt Suggestions:**';
                    const cleanDetails = legacyDetails.split(promptMarker)[0].trim();
                    detailsEl.innerHTML = marked.parse(cleanDetails);
                } else {
                    detailsEl.textContent = 'No details available.';
                }
            }

            // 4. Comprehensive / Detailed Analysis Section (Paragraph format)
            const comprehensiveEl = document.getElementById('gemini-comprehensive-content');
            const comprehensiveContent = gemini.comprehensive || '';
            if (comprehensiveContent) {
                comprehensiveEl.innerHTML = marked.parse(comprehensiveContent);
            } else {
                comprehensiveEl.textContent = 'No detailed analysis available.';
            }

            // 5. Visual Style Section
            const styleEl = document.getElementById('gemini-style-content');
            const styleContent = gemini.style || '';
            if (styleContent) {
                styleEl.innerHTML = marked.parse(styleContent);
            } else {
                styleEl.textContent = 'No style analysis available.';
            }

            // 5. Social Media Post
            document.getElementById('gemini-social-post-content').textContent = gemini.social_post || 'No social post generated.';

            // 6. Fun Fact / Did You Notice Section
            const funFactEl = document.getElementById('gemini-funfact-content');
            const funFactContent = gemini.fun_fact || gemini.hidden_details || '';
            if (funFactContent && funFactContent !== 'No specific hidden details noted.') {
                funFactEl.innerHTML = marked.parse(funFactContent);
            } else {
                funFactEl.textContent = 'No special observations noted.';
            }

            // 7. SD Prompts (if available)
            const sdPromptsContent = gemini.sd_prompts || '';
            if (sdPromptsContent) {
                document.getElementById('gemini-sd-prompts-content').textContent = sdPromptsContent;
                sdPromptsSection.classList.remove('hidden');
            } else {
                // Check legacy format for embedded prompts
                const legacyDetails = gemini.detailed_prompt || '';
                const promptMarker = '**Stable Diffusion Prompt Suggestions:**';
                const markerIndex = legacyDetails.indexOf(promptMarker);
                if (markerIndex !== -1) {
                    let sdPrompts = legacyDetails.substring(markerIndex + promptMarker.length).trim();
                    sdPrompts = sdPrompts.replace(/^\s*[\*\-]\s*/gm, '');
                    document.getElementById('gemini-sd-prompts-content').textContent = sdPrompts;
                    sdPromptsSection.classList.remove('hidden');
                }
            }

            geminiContainer.classList.remove('hidden');
        }

        // 5. Imagga Tags - HIDDEN (already combined in Smart Tags section above)
        // Tags from Imagga are now merged into the unified "Smart Tags" section
        // to avoid redundant display. Keeping the data processing but not displaying separately.
        /*
        if (data.results.imagga && data.results.imagga.length > 0) {
            imaggaTagsContent.className = 'tag-pills-container imagga-pills';
            imaggaTagsContent.innerHTML = '';
            data.results.imagga.forEach(tag => {
                const pill = document.createElement('div');
                pill.className = 'tag-pill';
                pill.innerHTML = `
                    <span class="tag-pill-name">${tag.name}</span>
                    <span class="tag-pill-confidence">${Math.round(tag.confidence)}%</span>
                `;
                imaggaTagsContent.appendChild(pill);
            });
            imaggaContainer.classList.remove('hidden');
        }
        */

        // 6. AI Visual Analytics - CHART.JS PROFESSIONAL VISUALIZATION
        const analyticsContainer = document.getElementById('ai-analytics-results');
        if (data.results.ai_analytics && analyticsContainer) {
            const analytics = data.results.ai_analytics;

            // Destroy existing charts if any
            const chartIds = ['content-detection-chart', 'quality-metrics-chart', 'mood-analysis-chart', 'technical-metrics-chart'];
            chartIds.forEach(id => {
                const existingChart = Chart.getChart(id);
                if (existingChart) existingChart.destroy();
            });

            // Theme-aware colors
            const isDarkTheme = document.documentElement.getAttribute('data-theme') === 'dark';
            const textColor = isDarkTheme ? '#e5e7eb' : '#374151';
            const gridColor = isDarkTheme ? 'rgba(255, 255, 255, 0.1)' : 'rgba(0, 0, 0, 0.1)';

            // Chart.js default settings
            Chart.defaults.color = textColor;
            Chart.defaults.borderColor = gridColor;

            // Color palettes
            const vibrantColors = [
                'rgba(59, 130, 246, 0.8)',   // Blue
                'rgba(34, 197, 94, 0.8)',    // Green
                'rgba(249, 115, 22, 0.8)',   // Orange
                'rgba(168, 85, 247, 0.8)',   // Purple
                'rgba(236, 72, 153, 0.8)',   // Pink
            ];
            const vibrantBorders = [
                'rgba(59, 130, 246, 1)',
                'rgba(34, 197, 94, 1)',
                'rgba(249, 115, 22, 1)',
                'rgba(168, 85, 247, 1)',
                'rgba(236, 72, 153, 1)',
            ];

            // 1. KEY INSIGHTS CARDS
            const insights = analytics.key_insights || {};
            const scoreEl = document.getElementById('insight-score-value');
            const resEl = document.getElementById('insight-resolution-value');
            const moodEl = document.getElementById('insight-mood-value');
            const styleEl = document.getElementById('insight-style-value');

            if (scoreEl) scoreEl.textContent = insights.overall_score ? `${insights.overall_score}%` : '--';
            if (resEl) resEl.textContent = insights.resolution_quality || '--';
            if (moodEl) moodEl.textContent = insights.mood_summary || '--';
            if (styleEl) styleEl.textContent = insights.style_category || '--';

            // Animate insight cards FIRST
            document.querySelectorAll('.insight-card').forEach((card, i) => {
                card.style.animation = `fadeInUp 0.5s ease forwards ${i * 0.1}s`;
                card.style.opacity = '0';
            });

            // Update mood emoji using AI-provided emoji (with delay for animation)
            setTimeout(() => {
                const moodIcon = document.getElementById('mood-emoji-icon');
                if (moodIcon) {
                    // Use AI-provided emoji, fallback to default 🎭
                    const emoji = insights.mood_emoji || '🎭';
                    moodIcon.textContent = emoji;
                    console.log('Mood emoji set to:', emoji);
                }
            }, 150);

            // 2. CONTENT DETECTION - HORIZONTAL BAR CHART (Blue theme)
            const contentCtx = document.getElementById('content-detection-chart');
            if (contentCtx && analytics.content_detection && analytics.content_detection.length > 0) {
                const labels = analytics.content_detection.map(d => d.label);
                const dataValues = analytics.content_detection.map(d => d.percentage);

                // Create gradient for each bar
                const ctx2d = contentCtx.getContext('2d');
                const gradient = ctx2d.createLinearGradient(0, 0, 400, 0);
                gradient.addColorStop(0, 'rgba(59, 130, 246, 0.9)');
                gradient.addColorStop(1, 'rgba(99, 102, 241, 0.9)');

                new Chart(contentCtx, {
                    type: 'bar',
                    data: {
                        labels: labels,
                        datasets: [{
                            label: 'Percentage',
                            data: dataValues,
                            backgroundColor: gradient,
                            borderColor: 'rgba(59, 130, 246, 1)',
                            borderWidth: 0,
                            borderRadius: 8,
                            borderSkipped: false,
                            barThickness: 28
                        }]
                    },
                    options: {
                        indexAxis: 'y',
                        responsive: true,
                        maintainAspectRatio: true,
                        plugins: {
                            legend: { display: false },
                            tooltip: {
                                backgroundColor: 'rgba(17, 24, 39, 0.95)',
                                titleFont: { size: 14, weight: 'bold' },
                                bodyFont: { size: 13 },
                                padding: 12,
                                cornerRadius: 8,
                                displayColors: false,
                                callbacks: {
                                    title: (items) => items[0].label,
                                    label: (ctx) => `Detection: ${ctx.parsed.x}%`
                                }
                            }
                        },
                        scales: {
                            x: {
                                min: 0,
                                max: 100,
                                grid: { color: gridColor, drawBorder: false },
                                ticks: {
                                    callback: (v) => v + '%',
                                    font: { size: 11 }
                                }
                            },
                            y: {
                                grid: { display: false },
                                ticks: {
                                    font: { size: 12, weight: '500' },
                                    color: textColor
                                }
                            }
                        },
                        animation: {
                            duration: 1200,
                            easing: 'easeOutCubic',
                            delay: (context) => context.dataIndex * 150
                        }
                    }
                });
            }

            // 3. QUALITY METRICS - HORIZONTAL BAR CHART (Green/Yellow/Red theme)
            const qualityCtx = document.getElementById('quality-metrics-chart');
            if (qualityCtx && analytics.quality_metrics && analytics.quality_metrics.length > 0) {
                const labels = analytics.quality_metrics.map(q => q.name);
                const dataValues = analytics.quality_metrics.map(q => q.score);

                // Enhanced color function with gradients
                const getQualityColor = (value, alpha = 0.85) => {
                    if (value >= 70) return `rgba(34, 197, 94, ${alpha})`;  // Green
                    if (value >= 40) return `rgba(234, 179, 8, ${alpha})`;  // Yellow
                    return `rgba(239, 68, 68, ${alpha})`;  // Red
                };

                const getQualityLabel = (value) => {
                    if (value >= 80) return 'Excellent';
                    if (value >= 70) return 'Good';
                    if (value >= 50) return 'Average';
                    if (value >= 40) return 'Fair';
                    return 'Poor';
                };

                new Chart(qualityCtx, {
                    type: 'bar',
                    data: {
                        labels: labels,
                        datasets: [{
                            label: 'Score',
                            data: dataValues,
                            backgroundColor: dataValues.map(v => getQualityColor(v, 0.85)),
                            borderColor: dataValues.map(v => getQualityColor(v, 1)),
                            borderWidth: 0,
                            borderRadius: 8,
                            borderSkipped: false,
                            barThickness: 28
                        }]
                    },
                    options: {
                        indexAxis: 'y',
                        responsive: true,
                        maintainAspectRatio: true,
                        plugins: {
                            legend: { display: false },
                            tooltip: {
                                backgroundColor: 'rgba(17, 24, 39, 0.95)',
                                titleFont: { size: 14, weight: 'bold' },
                                bodyFont: { size: 13 },
                                padding: 12,
                                cornerRadius: 8,
                                displayColors: true,
                                callbacks: {
                                    title: (items) => items[0].label,
                                    label: (ctx) => `Score: ${ctx.parsed.x}% (${getQualityLabel(ctx.parsed.x)})`
                                }
                            }
                        },
                        scales: {
                            x: {
                                min: 0,
                                max: 100,
                                grid: { color: gridColor, drawBorder: false },
                                ticks: {
                                    callback: (v) => v + '%',
                                    font: { size: 11 }
                                }
                            },
                            y: {
                                grid: { display: false },
                                ticks: {
                                    font: { size: 12, weight: '500' },
                                    color: textColor
                                }
                            }
                        },
                        animation: {
                            duration: 1200,
                            easing: 'easeOutCubic',
                            delay: (context) => context.dataIndex * 150
                        }
                    }
                });
            }

            // 4. MOOD ANALYSIS - POLAR AREA CHART (Pink/Purple theme)
            const moodCtx = document.getElementById('mood-analysis-chart');
            if (moodCtx && analytics.mood_analysis && analytics.mood_analysis.length > 0) {
                const labels = analytics.mood_analysis.map(m => m.emotion);
                const dataValues = analytics.mood_analysis.map(m => m.intensity);

                // Enhanced vibrant colors for polar area
                const moodColors = [
                    'rgba(236, 72, 153, 0.75)',  // Pink
                    'rgba(168, 85, 247, 0.75)',  // Purple
                    'rgba(244, 114, 182, 0.75)', // Light Pink
                    'rgba(139, 92, 246, 0.75)',  // Violet
                    'rgba(219, 39, 119, 0.75)'   // Deep Pink
                ];
                const moodBorders = [
                    'rgba(236, 72, 153, 1)',
                    'rgba(168, 85, 247, 1)',
                    'rgba(244, 114, 182, 1)',
                    'rgba(139, 92, 246, 1)',
                    'rgba(219, 39, 119, 1)'
                ];

                new Chart(moodCtx, {
                    type: 'polarArea',
                    data: {
                        labels: labels,
                        datasets: [{
                            data: dataValues,
                            backgroundColor: moodColors.slice(0, dataValues.length),
                            borderColor: moodBorders.slice(0, dataValues.length),
                            borderWidth: 3
                        }]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: true,
                        plugins: {
                            legend: {
                                position: 'bottom',
                                labels: {
                                    padding: 15,
                                    usePointStyle: true,
                                    pointStyle: 'circle',
                                    font: { size: 12, weight: '500' },
                                    color: textColor
                                }
                            },
                            tooltip: {
                                backgroundColor: 'rgba(17, 24, 39, 0.95)',
                                titleFont: { size: 14, weight: 'bold' },
                                bodyFont: { size: 13 },
                                padding: 12,
                                cornerRadius: 8,
                                callbacks: {
                                    label: (ctx) => `Intensity: ${ctx.parsed.r}%`
                                }
                            }
                        },
                        scales: {
                            r: {
                                min: 0,
                                max: 100,
                                ticks: { display: false },
                                grid: { color: gridColor, lineWidth: 1 }
                            }
                        },
                        animation: {
                            animateRotate: true,
                            animateScale: true,
                            duration: 1500
                        }
                    }
                });
            }

            // 5. TECHNICAL METRICS - RADAR CHART (Indigo theme)
            const techCtx = document.getElementById('technical-metrics-chart');
            if (techCtx && analytics.technical_metrics && analytics.technical_metrics.length > 0) {
                const labels = analytics.technical_metrics.map(t => t.name);
                const dataValues = analytics.technical_metrics.map(t => t.value);

                new Chart(techCtx, {
                    type: 'radar',
                    data: {
                        labels: labels,
                        datasets: [{
                            label: 'Technical Score',
                            data: dataValues,
                            backgroundColor: 'rgba(99, 102, 241, 0.35)',
                            borderColor: 'rgba(99, 102, 241, 1)',
                            borderWidth: 3,
                            pointBackgroundColor: 'rgba(99, 102, 241, 1)',
                            pointBorderColor: '#fff',
                            pointHoverBackgroundColor: '#fff',
                            pointHoverBorderColor: 'rgba(99, 102, 241, 1)',
                            pointRadius: 6,
                            pointHoverRadius: 9,
                            pointBorderWidth: 2
                        }]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: true,
                        plugins: {
                            legend: { display: false },
                            tooltip: {
                                backgroundColor: 'rgba(17, 24, 39, 0.95)',
                                titleFont: { size: 14, weight: 'bold' },
                                bodyFont: { size: 13 },
                                padding: 12,
                                cornerRadius: 8,
                                callbacks: {
                                    title: (items) => items[0].label,
                                    label: (ctx) => `Value: ${ctx.parsed.r}%`
                                }
                            }
                        },
                        scales: {
                            r: {
                                min: 0,
                                max: 100,
                                beginAtZero: true,
                                angleLines: { color: gridColor, lineWidth: 1 },
                                grid: { color: gridColor, lineWidth: 1 },
                                pointLabels: {
                                    font: { size: 12, weight: '600' },
                                    color: textColor
                                },
                                ticks: {
                                    stepSize: 25,
                                    display: false
                                }
                            }
                        },
                        animation: {
                            duration: 1800,
                            easing: 'easeOutQuart'
                        }
                    }
                });
            }

            analyticsContainer.classList.remove('hidden');
        }

        // 6.5 Smart Tags (Combined) - Show tags from all sources
        const tagsContainerEl = document.getElementById('tags-container');
        if (tagsContainerEl) {
            const allTags = new Map(); // Use Map to avoid duplicates

            // Collect tags from AI Analytics content_detection
            if (data.results.ai_analytics && data.results.ai_analytics.content_detection) {
                data.results.ai_analytics.content_detection.forEach(item => {
                    const name = item.label.toLowerCase();
                    if (!allTags.has(name)) {
                        allTags.set(name, { name: item.label, confidence: item.percentage || 80, source: 'AI' });
                    }
                });
            }

            // Collect tags from Imagga
            if (data.results.imagga && data.results.imagga.length > 0) {
                data.results.imagga.forEach(tag => {
                    const name = tag.name.toLowerCase();
                    if (!allTags.has(name) || tag.confidence > allTags.get(name).confidence) {
                        allTags.set(name, { name: tag.name, confidence: tag.confidence, source: 'Imagga' });
                    }
                });
            }

            // Collect tags from YOLO detection
            if (data.results.yolo && data.results.yolo.detection && data.results.yolo.detection.detection_counts) {
                Object.keys(data.results.yolo.detection.detection_counts).forEach(label => {
                    const name = label.toLowerCase();
                    if (!allTags.has(name)) {
                        allTags.set(name, { name: label, confidence: 90, source: 'YOLO' });
                    }
                });
            }

            // Fetch and collect custom tags from backend (persisted)
            // Use async IIFE to fetch and add custom tags
            (async () => {
                try {
                    if (data.filename || currentFilename) {
                        const filename = data.filename || currentFilename;
                        const response = await fetch(`/get_custom_tags/${encodeURIComponent(filename)}`);
                        if (response.ok) {
                            const tagData = await response.json();
                            if (tagData.custom_tags && tagData.custom_tags.length > 0) {
                                tagData.custom_tags.forEach(tagName => {
                                    const name = tagName.toLowerCase();
                                    if (!allTags.has(name)) {
                                        allTags.set(name, { name: tagName, confidence: 100, source: 'Custom' });
                                    }
                                });

                                // Re-render tags with custom tags included
                                tagsContainerEl.innerHTML = '';
                                const sortedTags = Array.from(allTags.values()).sort((a, b) => b.confidence - a.confidence);
                                sortedTags.forEach(tag => {
                                    const pill = document.createElement('div');
                                    pill.className = 'tag-pill';
                                    if (tag.source === 'Custom') {
                                        pill.style.background = 'linear-gradient(135deg, rgba(34, 197, 94, 0.2) 0%, rgba(34, 197, 94, 0.05) 100%)';
                                        pill.style.borderColor = '#22c55e';
                                        pill.innerHTML = `
                                            <span class="tag-pill-name">${tag.name}</span>
                                            <span class="tag-pill-confidence" style="background: #22c55e;">Custom</span>
                                        `;
                                    } else {
                                        pill.innerHTML = `
                                            <span class="tag-pill-name">${tag.name}</span>
                                            <span class="tag-pill-confidence">${Math.round(tag.confidence)}%</span>
                                        `;
                                    }
                                    tagsContainerEl.appendChild(pill);
                                });

                                tagsContainer.classList.remove('hidden');
                            }
                        }
                    }
                } catch (error) {
                    console.log('Could not fetch custom tags:', error);
                }
            })();

            // Display combined tags if any exist
            if (allTags.size > 0) {
                tagsContainerEl.innerHTML = '';
                tagsContainerEl.className = 'tag-pills-container';

                // Sort by confidence and display
                const sortedTags = Array.from(allTags.values()).sort((a, b) => b.confidence - a.confidence);
                sortedTags.forEach(tag => {
                    const pill = document.createElement('div');
                    pill.className = 'tag-pill';

                    // Custom tag styling
                    if (tag.source === 'Custom') {
                        pill.style.background = 'linear-gradient(135deg, rgba(34, 197, 94, 0.2) 0%, rgba(34, 197, 94, 0.05) 100%)';
                        pill.style.borderColor = '#22c55e';
                        pill.innerHTML = `
                            <span class="tag-pill-name">${tag.name}</span>
                            <span class="tag-pill-confidence" style="background: #22c55e;">Custom</span>
                        `;
                    } else {
                        pill.innerHTML = `
                            <span class="tag-pill-name">${tag.name}</span>
                            <span class="tag-pill-confidence">${Math.round(tag.confidence)}%</span>
                        `;
                    }
                    tagsContainerEl.appendChild(pill);
                });

                tagsContainer.classList.remove('hidden');
            }
        }

        // 7. Image Statistics Panel
        const statsPanel = document.getElementById('image-stats-results');
        if (data.image_stats && statsPanel) {
            const stats = data.image_stats;

            // Helper to set stat values
            const setStat = (id, value) => {
                const fillEl = document.getElementById(`stat-${id}-fill`);
                const valEl = document.getElementById(`stat-${id}-value`);

                if (fillEl && valEl) {
                    fillEl.style.width = `${value}%`;
                    valEl.textContent = `${value}%`;

                    // Simple color scale
                    if (value < 30) fillEl.style.backgroundColor = 'var(--pico-muted-color)';
                    else if (value < 70) fillEl.style.backgroundColor = 'var(--pico-primary)';
                    else fillEl.style.backgroundColor = 'var(--success-color)';
                }
            };

            setStat('brightness', stats.brightness || 0);
            setStat('contrast', stats.contrast || 0);
            setStat('saturation', stats.saturation || 0);
            setStat('sharpness', stats.sharpness || 0);

            statsPanel.classList.remove('hidden');
        }

        // 7. OCR
        if (data.results.ocr) {
            const ocr = data.results.ocr;
            document.getElementById('ocr-annotated-image').src = ocr.annotated_image_url;
            document.getElementById('ocr-text-content').textContent = ocr.extracted_text;

            // Display OCR stats (time taken, detection count, provider)
            const ocrStatsContainer = document.getElementById('ocr-stats');
            if (ocrStatsContainer) {
                let statsHtml = '';
                if (ocr.detection_count !== undefined) {
                    statsHtml += `<span class="ocr-stat"><i class="fa-solid fa-font"></i> ${ocr.detection_count} text${ocr.detection_count !== 1 ? 's' : ''} detected</span>`;
                }
                if (ocr.time_taken !== undefined) {
                    statsHtml += `<span class="ocr-stat"><i class="fa-solid fa-clock"></i> ${ocr.time_taken}s</span>`;
                }
                if (ocr.provider) {
                    statsHtml += `<span class="ocr-stat"><i class="fa-solid fa-robot"></i> ${ocr.provider.charAt(0).toUpperCase() + ocr.provider.slice(1)}</span>`;
                }
                ocrStatsContainer.innerHTML = statsHtml;
                ocrStatsContainer.classList.remove('hidden');
            }

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
                    if (segPlotPreview) segPlotPreview.src = result.plot_url;
                    segmentationToolbox.classList.remove('hidden');
                    yoloTaskFound = true;

                } else if (task === 'detection' && result.type === 'annotated_image') {
                    // Show detection counts in the collapsible section
                    if (result.detection_counts && result.total_objects > 0) {
                        const totalElement = document.createElement('p');
                        totalElement.className = 'yolo-count-total';
                        totalElement.textContent = `Total Objects Detected: ${result.total_objects}`;
                        yoloCountContainer.appendChild(totalElement);
                        const sortedCounts = Object.entries(result.detection_counts).sort(([, a], [, b]) => b - a);
                        for (const [name, count] of sortedCounts) {
                            const countElement = document.createElement('span');
                            countElement.className = 'yolo-count-item';
                            countElement.textContent = `${name} (${count})`;
                            yoloCountContainer.appendChild(countElement);
                        }
                        yoloDetectionResults.classList.remove('hidden');
                    }

                    // Create detection card with image AND detected objects list below it
                    const card = document.createElement('article');
                    card.className = 'yolo-card detection-card';

                    let content = `<h4>YOLOv8: Detection Plot</h4>`;
                    content += `<img src="${result.processed_image_url}" alt="Processed for ${task}" class="zoomable">`;

                    // Add detected objects summary directly below the image
                    if (result.detection_counts && result.total_objects > 0) {
                        content += `<div class="detection-summary">`;
                        content += `<p class="detection-total"><i class="fa-solid fa-magnifying-glass"></i> <strong>${result.total_objects}</strong> object${result.total_objects !== 1 ? 's' : ''} detected</p>`;
                        content += `<div class="detection-items">`;

                        const sortedCounts = Object.entries(result.detection_counts).sort(([, a], [, b]) => b - a);
                        for (const [name, count] of sortedCounts) {
                            content += `<span class="detection-item"><span class="detection-count">${count}×</span> ${name}</span>`;
                        }

                        content += `</div></div>`;
                    } else {
                        content += `<p class="detection-none"><i class="fa-solid fa-info-circle"></i> No objects detected in this image.</p>`;
                    }

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

        // 8. Auto-Expand Sections (User Request)
        const analyticsDetails = document.querySelector('#ai-analytics-results details');
        if (analyticsDetails) analyticsDetails.open = true;

        const yoloDetails = document.querySelector('#yolo-vision-analysis details');
        if (yoloDetails) yoloDetails.open = true;

        // 9. Q&A
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

            const basicProps = {};
            const sections = {};

            // 1. Separate Primitives (Basic) vs Objects (Sections)
            for (const key in metadata) {
                if (key === 'gps_info') continue; // Handled separately

                const value = metadata[key];
                if (typeof value === 'object' && value !== null) {
                    sections[key] = value;
                } else {
                    basicProps[key] = value;
                }
            }

            // 2. Render Basic Properties First
            if (Object.keys(basicProps).length > 0) {
                const titleElement = document.createElement('h6');
                titleElement.textContent = 'File Properties';
                metadataContainer.appendChild(titleElement);

                const listElement = document.createElement('ul');
                listElement.className = 'metadata-list';
                for (const key in basicProps) {
                    const listItem = document.createElement('li');
                    // Capitalize key
                    const label = key.charAt(0).toUpperCase() + key.replace('_', ' ').slice(1);
                    listItem.innerHTML = `<strong>${label}:</strong> ${basicProps[key]}`;
                    listElement.appendChild(listItem);
                }
                metadataContainer.appendChild(listElement);
            }

            // 3. Render Sections (Device Info etc)
            for (const sectionTitle in sections) {
                const section = sections[sectionTitle];
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

            // 4. GPS Map
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
    const clipboard = new ClipboardJS('.copy-btn, .copy-btn-mini, .copy-btn-small, .card-copy-btn');
    clipboard.on('success', function (e) {
        const originalIcon = e.trigger.innerHTML;
        e.trigger.innerHTML = '<i class="fa-solid fa-check"></i>';
        e.trigger.classList.add('copied');
        setTimeout(() => { e.trigger.innerHTML = originalIcon; e.trigger.classList.remove('copied'); }, 1500);
        e.clearSelection();
    });
    clipboard.on('error', function (e) { console.error('ClipboardJS error:', e); alert('Failed to copy text.'); });

    // --- MAGIC TOOLBOX INTERACTION LOGIC (REVERT1) ---

    // 1. Slider Value Display
    if (intensitySlider) {
        intensitySlider.addEventListener('input', (e) => {
            intensityValue.textContent = e.target.value;
        });
    }

    // 2. Effect Selection UI
    window.selectEffect = function (effect) {
        currentEffect = effect;
        effectSettings.classList.remove('hidden');
        document.querySelectorAll('.seg-tool-btn').forEach(b => b.classList.add('outline'));
        if (effect === 'blur') segBtnBlurBg.classList.remove('outline');
        if (effect === 'spotlight') segBtnSpotlight.classList.remove('outline');
    }

    // 3. Apply Button Handler
    if (applyEffectBtn) {
        applyEffectBtn.addEventListener('click', () => {
            if (currentEffect === 'blur') performAdvancedEdit('blur-bg');
            if (currentEffect === 'spotlight') performAdvancedEdit('spotlight');
        });
    }

    // 4. One-Click Button Handlers
    if (segBtnRemoveBg) {
        segBtnRemoveBg.addEventListener('click', () => {
            document.querySelectorAll('.seg-tool-btn').forEach(b => b.classList.add('outline'));
            document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active')); // Clear filters
            segBtnRemoveBg.classList.remove('outline');
            effectSettings.classList.add('hidden');
            performAdvancedEdit('remove-bg');
        });
    }
    if (segBtnSmartCrop) {
        segBtnSmartCrop.addEventListener('click', () => {
            document.querySelectorAll('.seg-tool-btn').forEach(b => b.classList.add('outline'));
            document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active')); // Clear filters
            segBtnSmartCrop.classList.remove('outline');
            effectSettings.classList.add('hidden');
            performAdvancedEdit('smart-crop');
        });
    }

    // New: Filter Buttons
    document.querySelectorAll('.filter-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            // Reset other tools
            document.querySelectorAll('.seg-tool-btn').forEach(b => b.classList.add('outline'));
            document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));

            // Set active
            btn.classList.add('active');
            effectSettings.classList.add('hidden');

            const filterType = btn.getAttribute('data-filter');
            performAdvancedEdit(filterType);
        });
    });

    // New: Reset Button
    const filterResetBtn = document.getElementById('filter-reset-btn');
    if (filterResetBtn) {
        filterResetBtn.addEventListener('click', () => {
            // Reset UI
            document.querySelectorAll('.seg-tool-btn').forEach(b => b.classList.add('outline'));
            document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));

            // Hide results
            segResultImage.classList.add('hidden');
            comparisonWrapper.classList.add('hidden');
            if (segDefaultImage) segDefaultImage.parentElement.classList.remove('hidden'); // Show default
            // segImageAfterPlaceholder.classList.remove('hidden'); // REMOVED
            segDownloadBtn.classList.add('hidden');

            showToast("Filters Reset", "success");
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
            if (btn) btn.disabled = true;
        });

        try {
            let endpoint = '';
            let successMessage = 'Effect Applied!';
            const intensity = intensitySlider ? parseInt(intensitySlider.value) : 50;

            let payload = {
                original_url: currentOriginalUrl,
                mask_url: currentMaskUrl,
                intensity: intensity
            };

            if (['bw', 'sepia', 'vintage', 'cool', 'warm', 'enhance'].includes(effectType)) {
                endpoint = '/edit/filter';
                successMessage = 'Filter Applied!';

                // Refactor for Blob/FormData upload as per user request
                try {
                    const imageResponse = await fetch(currentOriginalUrl);
                    const imageBlob = await imageResponse.blob();
                    const formData = new FormData();
                    formData.append('file', imageBlob, 'image.jpg'); // Filename is handled by backend logic or secure_filename
                    formData.append('filter_name', effectType);

                    const response = await fetch(endpoint, {
                        method: 'POST',
                        body: formData
                    });

                    // --- Handle Response (Duplicated from below but needed here for differnt logic flow if we want to return early) ---
                    const data = await response.json();
                    if (!response.ok) throw new Error(data.error || 'Failed to apply filter.');

                    const cacheBuster = '?t=' + new Date().getTime();

                    // Logic for Filters (Slider update)
                    segResultImage.classList.add('hidden');
                    comparisonWrapper.classList.remove('hidden');
                    if (segDefaultImage) segDefaultImage.parentElement.classList.add('hidden'); // Hide default
                    // segImageAfterPlaceholder.classList.add('hidden'); // REMOVED
                    sliderBefore.src = currentOriginalUrl;
                    sliderAfter.src = data.processed_image_url + cacheBuster;
                    setupComparisonSlider();

                    segDownloadBtn.href = data.processed_image_url + cacheBuster;
                    segDownloadBtn.download = data.filename;
                    segDownloadBtn.classList.remove('hidden');

                    showToast(successMessage, 'success');

                    return; // Exit function since we handled it here manually

                } catch (error) {
                    throw error; // Re-throw to be caught by outer catch
                }

            } else {
                // ... existing logic for remove-bg, blur, etc ...
                switch (effectType) {
                    case 'remove-bg': endpoint = '/edit/remove-bg'; successMessage = 'Background Removed!'; break;
                    case 'blur-bg': endpoint = '/edit/blur-bg'; successMessage = 'Background Blurred!'; break;
                    case 'spotlight': endpoint = '/edit/spotlight'; successMessage = 'Spotlight Applied!'; break;
                    case 'smart-crop': endpoint = '/edit/smart-crop'; successMessage = 'Smart Crop Complete!'; break;
                    default: showToast('Unknown effect.', 'error'); return;
                }

                const intensity = intensitySlider ? parseInt(intensitySlider.value) : 50;
                // Standard JSON Request for other tools
                const response = await fetch(endpoint, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        original_url: currentOriginalUrl,
                        mask_url: currentMaskUrl,
                        intensity: intensity
                    })
                });

                const data = await response.json();
                if (!response.ok) throw new Error(data.error || 'Failed to apply effect.');

                // ... Standard Display Logic ...
                const cacheBuster = '?t=' + new Date().getTime();

                // Display Logic
                if (effectType === 'remove-bg' || effectType === 'smart-crop') {
                    comparisonWrapper.classList.add('hidden');
                    segResultImage.src = data.processed_image_url + cacheBuster;
                    segResultImage.classList.remove('hidden');
                    if (segDefaultImage) segDefaultImage.parentElement.classList.add('hidden'); // Hide default
                    // segImageAfterPlaceholder.classList.add('hidden'); // REMOVED
                } else {
                    segResultImage.classList.add('hidden');
                    comparisonWrapper.classList.remove('hidden');
                    if (segDefaultImage) segDefaultImage.parentElement.classList.add('hidden'); // Hide default
                    // segImageAfterPlaceholder.classList.add('hidden'); // REMOVED
                    sliderBefore.src = currentOriginalUrl;
                    sliderAfter.src = data.processed_image_url + cacheBuster;
                    setupComparisonSlider();
                }

                segDownloadBtn.href = data.processed_image_url + cacheBuster;
                segDownloadBtn.download = data.filename;
                segDownloadBtn.classList.remove('hidden');

                showToast(successMessage, 'success');
                return;
            }

        } catch (error) {
            errorMessage.textContent = `Error: ${error.message}`;
            errorMessage.classList.remove('hidden');
            showToast(`Error: ${error.message}`, 'error');
        } finally {
            segLoader.classList.add('hidden');
            [segBtnRemoveBg, segBtnBlurBg, segBtnSpotlight, segBtnSmartCrop, applyEffectBtn].forEach(btn => {
                if (btn) btn.disabled = false;
            });
        }
    }

    // 6. Comparison Slider Logic
    let sliderInitialized = false;
    function setupComparisonSlider() {
        if (!comparisonWrapper || sliderInitialized) return;
        sliderInitialized = true;

        let isDragging = false;

        const onMove = (clientX) => {
            const rect = comparisonWrapper.getBoundingClientRect();
            let x = clientX - rect.left;
            let percent = (x / rect.width) * 100;
            percent = Math.max(0, Math.min(100, percent));

            if (sliderOverlay) sliderOverlay.style.clipPath = `inset(0 ${100 - percent}% 0 0)`;
            if (sliderDivider) sliderDivider.style.left = `${percent}%`;
        };

        const startDrag = (e) => {
            isDragging = true;
            comparisonWrapper.classList.add('dragging');

            // Fix: Calculate initial position on click/touch
            let clientX = e.touches ? e.touches[0].clientX : e.clientX;
            onMove(clientX);
        };

        const stopDrag = () => {
            isDragging = false;
            comparisonWrapper.classList.remove('dragging');
        };

        comparisonWrapper.addEventListener('mousedown', startDrag);
        window.addEventListener('mouseup', stopDrag);
        window.addEventListener('mousemove', (e) => {
            if (!isDragging) return;
            e.preventDefault(); // Prevent selection
            requestAnimationFrame(() => onMove(e.clientX));
        });

        comparisonWrapper.addEventListener('touchstart', startDrag, { passive: false });
        window.addEventListener('touchend', stopDrag);
        window.addEventListener('touchmove', (e) => {
            if (!isDragging) return;
            e.preventDefault(); // Prevent scroll
            requestAnimationFrame(() => onMove(e.touches[0].clientX));
        }, { passive: false });
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

            // 1. Optimistically add to UI immediately with pill styling
            const pill = document.createElement('div');
            pill.className = 'tag-pill';
            pill.style.background = 'linear-gradient(135deg, rgba(34, 197, 94, 0.2) 0%, rgba(34, 197, 94, 0.05) 100%)';
            pill.style.borderColor = '#22c55e';
            pill.innerHTML = `
                <span class="tag-pill-name">${newTag}</span>
                <span class="tag-pill-confidence" style="background: #22c55e;">Custom</span>
            `;
            tagsContainer.appendChild(pill);

            // Ensure tags section is visible
            const tagsResultsSection = document.getElementById('tags-results');
            if (tagsResultsSection) tagsResultsSection.classList.remove('hidden');

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

// --- Global Copy Function (for inline onclicks) ---
async function copyText(selector, btn) {
    const element = document.querySelector(selector);
    if (!element) return;

    const textToCopy = element.innerText || element.textContent; // Handle both
    if (!textToCopy) return;

    try {
        await navigator.clipboard.writeText(textToCopy);

        // Visual Feedback
        const originalIcon = btn.innerHTML;
        btn.innerHTML = '<i class="fa-solid fa-check"></i>';
        btn.style.opacity = '1';
        btn.style.color = 'var(--pico-primary)'; // Force primary color

        setTimeout(() => {
            btn.innerHTML = '<i class="fa-regular fa-copy"></i>';
            btn.style.opacity = '';
            btn.style.color = '';
        }, 2000);
    } catch (err) {
        console.error('Failed to copy!', err);
    }
}
// static/script.js
document.addEventListener('DOMContentLoaded', () => {
    
    // --- Element Selectors ---
    const fileInput = document.getElementById('file');
    const form = document.getElementById('upload-form');
    const globalLoader = document.getElementById('global-loader-container');
    const errorMessage = document.getElementById('error-message');
    
    // --- Result Area Selectors ---
    const resultsContainer = document.getElementById('results-container');
    
    // --- Wizard Step Selectors ---
    const step1Upload = document.getElementById('step-1-upload');
    const step2Options = document.getElementById('step-2-options');
    const step3Results = document.getElementById('step-3-results');

    // --- Wizard Element Selectors ---
    const wizardImagePreview = document.getElementById('wizard-image-preview');
    const taskCheckboxes = document.querySelectorAll('.task-checkbox');
    const runAnalysisBtn = document.getElementById('run-analysis-btn');
    const startOverBtns = document.querySelectorAll('.start-over-btn');
    const fileInputLabel = document.querySelector('.file-input-filename');
    const dropZone = document.querySelector('.drop-zone');

    // --- API Status Check Elements ---
    const checkApiBtn = document.getElementById('check-api-status-btn');
    const apiStatusMsg = document.getElementById('api-status-message');

    // --- State Variables ---
    let currentFilename = '';
    let selectedFile = null;
    const storageKey = 'analyzerLastAnalysis'; // localStorage key

    // --- Drag and Drop for File Input ---
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
            if (e.dataTransfer.files.length > 0) {
                const file = e.dataTransfer.files[0];
                if (file.type.startsWith('image/')) {
                    handleFileSelect(file);
                } else {
                    alert('Please drop an image file.');
                }
            }
        });
    }

    // --- API Status Check Logic ---
    if (checkApiBtn && apiStatusMsg) {
        checkApiBtn.addEventListener('click', () => {
            checkApiBtn.setAttribute('aria-busy', 'true');
            checkApiBtn.disabled = true;
            apiStatusMsg.textContent = 'Checking...';
            apiStatusMsg.style.color = 'var(--pico-muted-color)';
            
            fetch('/api/gemini-check')
                .then(response => response.json())
                .then(data => {
                    if (data.status === 'ok') {
                        apiStatusMsg.textContent = `✅ ${data.message}`;
                        apiStatusMsg.style.color = 'var(--success-color)';
                    } else {
                        apiStatusMsg.textContent = `❌ Error: ${data.message}`;
                        apiStatusMsg.style.color = 'var(--error-color)';
                    }
                })
                .catch(err => {
                    apiStatusMsg.textContent = '❌ Network Error: Could not reach the server.';
                    apiStatusMsg.style.color = 'var(--error-color)';
                })
                .finally(() => {
                    checkApiBtn.setAttribute('aria-busy', 'false');
                    checkApiBtn.disabled = false;
                });
        });
    }
    
    // --- Refactored File Selection Logic ---
    function handleFileSelect(file) {
        if (!file.type.startsWith('image/')) {
             alert('Please select an image file.');
             return;
        }
        selectedFile = file;
        const previewUrl = URL.createObjectURL(file);
        
        if (wizardImagePreview) {
            wizardImagePreview.src = previewUrl;
        }
        if (fileInputLabel) {
            fileInputLabel.textContent = file.name;
        }
        step1Upload.classList.add('hidden');
        step3Results.classList.add('hidden');
        step2Options.classList.remove('hidden');
        
        const dataTransfer = new DataTransfer();
        dataTransfer.items.add(selectedFile);
        fileInput.files = dataTransfer.files;
    }

    if (fileInput) {
        fileInput.addEventListener('change', (e) => {
            if (e.target.files && e.target.files.length > 0) {
                handleFileSelect(e.target.files[0]);
            }
        });
    }

    // --- Logic for "Run Selected Tasks" button ---
    if (runAnalysisBtn) {
        runAnalysisBtn.addEventListener('click', () => {
            document.querySelectorAll('input[name="tasks"]').forEach(cb => cb.checked = false);
            
            let tasksSelected = 0;
            taskCheckboxes.forEach(checkbox => {
                if (checkbox.checked) {
                    const taskName = checkbox.dataset.task;
                    if (taskName === 'segmentation') {
                        ['detection', 'segmentation', 'pose', 'classification'].forEach(task => {
                           const hiddenCb = document.querySelector(`input[name="tasks"][value="${task}"]`);
                           if(hiddenCb) hiddenCb.checked = true;
                        });
                    } else {
                        const hiddenCb = document.querySelector(`input[name="tasks"][value="${taskName}"]`);
                        if(hiddenCb) hiddenCb.checked = true;
                    }
                    tasksSelected++;
                }
            });

            if (tasksSelected === 0) {
                alert('Please select at least one task to run.');
                return;
            }
            
            step2Options.classList.add('hidden');
            globalLoader.classList.remove('hidden');
            errorMessage.classList.add('hidden');
            
            form.dispatchEvent(new Event('submit', { cancelable: true }));
        });
    }

    // --- REMOVED: "Ask a Question" button logic ---

    // --- Logic for "Start Over" buttons ---
    startOverBtns.forEach(btn => {
         btn.addEventListener('click', () => {
            step1Upload.classList.remove('hidden');
            step2Options.classList.add('hidden');
            step3Results.classList.add('hidden');
            resultsContainer.classList.add('hidden');
            
            fileInput.value = ''; 
            if (fileInputLabel) {
                fileInputLabel.textContent = 'No file selected';
            }
            taskCheckboxes.forEach(cb => cb.checked = false);
            currentFilename = '';
            selectedFile = null;
            
            // Clear persistence
            localStorage.removeItem(storageKey);
            
            if(apiStatusMsg) apiStatusMsg.textContent = '';
        });
    });

    // --- Main Analysis Form Handler ---
    if (form) {
        form.addEventListener('submit', async (e) => {
            e.preventDefault();
            const formData = new FormData(form);
            
            try {
                const response = await fetch('/analyze', { method: 'POST', body: formData });
                const data = await response.json();
                if (!response.ok) {
                    throw new Error(data.error || 'An unknown server error occurred.');
                }
                
                currentFilename = data.filename;
                // Save to localStorage
                localStorage.setItem(storageKey, JSON.stringify(data));
                
                // --- NEW: Increment API Counters ---
                if (window.incrementApiCount && data.api_calls) {
                    if (data.api_calls.gemini > 0) {
                        window.incrementApiCount('gemini', data.api_calls.gemini);
                    }
                }
                
                displayResults(data);

            } catch (error) {
                errorMessage.textContent = `Error: ${error.message}`;
                errorMessage.classList.remove('hidden');
                step3Results.classList.add('hidden');
            } finally {
                globalLoader.classList.add('hidden');
            }
        });
    }

    // --- REMOVED: Follow-up Question Handler ---

    // --- Function to Display Full Analysis Results ---
    function displayResults(data) {
        step3Results.classList.remove('hidden');
        document.getElementById('yolo-results-grid').innerHTML = '';
        
        // Hide all optional sections
        if (document.getElementById('gemini-results')) document.getElementById('gemini-results').classList.add('hidden');
        if (document.getElementById('ocr-results')) document.getElementById('ocr-results').classList.add('hidden');
        if (document.getElementById('tags-results')) document.getElementById('tags-results').classList.add('hidden');
        
        resultsContainer.classList.remove('hidden');
        document.getElementById('original-image').src = data.original_image_url;
        displayMetadata(data.metadata);

        const geminiContainer = document.getElementById('gemini-results');
        const ocrContainer = document.getElementById('ocr-results');
        const tagsContainer = document.getElementById('tags-results');
        const tagsContent = document.getElementById('tags-container');

        if (data.results.gemini) {
            geminiContainer.classList.remove('hidden');
            document.getElementById('gemini-caption').textContent = data.results.gemini.caption;
            document.getElementById('gemini-summary').textContent = data.results.gemini.summary;
            document.getElementById('gemini-detailed').textContent = data.results.gemini.detailed;
            document.getElementById('gemini-hidden-details').textContent = data.results.gemini.hidden_details;
            const socialDetails = document.getElementById('gemini-social-details');
            if (data.results.gemini.social_post) {
                document.getElementById('gemini-social-post').textContent = data.results.gemini.social_post;
                socialDetails.classList.remove('hidden');
            } else {
                socialDetails.classList.add('hidden');
            }
        }

        if (data.tags && data.tags.length > 0) {
            tagsContent.innerHTML = '';
            data.tags.forEach(tag => {
                const tagElement = document.createElement('span');
                tagElement.className = 'tag';
                tagElement.textContent = tag;
                tagsContent.appendChild(tagElement);
            });
            tagsContainer.classList.remove('hidden');
        }

        if (data.results.ocr) {
            document.getElementById('ocr-text-content').textContent = data.results.ocr;
            ocrContainer.classList.remove('hidden');
        }

        if (data.results.yolo) {
            const yoloGrid = document.getElementById('yolo-results-grid');
            yoloGrid.innerHTML = '';
            for (const task in data.results.yolo) {
                const result = data.results.yolo[task];
                const card = document.createElement('article');
                card.className = 'yolo-card';
                let content = `<h4>YOLOv8: ${task.charAt(0).toUpperCase() + task.slice(1)}</h4>`;
                if (result.type === 'annotated_image') {
                    content += `<img src="${result.processed_image_url}" alt="Processed for ${task}" class="zoomable">`;
                } else if (result.type === 'classification') {
                    content += `<p><strong>Class:</strong> ${result.class_name}</p><p><strong>Confidence:</strong> ${result.confidence}</p>`;
                }
                card.innerHTML = content;
                yoloGrid.appendChild(card);
            }
        }
    }

    // --- Helper for metadata ---
    function displayMetadata(metadata) {
        const metadataContainer = document.getElementById('metadata-content');
        metadataContainer.innerHTML = '';
        if (metadata) {
            for (const sectionTitle in metadata) {
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
        }
    }

    // --- Load Saved Results from localStorage on Page Load ---
    const savedData = localStorage.getItem(storageKey);
    if (savedData) {
        try {
            const data = JSON.parse(savedData);
            currentFilename = data.filename;
            step1Upload.classList.add('hidden');
            step2Options.classList.add('hidden');
            displayResults(data);
        } catch (e) {
            console.error("Could not parse saved analysis data.", e);
            localStorage.removeItem(storageKey);
        }
    }
});
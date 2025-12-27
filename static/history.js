// static/history.js
document.addEventListener('DOMContentLoaded', () => {
    const themeSwitcher = document.getElementById('theme-switcher');
    const zoomModal = document.getElementById('zoom-modal-backdrop');
    const zoomImg = document.getElementById('zoom-modal-img');

    // History Modal Elements
    const historyModal = document.getElementById('history-modal-backdrop');
    const historyModalClose = document.getElementById('history-modal-close');
    const modalImage = document.getElementById('modal-image');
    const modalTagsContainer = document.getElementById('modal-tags-container');
    const modalTimestamp = document.getElementById('modal-timestamp');

    // Buttons
    const modalDeleteBtn = document.getElementById('modal-delete-btn');
    const modalDownloadBtn = document.getElementById('modal-download-btn'); // <--- NEW DOWNLOAD BTN
    
    let currentHistoryId = null; // Variable to store the ID of the open modal

    // Metadata Selectors
    const modalMetadataSection = document.getElementById('modal-metadata-section');
    const modalMetadataContent = document.getElementById('modal-metadata-content');
    const modalMapContainer = document.getElementById('modal-map-container');

    // Generation Selectors
    const modalGenInfoSection = document.getElementById('modal-generation-info-section');
    const modalGenPrompt = document.getElementById('modal-generation-prompt');

    // Gemini Modal Elements
    const modalGeminiSection = document.getElementById('modal-gemini-section');
    const modalGeminiCaption = document.getElementById('modal-gemini-caption');
    const modalGeminiSummary = document.getElementById('modal-gemini-summary');
    const modalGeminiDetailed = document.getElementById('modal-gemini-detailed');
    const modalSdPromptsSection = document.getElementById('modal-sd-prompts-section');
    const modalSdPromptsContent = document.getElementById('modal-sd-prompts-content');
    const modalGeminiSocialDetails = document.getElementById('modal-gemini-social-details');
    const modalGeminiSocial = document.getElementById('modal-gemini-social');

    // OCR Modal Elements
    const modalOcrSection = document.getElementById('modal-ocr-section');
    const modalOcrAnnotatedImage = document.getElementById('modal-ocr-annotated-image');
    const modalOcrText = document.getElementById('modal-ocr-text');

    // YOLO Modal Elements
    const modalYoloSection = document.getElementById('modal-yolo-section');
    const modalYoloGrid = document.getElementById('modal-yolo-grid');

    // Imagga Modal Elements
    const modalImaggaSection = document.getElementById('modal-imagga-section');
    const modalImaggaTagsContainer = document.getElementById('modal-imagga-tags-container');

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

    // --- Gallery Card Click Logic ---
    const galleryCards = document.querySelectorAll('.history-gallery-card');
    galleryCards.forEach(card => {
        card.addEventListener('click', () => {

            currentHistoryId = card.dataset.id; // Store the ID

            // --- NEW: Setup Download Button Action ---
            if (modalDownloadBtn) {
                modalDownloadBtn.onclick = () => {
                    if (currentHistoryId) {
                        // Trigger the download route
                        window.location.href = `/history/download_pdf/${currentHistoryId}`;
                    }
                };
            }

            // Get data
            const imageUrl = card.dataset.imageUrl;
            const timestamp = card.dataset.timestamp;
            const tags = card.dataset.tags.split(',').filter(Boolean);
            const isGenerated = card.dataset.isGenerated === 'true';

            let predictions = {};
            try { 
                predictions = JSON.parse(card.dataset.predictions); 
            } catch (e) { 
                console.error("Failed to parse predictions:", e); 
                predictions = { error: "Could not load details." }; 
            }

            // Populate basic info
            modalImage.src = imageUrl;
            modalTimestamp.textContent = isGenerated ? `Generated: ${timestamp}` : `Analyzed: ${timestamp}`;

            // Populate Tags
            modalTagsContainer.innerHTML = '';
            if (tags.length > 0) {
                tags.forEach(tag => {
                    const tagLink = document.createElement('a');
                    tagLink.className = 'tag';
                    tagLink.textContent = tag;
                    tagLink.href = `/history?search=${encodeURIComponent(tag)}`;
                    modalTagsContainer.appendChild(tagLink);
                });
            }

            // --- HIDE ALL DETAIL SECTIONS INITIALLY ---
            modalMetadataSection.classList.add('hidden');
            modalGenInfoSection.classList.add('hidden');
            modalGeminiSection.classList.add('hidden');
            modalOcrSection.classList.add('hidden');
            modalYoloSection.classList.add('hidden');
            modalImaggaSection.classList.add('hidden');

            // --- SHOW MODAL BASED ON TYPE ---
            if (isGenerated) {
                // GENERATED IMAGE logic
                modalGenPrompt.textContent = predictions.prompt || "No prompt saved.";
                modalGenInfoSection.classList.remove('hidden');

                const tagLink = document.createElement('a');
                tagLink.className = 'tag tag-gemini';
                tagLink.textContent = 'AI Generated';
                tagLink.href = '#';
                modalTagsContainer.appendChild(tagLink);

            } else {
                // ANALYZED IMAGE logic

                // --- METADATA/MAP BLOCK ---
                modalMetadataContent.innerHTML = '';
                modalMapContainer.innerHTML = '';
                modalMapContainer.classList.add('hidden');
                
                if (predictions.metadata) {
                    const metadata = predictions.metadata;
                    for (const sectionTitle in metadata) {
                        if (sectionTitle === 'gps_info') continue;

                        const section = metadata[sectionTitle];
                        const titleElement = document.createElement('h6');
                        titleElement.textContent = sectionTitle;
                        modalMetadataContent.appendChild(titleElement);
                        
                        const listElement = document.createElement('ul');
                        listElement.className = 'metadata-list';
                        for (const key in section) {
                            const listItem = document.createElement('li');
                            listItem.innerHTML = `<strong>${key}:</strong> ${section[key]}`;
                            listElement.appendChild(listItem);
                        }
                        modalMetadataContent.appendChild(listElement);
                    }

                    if (metadata.gps_info && metadata.gps_info.latitude && metadata.gps_info.longitude) {
                        const lat = metadata.gps_info.latitude;
                        const lng = metadata.gps_info.longitude;
                        const mapUrl = `https://maps.google.com/maps?q=${lat},${lng}&t=&z=15&ie=UTF8&iwloc=&output=embed`;
                        modalMapContainer.innerHTML = `<iframe width="100%" height="300" src="${mapUrl}" frameborder="0" scrolling="no" marginheight="0" marginwidth="0" style="border:0; border-radius: var(--pico-border-radius);"></iframe>`;
                        modalMapContainer.classList.remove('hidden');
                    }
                    modalMetadataSection.classList.remove('hidden');
                }

                // --- GEMINI BLOCK ---
                modalSdPromptsSection.classList.add('hidden');
                if (predictions.gemini) {
                    const gemini = predictions.gemini;
                    modalGeminiCaption.textContent = gemini.caption || '';
                    
                    // Render Summary using Markdown
                    modalGeminiSummary.innerHTML = marked.parse(gemini.summary || '');
                    
                    let detailedDescription = gemini.detailed_prompt || '';
                    let sdPrompts = '';
                    const promptMarker = '**Stable Diffusion Prompt Suggestions:**';
                    const markerIndex = detailedDescription.indexOf(promptMarker);

                    if (markerIndex !== -1) {
                        sdPrompts = detailedDescription.substring(markerIndex + promptMarker.length).trim();
                        detailedDescription = detailedDescription.substring(0, markerIndex).trim();
                        sdPrompts = sdPrompts.replace(/^\s*[\*\-]\s*/gm, '');
                    }
                    
                    // --- MARKDOWN RENDER FIX ---
                    modalGeminiDetailed.innerHTML = marked.parse(detailedDescription || 'N/A');

                    if (sdPrompts) {
                        modalSdPromptsContent.textContent = sdPrompts;
                        modalSdPromptsSection.classList.remove('hidden');
                    }
                    
                    if (gemini.social_post) {
                        modalGeminiSocial.textContent = gemini.social_post;
                        modalGeminiSocialDetails.parentNode.classList.remove('hidden');
                    } else {
                        modalGeminiSocialDetails.parentNode.classList.add('hidden');
                    }
                    modalGeminiSection.classList.remove('hidden');
                }

                // --- OCR BLOCK ---
                if (predictions.ocr && predictions.ocr.annotated_image_url && predictions.ocr.extracted_text) {
                    modalOcrAnnotatedImage.src = predictions.ocr.annotated_image_url;
                    modalOcrText.textContent = predictions.ocr.extracted_text;
                    modalOcrSection.classList.remove('hidden');
                }

                // --- YOLO BLOCK ---
                modalYoloGrid.innerHTML = '';
                if (predictions.yolo) {
                    for (const task in predictions.yolo) {
                        const result = predictions.yolo[task];
                        const yoloCard = document.createElement('div');
                        yoloCard.className = 'yolo-card';
                        let content = `<h5>${task.charAt(0).toUpperCase() + task.slice(1)}</h5>`;
                        
                        if (result.type === 'segmentation_data') {
                            content += `<img src="${result.plot_url}" alt="Segmentation Plot" class="zoomable">`;
                        }
                        else if (result.type === 'annotated_image') {
                            content += `<img src="${result.processed_image_url}" alt="Result for ${task}" class="zoomable">`;
                        }
                        else if (result.type === 'classification') {
                            content += `<p><strong>Class:</strong> ${result.class_name}<br><strong>Confidence:</strong> ${result.confidence}</p>`;
                        }
                        else if (result.type === 'error') {
                            content += `<p><small>Note: ${result.message}</small></p>`;
                        }

                        yoloCard.innerHTML = content;
                        modalYoloGrid.appendChild(yoloCard);
                    }
                    modalYoloSection.classList.remove('hidden');
                }

                // --- IMAGGA BLOCK ---
                modalImaggaTagsContainer.innerHTML = '';
                if (predictions.imagga && Array.isArray(predictions.imagga) && predictions.imagga.length > 0) {
                    predictions.imagga.forEach(tag => {
                        const tagElement = document.createElement('span');
                        tagElement.className = 'tag tag-imagga';
                        tagElement.textContent = `${tag.name} (${tag.confidence}%)`;
                        modalImaggaTagsContainer.appendChild(tagElement);
                    });
                    modalImaggaSection.classList.remove('hidden');
                }
            }

            // Show modal
            historyModal.classList.remove('hidden');
        });
    });

    // --- Modal Close Logic ---
    function closeModal() {
        historyModal.classList.add('hidden');
        currentHistoryId = null;
    }
    historyModalClose.addEventListener('click', (e) => { e.preventDefault(); closeModal(); });
    historyModal.addEventListener('click', (e) => { if (e.target.id === 'history-modal-backdrop') closeModal(); });

    // --- Global Zoom Logic ---
    if (zoomModal) { 
        document.addEventListener('click', (e) => { 
            const zoomableTarget = e.target.closest('.zoomable'); 
            if (zoomableTarget) { 
                if (zoomableTarget.closest('#history-modal-content')) {
                    zoomModal.style.zIndex = "4000"; 
                } else {
                    zoomModal.style.zIndex = "3000"; 
                }
                zoomImg.src = zoomableTarget.src; 
                zoomModal.classList.remove('hidden'); 
            } 
            if (e.target.id === 'zoom-modal-backdrop') { 
                zoomModal.classList.add('hidden'); 
                zoomImg.src = ''; 
            } 
        }); 
    }

    // --- Delete Button Logic ---
    if (modalDeleteBtn) {
        modalDeleteBtn.addEventListener('click', async () => {
            if (!currentHistoryId) {
                alert('Error: No history item selected.');
                return;
            }

            if (!confirm('Are you sure you want to permanently delete this entry? This will also delete all associated image files.')) {
                return;
            }

            try {
                const response = await fetch('/delete_history', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ id: currentHistoryId })
                });

                const data = await response.json();
                if (!response.ok) {
                    throw new Error(data.error || 'Failed to delete entry.');
                }

                alert('Entry deleted successfully.');
                const cardToRemove = document.querySelector(`.history-gallery-card[data-id="${currentHistoryId}"]`);
                if (cardToRemove) {
                    cardToRemove.remove();
                }
                closeModal();

            } catch (error) {
                alert(`Error: ${error.message}`);
            }
        });
    }

});
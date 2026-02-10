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

    // Caption Section (in Overview tab)
    const modalCaptionSection = document.getElementById('modal-caption-section');

    // Q&A Empty States
    const qaEmptyState = document.getElementById('qa-empty-state');
    const analysisEmptyState = document.getElementById('analysis-empty-state');

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

    // --- Tab Navigation Logic ---
    const modalTabBtns = document.querySelectorAll('.modal-tab-btn');
    const modalTabPanes = document.querySelectorAll('.modal-tab-pane');

    modalTabBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            const targetTab = btn.dataset.tab;

            // Update active button
            modalTabBtns.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');

            // Update active pane
            modalTabPanes.forEach(pane => {
                if (pane.id === `tab-${targetTab}`) {
                    pane.classList.add('active');
                    pane.classList.remove('hidden');
                } else {
                    pane.classList.remove('active');
                    pane.classList.add('hidden');
                }
            });
        });
    });

    // --- Custom Tag Addition Logic ---
    const customTagInput = document.getElementById('custom-tag-input');
    const addCustomTagBtn = document.getElementById('add-custom-tag-btn');

    if (addCustomTagBtn && customTagInput) {
        addCustomTagBtn.addEventListener('click', async () => {
            const tagName = customTagInput.value.trim().toLowerCase();
            if (!tagName || !currentHistoryId) {
                return;
            }

            try {
                addCustomTagBtn.setAttribute('aria-busy', 'true');
                addCustomTagBtn.disabled = true;

                const response = await fetch('/history/add_tag', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        history_id: currentHistoryId,
                        tag_name: tagName
                    })
                });

                const data = await response.json();

                if (response.ok && data.success) {
                    // Add the tag to the display
                    const tagLink = document.createElement('a');
                    tagLink.className = 'tag';
                    tagLink.textContent = tagName;
                    tagLink.href = `/history?search=${encodeURIComponent(tagName)}`;
                    modalTagsContainer.appendChild(tagLink);

                    customTagInput.value = '';
                } else {
                    console.error('Failed to add tag:', data.error);
                }
            } catch (error) {
                console.error('Error adding tag:', error);
            } finally {
                addCustomTagBtn.setAttribute('aria-busy', 'false');
                addCustomTagBtn.disabled = false;
            }
        });

        // Allow Enter key to add tag
        customTagInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                e.preventDefault();
                addCustomTagBtn.click();
            }
        });
    }

    // Function to reset tabs to Overview
    function resetTabsToOverview() {
        modalTabBtns.forEach(b => {
            if (b.dataset.tab === 'overview') {
                b.classList.add('active');
            } else {
                b.classList.remove('active');
            }
        });
        modalTabPanes.forEach(pane => {
            if (pane.id === 'tab-overview') {
                pane.classList.add('active');
                pane.classList.remove('hidden');
            } else {
                pane.classList.remove('active');
                pane.classList.add('hidden');
            }
        });
    }

    // --- Filter Buttons Logic ---
    const filterButtons = document.querySelectorAll('.filter-btn');
    const allCards = document.querySelectorAll('.history-gallery-card');

    // --- Calculate and display Analyzed/Generated counts ---
    const analyzedCountEl = document.getElementById('analyzed-count');
    const generatedCountEl = document.getElementById('generated-count');
    if (analyzedCountEl && generatedCountEl) {
        let analyzedCount = 0;
        let generatedCount = 0;
        allCards.forEach(card => {
            if (card.dataset.filterType === 'generated') {
                generatedCount++;
            } else {
                analyzedCount++;
            }
        });
        analyzedCountEl.textContent = analyzedCount;
        generatedCountEl.textContent = generatedCount;
    }

    filterButtons.forEach(btn => {
        btn.addEventListener('click', () => {
            const filterType = btn.dataset.filter;

            // Update active button
            filterButtons.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');

            // Filter cards
            allCards.forEach(card => {
                const cardType = card.dataset.filterType;
                if (filterType === 'all' || cardType === filterType) {
                    card.style.display = '';
                } else {
                    card.style.display = 'none';
                }
            });
        });
    });

    // --- Gallery Card Click Logic (Redirect to Details Page) ---
    const galleryCards = document.querySelectorAll('.history-gallery-card');
    galleryCards.forEach(card => {
        card.addEventListener('click', () => {
            const historyId = card.dataset.id;
            if (historyId) {
                window.location.href = `/history/${historyId}`;
            }
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

    // --- Clear All History Button Logic ---
    const clearAllBtn = document.getElementById('clear-all-history-btn');
    if (clearAllBtn) {
        clearAllBtn.addEventListener('click', async () => {
            const cardCount = document.querySelectorAll('.history-gallery-card').length;

            if (cardCount === 0) {
                alert('No history to clear.');
                return;
            }

            if (!confirm(`Are you sure you want to permanently delete ALL ${cardCount} history entries? This cannot be undone.`)) {
                return;
            }

            try {
                const response = await fetch('/clear_all_history', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' }
                });

                const data = await response.json();
                if (!response.ok) {
                    throw new Error(data.error || 'Failed to clear history.');
                }

                alert(data.message || 'History cleared successfully.');
                window.location.reload();

            } catch (error) {
                alert(`Error: ${error.message}`);
            }
        });
    }

    // --- Multi-Select Mode Logic ---
    const toggleSelectBtn = document.getElementById('toggle-select-mode');
    const deleteSelectedBtn = document.getElementById('delete-selected-btn');
    const selectedCountEl = document.getElementById('selected-count');
    const cardCheckboxes = document.querySelectorAll('.card-select-checkbox');
    let selectModeActive = false;

    function updateSelectedCount() {
        const checkedCount = document.querySelectorAll('.card-select-checkbox:checked').length;
        selectedCountEl.textContent = checkedCount;

        if (checkedCount > 0) {
            deleteSelectedBtn.classList.remove('hidden');
        } else {
            deleteSelectedBtn.classList.add('hidden');
        }
    }

    if (toggleSelectBtn) {
        toggleSelectBtn.addEventListener('click', () => {
            selectModeActive = !selectModeActive;

            if (selectModeActive) {
                toggleSelectBtn.classList.add('active');
                toggleSelectBtn.innerHTML = '<i class="fa-solid fa-xmark"></i> Cancel';
                cardCheckboxes.forEach(cb => cb.classList.remove('hidden'));
                // Disable card click navigation in select mode
                allCards.forEach(card => card.classList.add('select-mode'));
            } else {
                toggleSelectBtn.classList.remove('active');
                toggleSelectBtn.innerHTML = '<i class="fa-regular fa-square-check"></i> Select';
                cardCheckboxes.forEach(cb => {
                    cb.classList.add('hidden');
                    cb.checked = false;
                });
                deleteSelectedBtn.classList.add('hidden');
                allCards.forEach(card => card.classList.remove('select-mode'));
            }
            updateSelectedCount();
        });
    }

    cardCheckboxes.forEach(cb => {
        cb.addEventListener('change', updateSelectedCount);
    });

    // Override card click when in select mode
    allCards.forEach(card => {
        card.addEventListener('click', (e) => {
            if (selectModeActive) {
                e.preventDefault();
                e.stopPropagation();
                const checkbox = card.querySelector('.card-select-checkbox');
                if (checkbox && e.target !== checkbox) {
                    checkbox.checked = !checkbox.checked;
                    updateSelectedCount();
                }
                return false;
            }
        }, true);
    });

    // Bulk delete selected
    if (deleteSelectedBtn) {
        deleteSelectedBtn.addEventListener('click', async () => {
            const checkedBoxes = document.querySelectorAll('.card-select-checkbox:checked');
            const ids = Array.from(checkedBoxes).map(cb => parseInt(cb.value));

            if (ids.length === 0) return;

            if (!confirm(`Delete ${ids.length} selected item(s)? This cannot be undone.`)) return;

            deleteSelectedBtn.disabled = true;
            deleteSelectedBtn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Deleting...';

            try {
                const response = await fetch('/delete_history_bulk', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ ids: ids })
                });

                const data = await response.json();
                if (!response.ok) {
                    throw new Error(data.error || 'Failed to delete items.');
                }

                alert(`Deleted ${data.deleted} item(s).`);
                window.location.reload();
            } catch (error) {
                alert(`Error: ${error.message}`);
                deleteSelectedBtn.disabled = false;
                deleteSelectedBtn.innerHTML = `<i class="fa-solid fa-trash-can"></i> Delete (${ids.length})`;
            }
        });
    }

});
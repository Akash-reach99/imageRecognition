// static/edit.js
document.addEventListener('DOMContentLoaded', () => {
    
    // --- Page Elements ---
    const uploadArticle = document.getElementById('upload-article-edit');
    const editResultsSection = document.getElementById('edit-results-section');
    const fileInput = document.getElementById('file');
    const fileInputLabel = document.getElementById('file-input-filename');
    const dropZone = document.querySelector('.drop-zone');
    const startOverBtn = document.getElementById('start-over-edit-btn');
    const themeSwitcher = document.getElementById('theme-switcher');

    // --- Results Elements ---
    const imageBefore = document.getElementById('image-before');
    const imageAfter = document.getElementById('image-after');
    const imageAfterPlaceholder = document.getElementById('image-after-placeholder');
    const downloadBtn = document.getElementById('download-edited-btn');

    // --- Global Elements ---
    const globalLoader = document.getElementById('global-loader-container');
    const errorMessage = document.getElementById('error-message');
    const zoomModal = document.getElementById('zoom-modal-backdrop');
    const zoomImg = document.getElementById('zoom-modal-img');

    let selectedFile = null;

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

    // --- File Selection ---
    if (fileInput) {
        fileInput.addEventListener('change', (e) => {
            if (e.target.files && e.target.files.length > 0) {
                handleFileSelect(e.target.files[0]);
            }
        });
    }

    // This is the main function
    function handleFileSelect(file) {
        selectedFile = file;
        const previewUrl = URL.createObjectURL(file);
        
        if (fileInputLabel) fileInputLabel.textContent = file.name;
        imageBefore.src = previewUrl;
        
        // Hide upload and show results
        uploadArticle.classList.add('hidden');
        editResultsSection.classList.remove('hidden');
        
        // Reset results area
        imageAfter.classList.add('hidden');
        imageAfter.src = '';
        imageAfterPlaceholder.classList.remove('hidden');
        downloadBtn.classList.add('hidden');
        errorMessage.classList.add('hidden');

        // Automatically start the background removal process
        performBackgroundRemoval();
    }

    async function performBackgroundRemoval() {
        if (!selectedFile) {
            alert("No file selected.");
            return;
        }

        globalLoader.classList.remove('hidden');
        
        const formData = new FormData();
        formData.append('file', selectedFile);

        try {
            const response = await fetch('/edit/remove-bg', {
                method: 'POST',
                body: formData
            });

            const data = await response.json();
            if (!response.ok) {
                throw new Error(data.error || 'Failed to remove background.');
            }

            // Success! Display the new image
            imageAfter.src = data.processed_image_url;
            imageAfter.classList.remove('hidden');
            imageAfterPlaceholder.classList.add('hidden');
            
            downloadBtn.href = data.processed_image_url;
            downloadBtn.download = data.filename;
            downloadBtn.classList.remove('hidden');

        } catch (error) {
            errorMessage.textContent = `Error: ${error.message}`;
            errorMessage.classList.remove('hidden');
        } finally {
            globalLoader.classList.add('hidden');
        }
    }


    // --- Start Over ---
    if (startOverBtn) {
        startOverBtn.addEventListener('click', () => {
            uploadArticle.classList.remove('hidden');
            editResultsSection.classList.add('hidden');
            fileInput.value = '';
            if (fileInputLabel) fileInputLabel.textContent = 'No file selected';
            imageBefore.src = '';
            imageAfter.src = '';
            selectedFile = null;
        });
    }

    // --- Global Zoom Logic ---
    if (zoomModal) {
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
    }
});
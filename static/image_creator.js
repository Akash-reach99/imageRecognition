document.addEventListener('DOMContentLoaded', () => {
    const textToImageForm = document.getElementById('text-to-image-form');
    const promptInput = document.getElementById('prompt');
    const generateImageBtn = document.getElementById('generate-image-btn');
    const generationLoader = document.getElementById('generation-loader');
    const generationError = document.getElementById('generation-error');
    const generatedImagePreview = document.getElementById('generated-image-preview');
    const generatedImageDisplay = document.getElementById('generated-image-display');
    const downloadGeneratedImageBtn = document.getElementById('download-generated-image-btn');
    const editGeneratedImageBtn = document.getElementById('edit-generated-image-btn');

    const imageEditorSection = document.getElementById('image-editor-section');
    const canvas = document.getElementById('image-editor-canvas');
    const ctx = canvas.getContext('2d');
    const textOverlayInput = document.getElementById('text-overlay-input');
    const textColorInput = document.getElementById('text-color');
    const textSizeInput = document.getElementById('text-size');
    const addTextBtn = document.getElementById('add-text-btn');
    const filterSelect = document.getElementById('filter-select');
    const applyFilterBtn = document.getElementById('apply-filter-btn');
    const resetEditorBtn = document.getElementById('reset-editor-btn');
    const downloadEditedImageBtn = document.getElementById('download-edited-image-btn');

    let originalImage = new Image(); // Stores the original generated image for reset
    let currentImageSrc = ''; // Stores the URL of the current image being edited

    // --- Text-to-Image Generation ---
    if (textToImageForm) {
        textToImageForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const prompt = promptInput.value.trim();
            if (!prompt) {
                generationError.textContent = 'Please enter a prompt.';
                generationError.classList.remove('hidden');
                return;
            }

            generatedImagePreview.classList.add('hidden');
            generationError.classList.add('hidden');
            generationLoader.classList.remove('hidden');
            imageEditorSection.classList.add('hidden'); // Hide editor until image is ready

            try {
                const response = await fetch('/generate_image', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ prompt })
                });

                const data = await response.json();
                if (!response.ok) {
                    throw new Error(data.error || 'Failed to generate image.');
                }

                currentImageSrc = data.image_url;
                generatedImageDisplay.src = currentImageSrc;
                generatedImagePreview.classList.remove('hidden');

                // Load image into editor for potential editing
                originalImage.onload = () => {
                    // Set canvas dimensions to image dimensions
                    canvas.width = originalImage.width;
                    canvas.height = originalImage.height;
                    drawCanvasImage(originalImage); // Draw original image to canvas
                };
                originalImage.src = currentImageSrc;


            } catch (error) {
                generationError.textContent = `Error: ${error.message}`;
                generationError.classList.remove('hidden');
            } finally {
                generationLoader.classList.add('hidden');
            }
        });
    }

    // --- Image Editing Functions ---

    // Function to draw the image on the canvas
    function drawCanvasImage(img, filters = []) {
        ctx.clearRect(0, 0, canvas.width, canvas.height); // Clear canvas first
        ctx.drawImage(img, 0, 0, canvas.width, canvas.height);

        // Apply filters if any (this is a simplified example)
        if (filters.length > 0) {
            const imageData = ctx.getImageData(0, 0, canvas.width, canvas.height);
            const pixels = imageData.data;

            for (let i = 0; i < pixels.length; i += 4) {
                const r = pixels[i];
                const g = pixels[i + 1];
                const b = pixels[i + 2];

                if (filters.includes('grayscale')) {
                    const gray = (r + g + b) / 3;
                    pixels[i] = gray;
                    pixels[i + 1] = gray;
                    pixels[i + 2] = gray;
                }
                if (filters.includes('sepia')) {
                    pixels[i] = Math.min(255, (r * 0.393) + (g * 0.769) + (b * 0.189));
                    pixels[i + 1] = Math.min(255, (r * 0.349) + (g * 0.686) + (b * 0.168));
                    pixels[i + 2] = Math.min(255, (r * 0.272) + (g * 0.534) + (b * 0.131));
                }
                if (filters.includes('invert')) {
                    pixels[i] = 255 - r;
                    pixels[i + 1] = 255 - g;
                    pixels[i + 2] = 255 - b;
                }
            }
            ctx.putImageData(imageData, 0, 0);
        }
    }

    // Event listener to show editor
    if (editGeneratedImageBtn) {
        editGeneratedImageBtn.addEventListener('click', () => {
            if (currentImageSrc) {
                imageEditorSection.classList.remove('hidden');
                originalImage.onload = () => {
                    canvas.width = originalImage.width;
                    canvas.height = originalImage.height;
                    drawCanvasImage(originalImage);
                };
                originalImage.src = currentImageSrc; // Reload to ensure clean slate for editing
            } else {
                alert('Please generate an image first.');
            }
        });
    }

    // Add Text Overlay
    if (addTextBtn) {
        addTextBtn.addEventListener('click', () => {
            const text = textOverlayInput.value.trim();
            if (!text || !currentImageSrc) return;

            // Redraw original image (or current state) before adding new text
            drawCanvasImage(originalImage, currentFilters); // Ensure filters are applied if any
            ctx.fillStyle = textColorInput.value;
            ctx.font = `${textSizeInput.value}px sans-serif`;

            // Simple placement - can be improved with drag-and-drop
            const textX = 20;
            const textY = parseInt(textSizeInput.value) + 20; // Some padding from top
            ctx.fillText(text, textX, textY);
        });
    }

    let currentFilters = []; // To keep track of applied filters

    // Apply Filter
    if (applyFilterBtn) {
        applyFilterBtn.addEventListener('click', () => {
            if (!currentImageSrc) {
                alert('Please generate an image first.');
                return;
            }
            const selectedFilter = filterSelect.value;
            if (selectedFilter !== 'none') {
                 currentFilters = [selectedFilter]; // Only one filter for simplicity
            } else {
                 currentFilters = [];
            }
            drawCanvasImage(originalImage, currentFilters); // Redraw with new filters
        });
    }


    // Reset Editor
    if (resetEditorBtn) {
        resetEditorBtn.addEventListener('click', () => {
            if (currentImageSrc) {
                currentFilters = []; // Clear all filters
                drawCanvasImage(originalImage); // Redraw just the original image
                textOverlayInput.value = ''; // Clear text input
                textColorInput.value = '#000000'; // Reset color
                textSizeInput.value = '30'; // Reset size
                filterSelect.value = 'none'; // Reset filter dropdown
            }
        });
    }

    // --- Download Functions ---
    if (downloadGeneratedImageBtn) {
        downloadGeneratedImageBtn.addEventListener('click', () => {
            if (currentImageSrc) {
                const link = document.createElement('a');
                link.href = currentImageSrc;
                link.download = `generated_image_${Date.now()}.png`;
                document.body.appendChild(link);
                link.click();
                document.body.removeChild(link);
            } else {
                alert('No image to download.');
            }
        });
    }

    if (downloadEditedImageBtn) {
        downloadEditedImageBtn.addEventListener('click', () => {
            if (canvas.width && canvas.height) {
                const link = document.createElement('a');
                link.download = `edited_image_${Date.now()}.png`;
                link.href = canvas.toDataURL('image/png'); // Get image data from canvas
                document.body.appendChild(link);
                link.click();
                document.body.removeChild(link);
            } else {
                alert('No edited image to download.');
            }
        });
    }

});
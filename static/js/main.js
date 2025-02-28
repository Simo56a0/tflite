document.addEventListener('DOMContentLoaded', function() {
    // DOM Elements
    const cameraButton = document.querySelector('.btn-primary');
    const captureButton = document.querySelector('.btn-accent');
    const translateButton = document.querySelector('button.btn-primary[style="width: 100%;"]');
    const videoFeed = document.querySelector('.video-feed');
    const fileInput = document.getElementById('file-input');
    const uploadArea = document.querySelector('.upload-area');
    const translationResult = document.querySelector('.translation-result');
    const copyButton = document.querySelector('.actions .btn-outline:first-child');
    const speechButton = document.querySelector('.actions .btn-outline:last-child');
    
    // New DOM Elements for Feature Extraction
    const featureFileInput = document.getElementById('feature-file-input');
    const featureUploadArea = document.querySelector('.feature-upload-area');
    const featureVideoPreview = document.getElementById('feature-video-preview');
    const featureExtractButton = document.getElementById('extract-features-btn');
    const featureResultBox = document.getElementById('feature-result-box');
    const featureResult = document.getElementById('feature-result');
    const featureProgressContainer = document.getElementById('feature-progress-container');
    const featureProgressBar = document.getElementById('feature-progress-bar');
    
    // Tab switching
    document.querySelectorAll('.toggle-btn').forEach(button => {
        button.addEventListener('click', () => {
            // Remove active class from all buttons and tabs
            document.querySelectorAll('.toggle-btn').forEach(btn => btn.classList.remove('active'));
            document.querySelectorAll('.tab-content').forEach(tab => tab.classList.remove('active'));
            
            // Add active class to clicked button and corresponding tab
            button.classList.add('active');
            document.getElementById(`${button.dataset.tab}-tab`).classList.add('active');
        });
    });
    
    // Global variables
    let stream = null;
    let videoElement = null;
    let capturedImage = null;
    let activeMode = 'camera'; // 'camera' or 'upload'
    let featureVideoFile = null; // Store the uploaded video file for feature extraction
    
    // Initialize video element
    function initializeVideo() {
        // Clear video feed div
        videoFeed.innerHTML = '';
        
        // Create video element
        videoElement = document.createElement('video');
        videoElement.style.width = '100%';
        videoElement.style.height = '100%';
        videoElement.style.objectFit = 'cover';
        videoElement.style.borderRadius = '10px';
        videoFeed.appendChild(videoElement);
        
        return videoElement;
    }
    
    // Start camera
    async function startCamera() {
        try {
            // Initialize video element if not already done
            if (!videoElement) {
                videoElement = initializeVideo();
            }
            
            // Get user media
            stream = await navigator.mediaDevices.getUserMedia({ 
                video: { 
                    width: { ideal: 1280 },
                    height: { ideal: 720 },
                    facingMode: 'user'
                } 
            });
            
            // Set video source
            videoElement.srcObject = stream;
            videoElement.play();
            
            // Update button text
            cameraButton.textContent = 'Stop Camera';
            cameraButton.classList.remove('btn-primary');
            cameraButton.classList.add('btn-outline');
            
            // Enable capture button
            captureButton.disabled = false;
            
        } catch (error) {
            console.error('Error accessing camera:', error);
            translationResult.innerHTML = `<p class="error">Error accessing camera: ${error.message}</p>`;
        }
    }
    
    // Stop camera
    function stopCamera() {
        if (stream) {
            stream.getTracks().forEach(track => track.stop());
            stream = null;
            
            if (videoElement) {
                videoElement.srcObject = null;
            }
            
            // Update button text
            cameraButton.textContent = 'Start Camera';
            cameraButton.classList.remove('btn-outline');
            cameraButton.classList.add('btn-primary');
            
            // Disable capture button
            captureButton.disabled = true;
        }
    }
    
    // Capture image from camera
    function captureImage() {
        if (!stream) return;
        
        // Create canvas element
        const canvas = document.createElement('canvas');
        canvas.width = videoElement.videoWidth;
        canvas.height = videoElement.videoHeight;
        
        // Draw video frame to canvas
        const ctx = canvas.getContext('2d');
        ctx.drawImage(videoElement, 0, 0, canvas.width, canvas.height);
        
        // Convert to base64
        capturedImage = canvas.toDataURL('image/jpeg');
        
        // Show captured image
        videoFeed.innerHTML = '';
        const img = document.createElement('img');
        img.src = capturedImage;
        img.style.width = '100%';
        img.style.height = '100%';
        img.style.objectFit = 'cover';
        img.style.borderRadius = '10px';
        videoFeed.appendChild(img);
        
        // Stop camera after capture
        stopCamera();
        
        // Enable translate button
        translateButton.disabled = false;
        
        // Set active mode
        activeMode = 'camera';
    }
    
    // Handle file upload
    function handleFileUpload(file) {
        if (!file) return;
        
        const reader = new FileReader();
        
        reader.onload = function(e) {
            // Store image data
            capturedImage = e.target.result;
            
            // Display image
            const img = document.createElement('img');
            img.src = capturedImage;
            img.style.width = '100%';
            img.style.height = '100%';
            img.style.objectFit = 'cover';
            img.style.borderRadius = '10px';
            
            // Replace upload area content with image
            uploadArea.innerHTML = '';
            uploadArea.appendChild(img);
            
            // Enable translate button
            translateButton.disabled = false;
            
            // Set active mode
            activeMode = 'upload';
        };
        
        reader.readAsDataURL(file);
    }
    
    // Translate sign language
    async function translateSign() {
        if (!capturedImage) {
            translationResult.innerHTML = '<p>Please capture or upload an image first.</p>';
            return;
        }
        
        try {
            // Show loading state
            translationResult.innerHTML = '<p>Analyzing sign language...</p>';
            
            let response;
            
            if (activeMode === 'camera') {
                // Send captured image data
                response = await fetch('/predict-from-camera', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        image: capturedImage
                    })
                });
            } else {
                // Send file upload
                const formData = new FormData();
                
                // Convert base64 to blob
                const base64Response = await fetch(capturedImage);
                const blob = await base64Response.blob();
                
                formData.append('file', blob, 'image.jpg');
                
                response = await fetch('/predict', {
                    method: 'POST',
                    body: formData
                });
            }
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const result = await response.json();
            
            // Show result
            if (result.error) {
                translationResult.innerHTML = `<p class="error">Error: ${result.error}</p>`;
            } else {
                translationResult.innerHTML = `
                    <h2 style="font-size: 36px; margin-bottom: 10px;">${result.class}</h2>
                    <p>Confidence: ${(result.confidence * 100).toFixed(2)}%</p>
                `;
                
                // Add to history (in a real app, this would be saved to a database)
                addToHistory(result.class, capturedImage);
            }
            
        } catch (error) {
            console.error('Translation error:', error);
            translationResult.innerHTML = `<p class="error">Translation error: ${error.message}</p>`;
        }
    }
    
    // Add to translation history
    function addToHistory(text, image) {
        const historyContainer = document.querySelector('.history-container');
        const historyItems = historyContainer.querySelectorAll('.history-item');
        
        // Create new history item
        const historyItem = document.createElement('div');
        historyItem.className = 'history-item';
        
        // Create thumbnail
        const thumbnail = document.createElement('div');
        thumbnail.className = 'history-thumbnail';
        thumbnail.style.backgroundImage = `url(${image})`;
        thumbnail.style.backgroundSize = 'cover';
        thumbnail.style.backgroundPosition = 'center';
        
        // Create text container
        const textContainer = document.createElement('div');
        textContainer.className = 'history-text';
        
        // Create text and timestamp
        const textElement = document.createElement('p');
        textElement.textContent = `"${text}"`;
        
        const timestamp = document.createElement('small');
        const now = new Date();
        timestamp.textContent = `Today, ${now.getHours()}:${now.getMinutes().toString().padStart(2, '0')} ${now.getHours() >= 12 ? 'PM' : 'AM'}`;
        
        // Assemble the history item
        textContainer.appendChild(textElement);
        textContainer.appendChild(timestamp);
        historyItem.appendChild(thumbnail);
        historyItem.appendChild(textContainer);
        
        // Add to history container (at the top)
        if (historyItems.length >= 5) {
            historyContainer.removeChild(historyItems[historyItems.length - 1]);
        }
        historyContainer.insertBefore(historyItem, historyItems[0]);
    }
    
    // Event Listeners
    cameraButton.addEventListener('click', () => {
        if (!stream) {
            startCamera();
        } else {
            stopCamera();
        }
    });
    
    captureButton.addEventListener('click', captureImage);
    
    translateButton.addEventListener('click', translateSign);
    
    // File input events
    fileInput.addEventListener('change', function() {
        const file = this.files[0];
        handleFileUpload(file);
    });
    
    // Feature extraction functionality
    featureFileInput.addEventListener('change', function() {
        const file = this.files[0];
        featureVideoFile = file;
        featureUploadArea.textContent = `Video file selected: ${file.name}`;
    });

    featureExtractButton.addEventListener('click', async function() {
        if (!featureVideoFile) {
            featureResultBox.style.display = 'none';
            featureProgressContainer.style.display = 'block';
            featureProgressBar.style.width = '100%';
            return;
        }

        featureProgressContainer.style.display = 'block';
        featureProgressBar.style.width = '20%';
        
        try {
            const formData = new FormData();
            formData.append('file', featureVideoFile);
            
            const response = await fetch('/extract-features', {
                method: 'POST',
                body: formData
            });
            
            if (!response.ok) {
                throw new Error('Failed to extract features');
            }
            
            const data = await response.json();
            
            // Update progress bar and show features
            featureProgressBar.style.width = '100%';
            featureProgressContainer.style.display = 'none';
            featureResultBox.style.display = 'block';
            
            if (data.features) {
                featureResult.innerHTML = `<pre>${JSON.stringify(data.features, null, 2)}</pre>`;
            }
            
        } catch (error) {
            console.error('Feature extraction error:', error);
            featureProgressBar.style.width = '100%';
            featureProgressContainer.style.display = 'none';
            featureResultBox.style.display = 'block';
            featureResult.innerHTML = `<p class="error">Error: ${error.message}</p>`;
        }
    });
});

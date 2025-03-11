document.addEventListener('DOMContentLoaded', function() {
    // DOM Elements
    const cameraButton = document.getElementById('startWebcamBtn');
    const captureButton = document.querySelector('.btn-accent');
    const translateButton = document.getElementById('translate-button');
    const videoFeed = document.querySelector('.video-feed');
    const fileInput = document.getElementById('file-input');
    const videoInput = document.getElementById('video-input');
    const translationResult = document.getElementById('translation-result');
    const copyButton = document.getElementById('copy-text-btn');
    const speechButton = document.getElementById('text-to-speech-btn');
    const videoPreview = document.getElementById('videoPreview');
    let stream = null;
    let videoElement = null;
    
    function initializeVideo() {
        videoFeed.innerHTML = '';
        videoElement = document.createElement('video');
        videoElement.style.width = '100%';
        videoElement.style.height = '100%';
        videoElement.setAttribute('autoplay', '');
        videoFeed.appendChild(videoElement);
        return videoElement;
    }
    
    async function startCamera() {
        try {
            if (!videoElement) {
                videoElement = initializeVideo();
            }
            stream = await navigator.mediaDevices.getUserMedia({ video: true });
            videoElement.srcObject = stream;
        } catch (error) {
            console.error('Error accessing camera:', error);
        }
    }
    
    function stopCamera() {
        if (stream) {
            stream.getTracks().forEach(track => track.stop());
            stream = null;
            videoElement.srcObject = null;
        }
    }
    
    function captureImage() {
        if (!stream) return;
        const canvas = document.createElement('canvas');
        canvas.width = videoElement.videoWidth;
        canvas.height = videoElement.videoHeight;
        const ctx = canvas.getContext('2d');
        ctx.drawImage(videoElement, 0, 0, canvas.width, canvas.height);
        const capturedImage = canvas.toDataURL('image/jpeg');
        sendFrameToBackend(capturedImage);
    }
    
    async function sendFrameToBackend(frame) {
        try {
            const response = await fetch('/webcam-predict', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ frame })
            });
            const data = await response.json();
            displayResult(data);
        } catch (error) {
            console.error('Error:', error);
        }
    }
    
    function displayResult(result) {
        if (result.error) {
            translationResult.innerHTML = `<p class='error'>Error: ${result.error}</p>`;
        } else {
            translationResult.innerHTML = `<h2>${result.class}</h2><p>Confidence: ${(result.confidence * 100).toFixed(2)}%</p>`;
        }
    }
    
    videoInput.addEventListener('change', async function(event) {
        const file = event.target.files[0];
        if (file) {
            const formData = new FormData();
            formData.append('file', file);
            const response = await fetch('/predict-video', {
                method: 'POST',
                body: formData
            });
            const data = await response.json();
            displayResult(data);
        }
    });
    
    cameraButton.addEventListener('click', startCamera);
    captureButton.addEventListener('click', captureImage);
    translateButton.addEventListener('click', captureImage);
    copyButton.addEventListener('click', function() {
        navigator.clipboard.writeText(translationResult.textContent.trim());
        alert('Text copied to clipboard!');
    });
    speechButton.addEventListener('click', function() {
        const text = translationResult.textContent.trim();
        if (text && window.speechSynthesis) {
            const utterance = new SpeechSynthesisUtterance(text);
            window.speechSynthesis.speak(utterance);
        }
    });
});

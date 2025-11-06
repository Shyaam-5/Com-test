// static/moduleA.js - Enhanced with countdown and recording time

const MAX_QUESTIONS = 10;
const COUNTDOWN_DURATION = 4; // 4 seconds before recording starts

let questionCount = 0;
let currentSentenceId = null;
let mediaRecorder = null;
let audioChunks = [];
let isRecording = false;
let audioStream = null;
let countdownTimer = null;
let recordingTimer = null;
let recordingStartTime = null;

document.addEventListener('DOMContentLoaded', () => {
    loadSentence();
    checkMicrophonePermission();
});

async function checkMicrophonePermission() {
    if (!navigator.mediaDevices) {
        console.warn('MediaDevices API not available - use HTTPS or localhost');
        return;
    }
    try {
        if (navigator.permissions && navigator.permissions.query) {
            const permissionStatus = await navigator.permissions.query({ name: 'microphone' });
            if (permissionStatus.state === 'denied') {
                showNotification('Microphone access is required for this module', 'error');
            }
        }
    } catch (error) {
        console.log('Permission API not supported');
    }
}

async function loadSentence() {
    if (questionCount >= MAX_QUESTIONS) {
        goToNextModule();
        return;
    }

    try {
        showLoading(true);
        const response = await fetch('/api/moduleA/sentence', {
            method: 'GET',
            credentials: 'same-origin'
        });

        if (response.status === 401) {
            window.location.href = '/login';
            return;
        }

        const data = await response.json();

        if (data.success) {
            currentSentenceId = data.sentence_id;
            document.getElementById('sentence').textContent = data.sentence;
            
            questionCount++;
            updateProgressUI();
            
            closeResults();
            resetUI();
        } else {
            showNotification('Failed to load sentence: ' + (data.error || 'Unknown error'), 'error');
        }
    } catch (error) {
        console.error('Load sentence error:', error);
        showNotification('Network error. Please check your connection.', 'error');
    } finally {
        showLoading(false);
    }
}

async function toggleRecording() {
    if (!isRecording) {
        await startCountdown();
    } else {
        await stopRecording();
    }
}

async function startCountdown() {
    // Hide button, show countdown
    document.getElementById('recordButtonWrapper').style.display = 'none';
    document.getElementById('countdownDisplay').style.display = 'block';
    
    let timeLeft = COUNTDOWN_DURATION;
    document.getElementById('countdownNumber').textContent = timeLeft;
    
    countdownTimer = setInterval(() => {
        timeLeft--;
        if (timeLeft > 0) {
            document.getElementById('countdownNumber').textContent = timeLeft;
        } else {
            clearInterval(countdownTimer);
            document.getElementById('countdownDisplay').style.display = 'none';
            startRecording();
        }
    }, 1000);
}

async function startRecording() {
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
        showNotification(
            'Microphone access requires HTTPS or localhost. Please access via https:// or http://localhost:5000',
            'error'
        );
        resetUI();
        return;
    }

    try {
        audioStream = await navigator.mediaDevices.getUserMedia({
            audio: {
                echoCancellation: true,
                noiseSuppression: true,
                sampleRate: 44100
            }
        });

        const mimeType = MediaRecorder.isTypeSupported('audio/webm') ? 'audio/webm' : 'audio/ogg';
        mediaRecorder = new MediaRecorder(audioStream, { mimeType });
        audioChunks = [];

        mediaRecorder.ondataavailable = (event) => {
            if (event.data.size > 0) {
                audioChunks.push(event.data);
            }
        };

        mediaRecorder.onstop = async () => {
            const audioBlob = new Blob(audioChunks, { type: 'audio/wav' });
            await submitAudio(audioBlob);
            
            if (audioStream) {
                audioStream.getTracks().forEach(track => track.stop());
                audioStream = null;
            }
        };

        mediaRecorder.start();
        isRecording = true;
        recordingStartTime = Date.now();

        // Show waveform animation
        document.getElementById('waveformContainer').style.display = 'block';
        
        // Start recording time display
        updateRecordingTime();

        console.log('Recording started');

    } catch (error) {
        console.error('Start recording error:', error);
        if (error.name === 'NotAllowedError' || error.name === 'PermissionDeniedError') {
            showNotification('Microphone access denied. Please allow microphone access.', 'error');
        } else if (error.name === 'NotFoundError') {
            showNotification('No microphone found. Please connect a microphone.', 'error');
        } else {
            showNotification('Could not start recording: ' + error.message, 'error');
        }
        resetUI();
    }
}

function updateRecordingTime() {
    if (!isRecording) return;
    
    const elapsed = Math.floor((Date.now() - recordingStartTime) / 1000);
    const minutes = Math.floor(elapsed / 60);
    const seconds = elapsed % 60;
    document.getElementById('recordingTime').textContent = 
        `${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
    
    recordingTimer = setTimeout(updateRecordingTime, 1000);
}

async function stopRecording() {
    if (mediaRecorder && isRecording) {
        isRecording = false;
        
        if (recordingTimer) {
            clearTimeout(recordingTimer);
            recordingTimer = null;
        }

        // Hide waveform, show processing state
        document.getElementById('waveformContainer').style.display = 'none';
        document.getElementById('recordButtonWrapper').style.display = 'flex';
        
        const btn = document.getElementById('recordBtn');
        const text = document.getElementById('recordText');
        text.textContent = 'Processing...';
        btn.disabled = true;

        mediaRecorder.stop();
        console.log('Recording stopped');
    }
}

async function submitAudio(audioBlob) {
    const formData = new FormData();
    formData.append('audio', audioBlob, 'recording.wav');
    formData.append('sentence_id', currentSentenceId);

    try {
        const response = await fetch('/api/moduleA', {
            method: 'POST',
            body: formData,
            credentials: 'same-origin'
        });

        if (response.status === 401) {
            window.location.href = '/login';
            return;
        }

        const result = await response.json();

        if (result.success) {
            displayResults(result);
        } else {
            showNotification('Processing failed: ' + (result.error || 'Unknown error'), 'error');
        }

    } catch (error) {
        console.error('Submit audio error:', error);
        showNotification('Failed to process audio. Please try again.', 'error');
    } finally {
        resetUI();
    }
}

function displayResults(result) {
    const score = Math.round(result.score || result.pronunciation_score || 0);
    document.getElementById('score').textContent = score;

    const transcription = result.transcription || result.transcribed_text || 'No transcription available';
    document.getElementById('transcription').textContent = transcription;

    const feedback = result.feedback || 'No feedback available';
    document.getElementById('feedback').textContent = feedback;

    document.getElementById('results').style.display = 'flex';
       setTimeout(() => {
        closeResults();
        nextSentence();
    }, 5000);
}

function closeResults() {
    document.getElementById('results').style.display = 'none';
}

function nextSentence() {
    loadSentence();
}

function resetUI() {
    const btn = document.getElementById('recordBtn');
    const text = document.getElementById('recordText');
    
    btn.disabled = false;
    text.textContent = 'Start Speaking';
    isRecording = false;
    
    // Hide countdown and waveform
    document.getElementById('countdownDisplay').style.display = 'none';
    document.getElementById('waveformContainer').style.display = 'none';
    document.getElementById('recordButtonWrapper').style.display = 'flex';
    
    // Clear timers
    if (countdownTimer) {
        clearInterval(countdownTimer);
        countdownTimer = null;
    }
    if (recordingTimer) {
        clearTimeout(recordingTimer);
        recordingTimer = null;
    }
}

function showLoading(show) {
    const sentenceEl = document.getElementById('sentence');
    if (show) {
        sentenceEl.textContent = 'Loading...';
        sentenceEl.style.opacity = '0.5';
    } else {
        sentenceEl.style.opacity = '1';
    }
}

function showNotification(message, type = 'info') {
    console.log(`[${type.toUpperCase()}]`, message);
    alert(message);
}

function updateProgressUI() {
    const pill = document.getElementById('progress-pill');
    if (pill) {
        pill.style.display = 'block';
        pill.textContent = `${questionCount}/${MAX_QUESTIONS}`;
    }
}

function goToNextModule() {
    const proceed = confirm('Great job! You completed Module A (Read & Speak).\n\nReady to move to Module B (Listen & Repeat)?');
    if (proceed) {
        window.location.href = '/moduleB';
    }
}

window.addEventListener('beforeunload', (event) => {
    if (isRecording) {
        event.preventDefault();
        event.returnValue = 'Recording in progress';
        return event.returnValue;
    }
});

window.addEventListener('unload', () => {
    if (audioStream) {
        audioStream.getTracks().forEach(track => track.stop());
    }
    if (countdownTimer) clearInterval(countdownTimer);
    if (recordingTimer) clearTimeout(recordingTimer);
});

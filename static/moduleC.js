// static/moduleC.js - Topic Speaking Module

const MAX_QUESTIONS = 5;  // Only 5 topics for this module
const RECORDING_DURATION = 120; // 2 minutes in seconds

let questionCount = 0;
let currentTopicId = null;
let currentTopic = '';
let mediaRecorder = null;
let audioChunks = [];
let isRecording = false;
let audioStream = null;
let recordingTimer = null;
let timeRemaining = RECORDING_DURATION;

document.addEventListener('DOMContentLoaded', () => {
    loadTopic();
    checkMicrophonePermission();
});

async function checkMicrophonePermission() {
    if (!navigator.mediaDevices) {
        console.warn('MediaDevices API not available');
        return;
    }
    try {
        if (navigator.permissions && navigator.permissions.query) {
            const permissionStatus = await navigator.permissions.query({ name: 'microphone' });
            if (permissionStatus.state === 'denied') {
                showNotification('Microphone access is required', 'error');
            }
        }
    } catch (error) {
        console.log('Permission API not supported');
    }
}

async function loadTopic() {
    // Check if completed 5 topics
    if (questionCount >= MAX_QUESTIONS) {
        goToNextModule();
        return;
    }

    try {
        showLoading(true);
        const response = await fetch('/api/moduleC/topic', {
            method: 'GET',
            credentials: 'same-origin'
        });

        if (response.status === 401) {
            window.location.href = '/login';
            return;
        }

        const data = await response.json();

        if (data.success) {
            currentTopicId = data.topic_id;
            currentTopic = data.topic;
            
            // Display topic
            document.getElementById('topicText').textContent = currentTopic;
            
            // Increment count
            questionCount++;
            updateProgressUI();
            
            // Reset UI
            closeResults();
            resetRecordButton();
            resetTimer();
        } else {
            showNotification('Failed to load topic: ' + (data.error || 'Unknown error'), 'error');
        }
    } catch (error) {
        console.error('Load topic error:', error);
        showNotification('Network error. Please check your connection.', 'error');
    } finally {
        showLoading(false);
    }
}

async function toggleRecording() {
    if (!isRecording) {
        await startRecording();
    } else {
        await stopRecording();
    }
}

async function startRecording() {
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
        showNotification(
            'Microphone access requires HTTPS or localhost. Please access via https:// or http://localhost:5000',
            'error'
        );
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

        // Update button
        const btn = document.getElementById('recordBtn');
        const text = document.getElementById('recordText');
        btn.classList.add('recording');
        text.textContent = 'Stop Speaking';

        // Start timer
        startTimer();

        console.log('Recording started for 2 minutes');

    } catch (error) {
        console.error('Start recording error:', error);
        if (error.name === 'NotAllowedError' || error.name === 'PermissionDeniedError') {
            showNotification('Microphone access denied. Please allow microphone access.', 'error');
        } else if (error.name === 'NotFoundError') {
            showNotification('No microphone found. Please connect a microphone.', 'error');
        } else {
            showNotification('Could not start recording: ' + error.message, 'error');
        }
        resetRecordButton();
    }
}

async function stopRecording() {
    if (mediaRecorder && isRecording) {
        isRecording = false;
        
        // Stop timer
        stopTimer();
        
        const btn = document.getElementById('recordBtn');
        const text = document.getElementById('recordText');
        btn.classList.remove('recording');
        text.textContent = 'Processing...';
        btn.disabled = true;

        mediaRecorder.stop();
        console.log('Recording stopped');
    }
}

function startTimer() {
    timeRemaining = RECORDING_DURATION;
    document.getElementById('timerDisplay').style.display = 'block';
    updateTimerDisplay();

    recordingTimer = setInterval(() => {
        timeRemaining--;
        updateTimerDisplay();

        if (timeRemaining <= 0) {
            // Auto-stop recording after 2 minutes
            stopRecording();
        }
    }, 1000);
}

function stopTimer() {
    if (recordingTimer) {
        clearInterval(recordingTimer);
        recordingTimer = null;
    }
}

function resetTimer() {
    stopTimer();
    timeRemaining = RECORDING_DURATION;
    document.getElementById('timerDisplay').style.display = 'none';
    updateTimerDisplay();
}

function updateTimerDisplay() {
    const minutes = Math.floor(timeRemaining / 60);
    const seconds = timeRemaining % 60;
    const display = `${minutes}:${seconds.toString().padStart(2, '0')}`;
    document.getElementById('timeRemaining').textContent = display;
}

async function submitAudio(audioBlob) {
    const formData = new FormData();
    formData.append('audio', audioBlob, 'recording.wav');
    formData.append('topic_id', currentTopicId);

    try {
        console.log('Submitting audio, topic_id:', currentTopicId);
        
        const response = await fetch('/api/moduleC', {
            method: 'POST',
            body: formData,
            credentials: 'same-origin'
        });

        if (response.status === 401) {
            window.location.href = '/login';
            return;
        }

        const result = await response.json();
        console.log('Backend response:', result);

        if (result.success) {
            displayResults(result);
        } else {
            showNotification('Processing failed: ' + (result.error || 'Unknown error'), 'error');
        }

    } catch (error) {
        console.error('Submit audio error:', error);
        showNotification('Failed to process audio. Please try again.', 'error');
    } finally {
        resetRecordButton();
    }
}

function displayResults(result) {
    const score = Math.round(result.score || 0);
    document.getElementById('score').textContent = score;

    const transcription = result.transcription || 'No transcription available';
    document.getElementById('transcription').textContent = transcription;

    const analysis = result.analysis || 'No analysis available';
    document.getElementById('analysis').textContent = analysis;

    const feedback = result.feedback || 'No feedback available';
    document.getElementById('feedback').textContent = feedback;

    document.getElementById('results').style.display = 'flex';
}

function closeResults() {
    document.getElementById('results').style.display = 'none';
}

function nextTopic() {
    loadTopic();
}

function resetRecordButton() {
    const btn = document.getElementById('recordBtn');
    const text = document.getElementById('recordText');
    
    btn.classList.remove('recording');
    btn.disabled = false;
    text.textContent = 'Start Speaking';
    isRecording = false;
    
    resetTimer();
}

function showLoading(show) {
    const topicEl = document.getElementById('topicText');
    if (show) {
        topicEl.textContent = 'Loading topic...';
        topicEl.style.opacity = '0.5';
    } else {
        topicEl.style.opacity = '1';
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
    const proceed = confirm('Fantastic! You completed Module C (Topic Speaking).\n\nReady for the final module - Grammar Quiz?');
    if (proceed) {
        window.location.href = '/moduleD';
    }
}

function logout() {
    if (confirm('Are you sure you want to logout?')) {
        fetch('/logout', { method: 'POST', credentials: 'same-origin' })
            .then(() => window.location.href = '/login')
            .catch(() => window.location.href = '/login');
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
    stopTimer();
});

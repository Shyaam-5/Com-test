// static/moduleB.js - Enhanced Listen & Repeat Module

const MAX_QUESTIONS = 10;
const COUNTDOWN_DURATION = 4;

let questionCount = 0;
let currentSentenceId = null;
let currentSentence = '';
let mediaRecorder = null;
let audioChunks = [];
let isRecording = false;
let audioStream = null;
let hasPlayedAudio = false;
let countdownTimer = null;
let recordingTimer = null;
let recordingStartTime = null;

document.addEventListener('DOMContentLoaded', () => {
    loadSentence();
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

async function loadSentence() {
    if (questionCount >= MAX_QUESTIONS) {
        goToNextModule();
        return;
    }

    try {
        showLoading(true);
        const response = await fetch('/api/moduleB/sentence', {
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
            currentSentence = data.sentence;
            hasPlayedAudio = false;
            
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

async function playAudio() {
    try {
        const btn = document.getElementById('playBtn');
        const text = document.getElementById('playText');
        
        btn.disabled = true;
        text.textContent = 'Playing...';

        if ('speechSynthesis' in window) {
            window.speechSynthesis.cancel(); // Clear any previous speech
            
            const utterance = new SpeechSynthesisUtterance(currentSentence);
            utterance.rate = 0.85;
            utterance.pitch = 1;
            utterance.volume = 1;
            utterance.lang = 'en-US';

            utterance.onend = () => {
                hasPlayedAudio = true;
                text.textContent = 'Play Again';
                btn.disabled = false;
                
                // Show record section after audio finishes
                document.getElementById('recordButtonWrapper').style.display = 'flex';
                document.getElementById('tipText').style.display = 'none';
            };

            utterance.onerror = (event) => {
                console.error('Speech synthesis error:', event);
                showNotification('Audio playback failed. Please try again.', 'error');
                btn.disabled = false;
                text.textContent = 'Start Listening';
            };

            window.speechSynthesis.speak(utterance);
            
        } else {
            showNotification('Text-to-speech not supported in this browser', 'error');
            btn.disabled = false;
        }

    } catch (error) {
        console.error('Play audio error:', error);
        showNotification('Could not play audio', 'error');
        document.getElementById('playText').textContent = 'Start Listening';
        document.getElementById('playBtn').disabled = false;
    }
}

async function toggleRecording() {
    if (!hasPlayedAudio) {
        showNotification('Please listen to the audio first', 'error');
        return;
    }

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

    } catch (error) {
        console.error('Start recording error:', error);
        if (error.name === 'NotAllowedError') {
            showNotification('Microphone access denied', 'error');
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

        // Hide waveform, show processing
        document.getElementById('waveformContainer').style.display = 'none';
        document.getElementById('recordButtonWrapper').style.display = 'flex';
        
        const btn = document.getElementById('recordBtn');
        const text = document.getElementById('recordText');
        text.textContent = 'Processing...';
        btn.disabled = true;

        mediaRecorder.stop();
    }
}

async function submitAudio(audioBlob) {
    const formData = new FormData();
    formData.append('audio', audioBlob, 'recording.wav');
    formData.append('sentence_id', currentSentenceId);

    try {
        const response = await fetch('/api/moduleB', {
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
        showNotification('Failed to process audio', 'error');
    } finally {
        resetRecordButton();
    }
}

function displayResults(result) {
    const score = Math.round(result.score || result.pronunciation_score || 0);
    document.getElementById('score').textContent = score;

    const transcription = result.transcription || result.transcribed_text || 'No transcription';
    document.getElementById('transcription').textContent = transcription;

    const feedback = result.feedback || 'No feedback available';
    document.getElementById('feedback').textContent = feedback;

    document.getElementById('results').style.display = 'flex';
    
    // Auto-close results and load next question after 5 seconds
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

function resetPlayButton() {
    const btn = document.getElementById('playBtn');
    const text = document.getElementById('playText');
    btn.disabled = false;
    text.textContent = 'Start Listening';
}

function resetRecordButton() {
    const btn = document.getElementById('recordBtn');
    const text = document.getElementById('recordText');
    btn.disabled = false;
    text.textContent = 'Start Speaking';
    isRecording = false;
}

function resetUI() {
    // Reset all UI elements to initial state
    document.getElementById('playButtonWrapper').style.display = 'flex';
    document.getElementById('recordButtonWrapper').style.display = 'none';
    document.getElementById('countdownDisplay').style.display = 'none';
    document.getElementById('waveformContainer').style.display = 'none';
    document.getElementById('tipText').style.display = 'block';
    
    resetPlayButton();
    resetRecordButton();
    
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
    // Optional loading state
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
    const proceed = confirm('Excellent! You completed Module B (Listen & Repeat).\n\nReady for Module C (Topic Speaking)?');
    if (proceed) {
        window.location.href = '/moduleC';
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

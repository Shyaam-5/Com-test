import random
import librosa
import os
from jiwer import wer
from groq import Groq
from gtts import gTTS  # Text-to-speech
from dotenv import load_dotenv

load_dotenv()
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

sentences = [
    "The sun rises in the east and sets in the west.",
    "Python is a powerful programming language used worldwide.",
    "Artificial intelligence is transforming the future of technology.",
    "Reading books expands knowledge and sharpens the mind.",
    "A balanced diet is essential for a healthy lifestyle.",
    "The quick brown fox jumps over the lazy dog.",
    "Water is the most essential resource for all living beings.",
    "Cloud computing allows data to be stored and accessed online.",
    "The earth revolves around the sun in an elliptical orbit.",
    "Machine learning enables computers to learn from data.",
    "Listening to music can reduce stress and improve mood.",
    "Teamwork is the key to achieving great success.",
    "Renewable energy sources are vital for a sustainable future.",
    "The internet has revolutionized communication and information sharing."
]

def generate_audio_for_sentence(sentence_id, output_folder='static/audio'):
    """Generate TTS audio for a sentence

    Args:
        sentence_id: Index of the sentence
        output_folder: Folder to save audio files

    Returns:
        Path to the generated audio file (relative to static folder)
    """
    try:
        # Create output folder if it doesn't exist
        os.makedirs(output_folder, exist_ok=True)

        sentence = sentences[sentence_id]
        filename = f"sentence_{sentence_id}.mp3"
        filepath = os.path.join(output_folder, filename)

        # Check if audio already exists
        if os.path.exists(filepath):
            return f"/static/audio/{filename}"

        # Generate TTS audio
        tts = gTTS(text=sentence, lang='en', slow=False)
        tts.save(filepath)

        return f"/static/audio/{filename}"

    except Exception as e:
        print(f"Error generating audio: {str(e)}")
        return None

def run_moduleB(audio_path, sentence_id):
    """Process audio for Module B - Listen & Repeat

    Args:
        audio_path: Path to the audio file
        sentence_id: Index of the sentence to compare against

    Returns:
        Dictionary with score, transcription, and feedback
    """
    try:
        # Get the expected sentence
        if sentence_id < 0 or sentence_id >= len(sentences):
            return {
                "error": "Invalid sentence_id",
                "success": False
            }

        expected_sentence = sentences[sentence_id]

        # Transcribe the audio using Groq Whisper
        with open(audio_path, "rb") as audio_file:
            transcription_response = client.audio.transcriptions.create(
                file=(audio_path, audio_file.read()),
                model="whisper-large-v3",
                response_format="text"
            )

        user_text = transcription_response.strip()

        # Calculate Word Error Rate
        error_rate = wer(expected_sentence.lower(), user_text.lower())
        accuracy = max(0, (1 - error_rate) * 100)

        # Generate feedback
        if accuracy >= 90:
            feedback = "Excellent! Your pronunciation is very clear."
        elif accuracy >= 70:
            feedback = "Good job! Minor improvements needed."
        elif accuracy >= 50:
            feedback = "Fair attempt. Keep practicing pronunciation."
        else:
            feedback = "Needs improvement. Focus on clarity and pace."

        return {
            "success": True,
            "score": round(accuracy, 2),
            "expected": expected_sentence,
            "transcription": user_text,
            "feedback": feedback,
            "sentence_id": sentence_id
        }

    except Exception as e:
        return {
            "error": str(e),
            "success": False
        }

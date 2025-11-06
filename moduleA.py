import random
import librosa
import os
from jiwer import wer
from groq import Groq
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
    "The internet has revolutionized communication and information sharing.",
    "Practice makes perfect, so never stop learning new things."
]

def run_moduleA(audio_path,sentence_id):
    try:
        print(f"Processing audio file: {audio_path}")

        if not os.path.exists(audio_path):
            print(f"ERROR: Audio file not found: {audio_path}")
            return {"error": "Audio file not found"}

        if os.path.getsize(audio_path) == 0:
            print(f"ERROR: Audio file is empty: {audio_path}")
            return {"error": "Audio file is empty"}

        # Choose and remember the exact sentence and an id
        target_sentence = sentences[sentence_id]
        print(f"Target sentence[{sentence_id}]: {target_sentence}")

        # Transcribe
        with open(audio_path, "rb") as audio_file:
            transcription = client.audio.transcriptions.create(
                file=audio_file,
                model="whisper-large-v3"
            )

        transcribed_text = transcription.text or ""
        print(f"Transcribed: {transcribed_text}")

        # Pronunciation score via WER
        error_rate = wer(target_sentence.lower(), transcribed_text.lower())
        pronunciation_score = max(0.0, (1 - error_rate) * 100.0)
        print(f"Pronunciation score: {pronunciation_score}")

        # Fluency features
        try:
            # Slightly faster: compute duration from path directly
            duration = librosa.get_duration(path=audio_path)
            sr = None  # not needed if only duration is required
            y = None
        except Exception:
            # Fallback: load then measure
            y, sr = librosa.load(audio_path, sr=None, mono=True)
            duration = librosa.get_duration(y=y, sr=sr)

        words = len(transcribed_text.split())
        wps = words / max(duration, 1e-6)

        if wps < 1:
            fluency_score = wps * 50
        elif 1 <= wps <= 3:
            fluency_score = 80 + ((wps - 1) / 2 * 20)
        else:
            fluency_score = max(0, 100 - (wps - 3) * 20)

        fluency_score = min(100, fluency_score)
        print(f"Fluency score: {fluency_score}")

        if pronunciation_score > 90 and fluency_score > 85:
            feedback = "Excellent! Your pronunciation and fluency are outstanding."
        elif pronunciation_score > 75:
            feedback = "Good pronunciation, but try to improve your pacing."
        else:
            feedback = "Needs improvement — focus on speaking more clearly."

        result = {
            "sentence_id": sentence_id,            # new
            "target_sentence": target_sentence,    # already present
            "transcribed_text": transcribed_text,
            "pronunciation_score": pronunciation_score,
            "fluency_score": fluency_score,
            "duration_sec": duration,              # helpful for UI/debug
            "wps": wps,                            # optional extra metric
            "feedback": feedback
        }

        print(f"Final result: {result}")
        return result

    except Exception as e:
        print(f"ERROR in run_moduleA: {str(e)}")
        import traceback
        traceback.print_exc()
        return {
            "error": str(e),
            "sentence_id": None,
            "target_sentence": "Error occurred",
            "transcribed_text": "Processing failed",
            "pronunciation_score": 0,
            "fluency_score": 0,
            "feedback": f"Error: {str(e)}"
        }
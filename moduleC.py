import random
import os
import json
import re
from groq import Groq
from google import genai
from dotenv import load_dotenv

load_dotenv()
groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))
gemini_client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

topics = [
    "The importance of renewable energy in today's world",
    "How technology is revolutionizing modern education",
    "The role of artificial intelligence in healthcare",
    "Your favorite hobby and why it brings you joy",
    "The impact of social media on modern society",
    "How to maintain a healthy lifestyle in busy times",
    "The importance of effective time management",
    "The benefits of reading books in the digital age",
    "Climate change and its global effects",
    "Your dream vacation destination and why"
]

def run_moduleC(audio_path):
    """Process audio for Module C - Topic Speaking

    Args:
        audio_path: Path to the audio file

    Returns:
        Dictionary with score, transcription, feedback, and analysis
    """
    try:
        # Get random topic
        topic = random.choice(topics)

        # Transcribe the audio using Groq Whisper
        with open(audio_path, "rb") as audio_file:
            transcription_response = groq_client.audio.transcriptions.create(
                file=(audio_path, audio_file.read()),
                model="whisper-large-v3",
                response_format="text"
            )

        user_text = transcription_response.strip()

        # Use Gemini to evaluate the response
        prompt = f"""You are an English language evaluator. Evaluate the following spoken response on the topic: "{topic}"

User's transcribed response: "{user_text}"

Evaluate based on:
1. Relevance to the topic (0-25 points)
2. Grammar and sentence structure (0-25 points)
3. Vocabulary richness (0-25 points)
4. Coherence and organization (0-25 points)

Provide your evaluation in the following JSON format:
{{
    "relevance_score": <0-25>,
    "grammar_score": <0-25>,
    "vocabulary_score": <0-25>,
    "coherence_score": <0-25>,
    "total_score": <0-100>,
    "feedback": "<detailed constructive feedback>",
    "strengths": ["<strength1>", "<strength2>"],
    "improvements": ["<improvement1>", "<improvement2>"]
}}

Only respond with valid JSON, no additional text."""

        response = gemini_client.models.generate_content(
            model='gemini-2.0-flash-exp',
            contents=prompt
        )

        # Parse the JSON response
        response_text = response.text.strip()

        # Remove markdown code blocks if present
        response_text = re.sub(r'^```json\s*|\s*```$', '', response_text, flags=re.MULTILINE)

        evaluation = json.loads(response_text)

        return {
            "success": True,
            "topic": topic,
            "transcription": user_text,
            "score": evaluation.get("total_score", 0),
            "relevance_score": evaluation.get("relevance_score", 0),
            "grammar_score": evaluation.get("grammar_score", 0),
            "vocabulary_score": evaluation.get("vocabulary_score", 0),
            "coherence_score": evaluation.get("coherence_score", 0),
            "feedback": evaluation.get("feedback", ""),
            "strengths": evaluation.get("strengths", []),
            "improvements": evaluation.get("improvements", [])
        }

    except json.JSONDecodeError as e:
        return {
            "error": f"Failed to parse evaluation: {str(e)}",
            "success": False
        }
    except Exception as e:
        return {
            "error": str(e),
            "success": False
        }

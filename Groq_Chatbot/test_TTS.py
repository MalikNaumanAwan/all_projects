#!/usr/bin/env python3
"""
Generate speech from text using Groq's playai-tts model.

Requirements:
    pip install groq python-dotenv

Ensure you have a `.env` file in your root directory:
    GROQ_API_KEY=your_real_api_key_here
"""

import os
from dotenv import load_dotenv
from groq import Groq

# Supported voices (for quick reference)
ENGLISH_VOICES = [
    "Arista-PlayAI",
    "Atlas-PlayAI",
    "Basil-PlayAI",
    "Briggs-PlayAI",
    "Calum-PlayAI",
    "Celeste-PlayAI",
    "Cheyenne-PlayAI",
    "Chip-PlayAI",
    "Cillian-PlayAI",
    "Deedee-PlayAI",
    "Fritz-PlayAI",
    "Gail-PlayAI",
    "Indigo-PlayAI",
    "Mamaw-PlayAI",
    "Mason-PlayAI",
    "Mikail-PlayAI",
    "Mitch-PlayAI",
    "Quinn-PlayAI",
    "Thunder-PlayAI",
]


def main():
    # Load environment variables
    load_dotenv()
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise RuntimeError("Missing GROQ_API_KEY in environment or .env file.")

    # Initialize Groq client
    client = Groq(api_key=api_key)

    # Define parameters
    model = "playai-tts"
    voice = "Cheyenne-PlayAI"  # Change voice as desired among supported English voices :contentReference[oaicite:0]{index=0}
    text = "This is a sample message being synthesized into speech.Below is a modular script that enables you to select any of the supported voices dynamically—streamlining experimentation and deployment in high-throughput, voice-centric pipelines."
    output_format = "mp3"
    output_file = "speech.mp3"

    # Invoke TTS API
    response = client.audio.speech.create(
        model=model, voice=voice, input=text, response_format=output_format
    )

    # Save audio to root directory
    response.write_to_file(output_file)
    print(f"Audio synthesis successful. File saved as: {output_file}")


if __name__ == "__main__":
    main()

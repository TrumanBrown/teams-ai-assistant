import os
import queue
import sounddevice as sd
import vosk
import json
from openai import OpenAI
from datetime import datetime
from tabulate import tabulate
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

# Set up OpenAI client using .env
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Load Vosk model from models directory
model_path = os.path.join(os.path.dirname(__file__), "..", "models", "vosk-model-small-en-us-0.15")
model = vosk.Model(model_path)
samplerate = 16000
q = queue.Queue()

# Output file
output_file = os.path.join(os.path.dirname(__file__), "..", "output", "meeting_log.txt")
os.makedirs(os.path.dirname(output_file), exist_ok=True)

# Create or reset log file
with open(output_file, "w", encoding="utf-8") as f:
    f.write("🧠 Real-Time Meeting Copilot Log\n")
    f.write("=" * 80 + "\n")

# Table data
table_rows = []

def callback(indata, frames, time, status):
    if status:
        print("Stream Status:", status)
    q.put(bytes(indata))

device_index = 3  # Update as needed
channels = 1

with sd.InputStream(samplerate=samplerate, blocksize=8000, dtype='int16',
                    channels=channels, callback=callback, device=device_index):
    rec = vosk.KaldiRecognizer(model, samplerate)

    while True:
        data = q.get()
        if rec.AcceptWaveform(data):
            result = json.loads(rec.Result())
            text = result.get("text", "").strip()
            if not text:
                continue

            # Get GPT response
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "You're helping a user in a Microsoft Teams meeting. Respond informatively to conversation topics, and if a question is asked, answer it and include helpful reference links if relevant."},
                    {"role": "user", "content": text}
                ]
            )
            answer = response.choices[0].message.content.strip()

            # Append to table and write to file
            table_rows.append([text, answer])
            table = tabulate(table_rows, headers=["🗣 Heard", "🤖 GPT Response"], tablefmt="grid", maxcolwidths=[40, 60])

            with open(output_file, "w", encoding="utf-8") as f:
                f.write(table + "\n")

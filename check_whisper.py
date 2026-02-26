import whisper
import os
print(f"Whisper file: {whisper.__file__}")
try:
    print(f"Whisper version: {whisper.__version__}")
except AttributeError:
    print("Whisper has no __version__")

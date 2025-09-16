import os
import librosa
import tensorflow as tf
import tensorflow_hub as hub

DATASETS_DIR = "datasets"
song_file = "Aao Na Kuch Kuch Locha Hai Sunny Leone & Ram Kapoor_20e3bc77_9c257d2b-e34c-4f65-b987-cae7bc03d86e.mp3"
song_path = os.path.join(DATASETS_DIR, song_file)

print("[i] Loading audio")
y, sr = librosa.load(song_path, sr=16000)
print("[✓] Audio loaded, duration:", librosa.get_duration(y=y, sr=sr))

# --- Test Librosa features separately ---
try:
    import numpy as np
    mfccs = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=13)
    chroma = librosa.feature.chroma_stft(y=y, sr=sr)
    print("[✓] Librosa features OK")
except Exception as e:
    print("[!] Librosa error:", e)

# --- Test YAMNet separately ---
try:
    print("[i] Loading YAMNet")
    yamnet = hub.load("https://tfhub.dev/google/yamnet/1")
    print("[✓] YAMNet loaded")

    print("[i] Running YAMNet on full audio (may crash)...")
    audio_tensor = tf.convert_to_tensor(y, dtype=tf.float32)
    scores, embeddings, _ = yamnet(audio_tensor)  # <-- likely crash
    print("[✓] YAMNet inference OK")
except Exception as e:
    print("[!] YAMNet error:", e)

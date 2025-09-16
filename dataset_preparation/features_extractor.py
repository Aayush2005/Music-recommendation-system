#!/usr/bin/env python3
"""
Thread-safe MP3 Feature Extractor (Librosa + YAMNet) for Apple Silicon
- Step 1: Librosa features (single process)
- Step 2: YAMNet embeddings & instruments (multi-process)
- Combines both into features_combined.json
"""

import faulthandler
faulthandler.enable()
import os
import json
import numpy as np
import librosa
import tensorflow as tf
import tensorflow_hub as hub
import requests
from pydub import AudioSegment
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

# ---- Paths ----
DATASETS_DIR = "datasets"
METADATA_JSON = "metadata.json"
OUTPUT_LIBROSA = "features_librosa.json"
OUTPUT_COMBINED = "features_combined.json"

# ---- Load metadata ----
with open(METADATA_JSON, "r", encoding="utf-8") as f:
    metadata = json.load(f)
filename_to_id = {fname: meta["song_id"] for fname, meta in metadata.items()}

# ---- MP3 in-memory loader ----
def load_mp3_in_memory(path, target_sr=16000):
    audio = AudioSegment.from_file(path)
    audio = audio.set_channels(1).set_frame_rate(target_sr)
    y = np.array(audio.get_array_of_samples()).astype(np.float32) / (2**15)
    return np.ascontiguousarray(y, dtype=np.float32), target_sr

# ---- Step 1: Librosa-only features ----
def extract_features_librosa(fpath):
    fname = os.path.basename(fpath)
    song_id = filename_to_id.get(fname)
    if not song_id:
        print(f"[!] Metadata missing for {fname}")
        return None

    try:
        y, sr = load_mp3_in_memory(fpath, target_sr=16000)

        # MFCC
        mfccs = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=13)
        mfcc_mean = mfccs.mean(axis=1).tolist()
        mfcc_std = mfccs.std(axis=1).tolist()

        # Chroma
        chroma = librosa.feature.chroma_stft(y=y, sr=sr)
        chroma_mean = chroma.mean(axis=1).tolist()

        # Spectral
        spectral_centroid = float(librosa.feature.spectral_centroid(y=y, sr=sr).mean())
        spectral_bandwidth = float(librosa.feature.spectral_bandwidth(y=y, sr=sr).mean())
        spectral_contrast = librosa.feature.spectral_contrast(y=y, sr=sr).mean(axis=1).tolist()

        # Others
        zero_crossing = float(librosa.feature.zero_crossing_rate(y).mean())
        tempo = 0.0
        duration = float(librosa.get_duration(y=y, sr=sr))

        feature_vector = mfcc_mean + mfcc_std + chroma_mean + [
            spectral_centroid, spectral_bandwidth, zero_crossing, tempo, duration
        ] + spectral_contrast

        return song_id, {
            "features": feature_vector,
            "duration": duration
        }

    except Exception as e:
        print(f"[!] Error processing {fname}: {e}")
        return None

# ---- Step 2: YAMNet features (multi-process) ----
print("[i] Loading YAMNet model...")
yamnet = hub.load("https://tfhub.dev/google/yamnet/1")
print("[✓] YAMNet loaded.")

# Load class names
yamnet_class_map_url = "https://raw.githubusercontent.com/tensorflow/models/master/research/audioset/yamnet/yamnet_class_map.csv"
resp = requests.get(yamnet_class_map_url, timeout=30)
resp.raise_for_status()
CLASS_NAMES = [line.split(",")[2].strip() for line in resp.text.strip().split("\n")[1:]]

def yamnet_chunked_features(y, chunk_sec=2, sr=16000):
    chunk_len = sr * chunk_sec
    embeddings_list, scores_list = [], []

    for start in range(0, len(y), chunk_len):
        chunk = y[start:start+chunk_len]
        if len(chunk) == 0:
            continue
        # Flatten chunk to 1D
        chunk_flat = np.reshape(chunk, (-1,))
        chunk_tensor = tf.convert_to_tensor(chunk_flat, dtype=tf.float32)
        scores, embeddings, _ = yamnet(chunk_tensor)
        scores_list.append(scores.numpy())
        embeddings_list.append(embeddings.numpy())

    if embeddings_list:
        scores_mean = np.mean(np.vstack(scores_list), axis=0)
        embeddings_mean = np.mean(np.vstack(embeddings_list), axis=0)
    else:
        scores_mean = np.zeros(len(CLASS_NAMES))
        embeddings_mean = np.zeros(1024)  # YAMNet embedding size
    return scores_mean, embeddings_mean

def extract_features_yamnet(fpath):
    fname = os.path.basename(fpath)
    song_id = filename_to_id.get(fname)
    if not song_id:
        return None
    try:
        y, sr = load_mp3_in_memory(fpath, target_sr=16000)
        scores, embedding = yamnet_chunked_features(y, chunk_sec=2, sr=sr)
        top_idx = np.argsort(scores)[::-1][:20]
        instruments = {CLASS_NAMES[i]: float(scores[i]) for i in top_idx if scores[i] > 0.15}
        return song_id, embedding.tolist(), instruments
    except Exception as e:
        print(f"[!] YAMNet error {fname}: {e}")
        return None

# ---- Main ----
def main():
    files = list(Path(DATASETS_DIR).glob("*.mp3"))
    print(f"[i] Step 1: Extracting Librosa features for {len(files)} files...")

    # Load previous Librosa features if any
    features_dict = {}
    if os.path.exists(OUTPUT_LIBROSA):
        with open(OUTPUT_LIBROSA, "r") as f:
            features_dict = json.load(f)

    # Step 1: Librosa
    for idx, fp in enumerate(files, 1):
        song_id = filename_to_id.get(fp.name)
        if song_id in features_dict:
            continue
        res = extract_features_librosa(fp)
        if res:
            song_id, data = res
            features_dict[song_id] = data
            # Save incrementally
            with open(OUTPUT_LIBROSA, "w") as f:
                json.dump(features_dict, f, indent=2)
        print(f"[{idx}/{len(files)}] Librosa done: {fp.name}")

    print(f"[✓] Librosa features saved to {OUTPUT_LIBROSA}")

    # Step 2: YAMNet
    print(f"[i] Step 2: Extracting YAMNet features (parallel)...")
    with ProcessPoolExecutor() as executor:
        futures = {executor.submit(extract_features_yamnet, fp): fp for fp in files}
        for idx, fut in enumerate(as_completed(futures), 1):
            res = fut.result()
            if res:
                song_id, embedding, instruments = res
                if song_id in features_dict:
                    features_dict[song_id]["yamnet_embedding"] = embedding
                    features_dict[song_id]["instruments"] = instruments
                # Save incrementally
                with open(OUTPUT_COMBINED, "w") as f:
                    json.dump(features_dict, f, indent=2)
            print(f"[{idx}/{len(files)}] YAMNet done: {os.path.basename(futures[fut])}")

    print(f"[✓] Combined features saved to {OUTPUT_COMBINED}")

# ---- CLI ----
if __name__ == "__main__":
    main()

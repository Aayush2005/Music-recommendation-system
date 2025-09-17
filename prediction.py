import json
import numpy as np
from pathlib import Path
from pydub import AudioSegment
import librosa
import joblib
import requests
import onnxruntime as ort

# ---------------------------
# Paths
# ---------------------------
TEST_DIR = "test"
CLUSTERS_JSON = "clusters.json"
FEATURES_REDUCED_JSON = "features_reduced.json"
METADATA_JSON = "metadata.json"
PCA_FILE = "models/yamnet_pca.joblib"
OUTPUT_JSON = "predictions_cluster_top10.json"
ONNX_MODEL_PATH = "models/yamnet.onnx"

# ---------------------------
# Load metadata
# ---------------------------
with open(METADATA_JSON, "r") as f:
    metadata = json.load(f)
song_id_to_meta = {v["song_id"]: v for v in metadata.values()}

# ---------------------------
# Load clusters and reduced features
# ---------------------------
with open(CLUSTERS_JSON, "r") as f:
    clusters_data = json.load(f)

cluster_centroids = {int(k): np.array(v, dtype=np.float32) 
                     for k, v in clusters_data["centroids"].items()}

with open(FEATURES_REDUCED_JSON, "r") as f:
    features_reduced = json.load(f)

cluster_to_song_ids = {}
for song_id, data in features_reduced.items():
    cluster_to_song_ids.setdefault(data["cluster"], []).append(song_id)

# ---------------------------
# Load PCA and YAMNet ONNX Model
# ---------------------------
pca = joblib.load(PCA_FILE)

# --- Updated Model Loading ---
print(f"[i] Loading ONNX YAMNet model from '{ONNX_MODEL_PATH}'...")
onnx_session = ort.InferenceSession(ONNX_MODEL_PATH)
# Get model input and output names dynamically for robustness
input_name = onnx_session.get_inputs()[0].name
output_names = [output.name for output in onnx_session.get_outputs()]
print("[✓] ONNX model loaded successfully.")
# ---

# Load YAMNet class names for instrument detection
print("[i] Loading YAMNet class names...")
yamnet_class_map_url = "https://raw.githubusercontent.com/tensorflow/models/master/research/audioset/yamnet/yamnet_class_map.csv"
try:
    resp = requests.get(yamnet_class_map_url, timeout=30)
    resp.raise_for_status()
    # Ensure quotes are stripped from class names
    CLASS_NAMES = [line.split(",")[2].strip().strip('"') for line in resp.text.strip().split("\n")[1:]]
    print(f"[✓] Loaded {len(CLASS_NAMES)} YAMNet class names")
except Exception as e:
    print(f"[!] Failed to load class names: {e}")
    CLASS_NAMES = [f"class_{i}" for i in range(521)]

# ---------------------------
# Helpers
# ---------------------------
def load_mp3(path, target_sr=16000):
    audio = AudioSegment.from_file(path)
    audio = audio.set_channels(1).set_frame_rate(target_sr)
    y = np.array(audio.get_array_of_samples()).astype(np.float32) / (2**15)
    return np.ascontiguousarray(y, dtype=np.float32), target_sr

def extract_librosa(y, sr):
    mfccs = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=13)
    mfcc_mean = mfccs.mean(axis=1).tolist()
    mfcc_std = mfccs.std(axis=1).tolist()
    chroma = librosa.feature.chroma_stft(y=y, sr=sr)
    chroma_mean = chroma.mean(axis=1).tolist()
    spectral_centroid = float(librosa.feature.spectral_centroid(y=y, sr=sr).mean())
    spectral_bandwidth = float(librosa.feature.spectral_bandwidth(y=y, sr=sr).mean())
    spectral_contrast = librosa.feature.spectral_contrast(y=y, sr=sr).mean(axis=1).tolist()
    zero_crossing = float(librosa.feature.zero_crossing_rate(y).mean())
    duration = float(librosa.get_duration(y=y, sr=sr))
    feature_vector = mfcc_mean + mfcc_std + chroma_mean + [
        spectral_centroid, spectral_bandwidth, zero_crossing, 0.0, duration
    ] + spectral_contrast
    return np.array(feature_vector, dtype=np.float32), duration

# --- Rewritten YAMNet extraction function ---
def extract_yamnet_with_instruments(y, sr, chunk_sec=2):
    """Extract YAMNet embeddings and instrument scores using the ONNX model."""
    chunk_len = sr * chunk_sec
    embeddings_list, scores_list = [], []
    
    for start in range(0, len(y), chunk_len):
        chunk = y[start:start+chunk_len]
        if len(chunk) == 0:
            continue
        
        chunk_flat_np = np.reshape(chunk, (-1,)).astype(np.float32)

        # Run ONNX inference
        onnx_outputs = onnx_session.run(output_names, {input_name: chunk_flat_np})
        
        # Map outputs by name to avoid order dependency
        output_map = {name: out for name, out in zip(output_names, onnx_outputs)}
        scores = output_map['scores']
        embeddings = output_map['embeddings']

        scores_list.append(scores)
        embeddings_list.append(embeddings)
    
    if embeddings_list and scores_list:
        scores_mean = np.mean(np.vstack(scores_list), axis=0)
        embeddings_mean = np.mean(np.vstack(embeddings_list), axis=0)
        
        top_idx = np.argsort(scores_mean)[::-1][:20]
        instruments = {CLASS_NAMES[i]: float(scores_mean[i]) for i in top_idx if scores_mean[i] > 0.15}
        top_instrument_score = list(instruments.values())[0] if instruments else 0.0
        
        return embeddings_mean, top_instrument_score
    
    return np.zeros(1024, dtype=np.float32), 0.0
# ---

def combine_features(librosa_feat, yamnet_feat_reduced, instrument_feat, duration_feat):
    return np.hstack([librosa_feat, yamnet_feat_reduced, [instrument_feat], [duration_feat]]).astype(np.float32)

def assign_cluster(feature_vec):
    min_dist = float("inf")
    assigned = -1
    for lbl, centroid in cluster_centroids.items():
        dist = np.linalg.norm(feature_vec - centroid)
        if dist < min_dist:
            min_dist = dist
            assigned = lbl
    return assigned

# ---------------------------
# Core runner for one file
# ---------------------------
def run(file_path: str):
    """Process a single MP3 file and return recommendations."""
    try:
        y, sr = load_mp3(file_path)
        lib_feat, dur = extract_librosa(y, sr)
        
        # This function call stays the same, but now uses the ONNX implementation
        yam_feat, instrument_score = extract_yamnet_with_instruments(y, sr)
        
        yam_feat_reduced = pca.transform(yam_feat.reshape(1, -1))[0]
        final_vec = combine_features(lib_feat, yam_feat_reduced, instrument_score, dur)
        cluster_id = assign_cluster(final_vec)
        candidate_song_ids = cluster_to_song_ids.get(cluster_id, [])
        
        if not candidate_song_ids:
            similarities = []
            for sid, song_data in features_reduced.items():
                if "features" in song_data:
                    song_features = np.array(song_data["features"], dtype=np.float32)
                    similarity = 1.0 / (1.0 + np.linalg.norm(final_vec - song_features))
                    similarities.append((sid, similarity))
            similarities.sort(key=lambda x: x[1], reverse=True)
            candidate_song_ids = [sid for sid, _ in similarities[:10]]
        
        top_songs = []
        seen_urls = set()
        
        for sid in candidate_song_ids:
            if len(top_songs) >= 10:
                break
            if sid in song_id_to_meta:
                song_meta = song_id_to_meta[sid]
                perma_url = song_meta.get("perma_url")
                if perma_url and perma_url in seen_urls:
                    continue
                if perma_url:
                    seen_urls.add(perma_url)
                top_songs.append({
                    "song_id": sid,
                    "title": song_meta["title"],
                    "album": song_meta.get("album", ""),
                    "year": song_meta.get("year", ""),
                    "language": song_meta.get("language", ""),
                    "duration": song_meta.get("duration", 0),
                    "perma_url": perma_url,
                    "image_url": song_meta.get("image_url", "")
                })
        
        return {
            "cluster_id": cluster_id,
            "total_candidates": len(candidate_song_ids),
            "recommendations": top_songs,
            "method": "cluster" if cluster_to_song_ids.get(cluster_id) else "similarity"
        }
    except Exception as e:
        return {"error": str(e)}

# ---------------------------
# Batch mode (test directory)
# ---------------------------
if __name__ == "__main__":
    predictions = {}
    test_files = list(Path(TEST_DIR).glob("*.mp3"))
    if not test_files:
        print(f"[!] No .mp3 files found in the '{TEST_DIR}' directory. Exiting.")
    else:
        print(f"[i] Processing {len(test_files)} test files...")
        for fp in test_files:
            print(f"[i] Processing: {fp.name}")
            predictions[fp.name] = run(str(fp))
        with open(OUTPUT_JSON, "w") as f:
            json.dump(predictions, f, indent=2)
        print(f"[✓] Predictions saved to '{OUTPUT_JSON}'")
        print(f"[✓] Processed {len(predictions)} files successfully")
import json
import numpy as np
from pathlib import Path
from pydub import AudioSegment
import librosa
import tensorflow as tf
import tensorflow_hub as hub
import joblib
import requests

# ---------------------------
# Paths
# ---------------------------
TEST_DIR = "test"
CLUSTERS_JSON = "clusters.json"
FEATURES_REDUCED_JSON = "features_reduced.json"
METADATA_JSON = "metadata.json"
PCA_FILE = "yamnet_pca.joblib"
OUTPUT_JSON = "predictions_cluster_top10.json"

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
    features_reduced = json.load(f)  # each song_id → {"features": [...], "cluster": int}

# Build cluster → song_id mapping
cluster_to_song_ids = {}
for song_id, data in features_reduced.items():
    cluster_to_song_ids.setdefault(data["cluster"], []).append(song_id)

# ---------------------------
# Load PCA and YAMNet
# ---------------------------
pca = joblib.load(PCA_FILE)
yamnet = hub.load("https://tfhub.dev/google/yamnet/1")

# Load YAMNet class names for instrument detection
print("[i] Loading YAMNet class names...")
yamnet_class_map_url = "https://raw.githubusercontent.com/tensorflow/models/master/research/audioset/yamnet/yamnet_class_map.csv"
try:
    resp = requests.get(yamnet_class_map_url, timeout=30)
    resp.raise_for_status()
    CLASS_NAMES = [line.split(",")[2].strip() for line in resp.text.strip().split("\n")[1:]]
    print(f"[✓] Loaded {len(CLASS_NAMES)} YAMNet class names")
except Exception as e:
    print(f"[!] Failed to load class names: {e}")
    CLASS_NAMES = [f"class_{i}" for i in range(521)]  # Fallback

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

def extract_yamnet_with_instruments(y, sr, chunk_sec=2):
    """Extract YAMNet embeddings and instrument scores (matching training pipeline)"""
    chunk_len = sr * chunk_sec
    embeddings_list, scores_list = [], []
    
    for start in range(0, len(y), chunk_len):
        chunk = y[start:start+chunk_len]
        if len(chunk) == 0:
            continue
        # Flatten chunk to 1D (matching training pipeline)
        chunk_flat = np.reshape(chunk, (-1,))
        chunk_tensor = tf.convert_to_tensor(chunk_flat, dtype=tf.float32)
        scores, embeddings, _ = yamnet(chunk_tensor)
        scores_list.append(scores.numpy())
        embeddings_list.append(embeddings.numpy())
    
    if embeddings_list and scores_list:
        scores_mean = np.mean(np.vstack(scores_list), axis=0)
        embeddings_mean = np.mean(np.vstack(embeddings_list), axis=0)
        
        # Extract top instrument scores (matching training pipeline)
        top_idx = np.argsort(scores_mean)[::-1][:20]
        instruments = {CLASS_NAMES[i]: float(scores_mean[i]) for i in top_idx if scores_mean[i] > 0.15}
        
        # Get the top instrument score (matching feature_selector.py)
        top_instrument_score = list(instruments.values())[0] if instruments else 0.0
        
        return embeddings_mean, top_instrument_score
    
    return np.zeros(1024, dtype=np.float32), 0.0

def combine_features(librosa_feat, yamnet_feat_reduced, instrument_feat, duration_feat):
    """Combine features in the same order as training pipeline"""
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
# Prediction
# ---------------------------
predictions = {}
print(f"[i] Processing {len(list(Path(TEST_DIR).glob('*.mp3')))} test files...")

for fp in Path(TEST_DIR).glob("*.mp3"):
    try:
        print(f"[i] Processing: {fp.name}")
        
        # Load audio
        y, sr = load_mp3(fp)
        
        # Extract Librosa features (matching training pipeline)
        lib_feat, dur = extract_librosa(y, sr)
        print(f"    Librosa features: {len(lib_feat)} dims, duration: {dur:.2f}s")
        
        # Extract YAMNet features and instruments (matching training pipeline)
        yam_feat, instrument_score = extract_yamnet_with_instruments(y, sr)
        print(f"    YAMNet embedding: {len(yam_feat)} dims, top instrument score: {instrument_score:.3f}")
        
        # Apply PCA to YAMNet features (matching training pipeline)
        yam_feat_reduced = pca.transform(yam_feat.reshape(1, -1))[0]
        print(f"    YAMNet reduced: {len(yam_feat_reduced)} dims")
        
        # Combine features in the same order as training
        final_vec = combine_features(lib_feat, yam_feat_reduced, instrument_score, dur)
        print(f"    Final feature vector: {len(final_vec)} dims")
        
        # Assign to cluster
        cluster_id = assign_cluster(final_vec)
        print(f"    Assigned to cluster: {cluster_id}")
        
        # Get songs from the same cluster
        candidate_song_ids = cluster_to_song_ids.get(cluster_id, [])
        
        # If no songs in cluster (e.g., cluster -1 for noise), use similarity-based fallback
        if not candidate_song_ids:
            print(f"    No songs in cluster {cluster_id}, using similarity-based recommendations...")
            
            # Calculate similarity to all songs in the dataset
            similarities = []
            for sid, song_data in features_reduced.items():
                if "features" in song_data:
                    song_features = np.array(song_data["features"], dtype=np.float32)
                    similarity = 1.0 / (1.0 + np.linalg.norm(final_vec - song_features))
                    similarities.append((sid, similarity))
            
            # Sort by similarity and get top 10
            similarities.sort(key=lambda x: x[1], reverse=True)
            candidate_song_ids = [sid for sid, _ in similarities[:10]]
        
        # Create recommendations with metadata
        top_songs = []
        for sid in candidate_song_ids[:10]:
            if sid in song_id_to_meta:
                song_meta = song_id_to_meta[sid]
                top_songs.append({
                    "song_id": sid,
                    "title": song_meta["title"],
                    "album": song_meta.get("album", ""),
                    "year": song_meta.get("year", ""),
                    "language": song_meta.get("language", ""),
                    "duration": song_meta.get("duration", 0),
                    "perma_url": song_meta["perma_url"],
                    "image_url": song_meta.get("image_url", "")
                })
        
        predictions[fp.name] = {
            "cluster_id": cluster_id,
            "total_candidates": len(candidate_song_ids),
            "recommendations": top_songs,
            "method": "cluster" if cluster_to_song_ids.get(cluster_id) else "similarity"
        }
        
        method = "cluster-based" if cluster_to_song_ids.get(cluster_id) else "similarity-based"
        print(f"    → Found {len(top_songs)} recommendations using {method} approach")
        print()

    except Exception as e:
        print(f"[!] Error processing {fp.name}: {e}")
        import traceback
        traceback.print_exc()
        print()

# Save predictions to JSON
with open(OUTPUT_JSON, "w") as f:
    json.dump(predictions, f, indent=2)

print(f"[✓] Predictions saved to '{OUTPUT_JSON}'")
print(f"[✓] Processed {len(predictions)} files successfully")

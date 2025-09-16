import json
import numpy as np
from sklearn.decomposition import PCA

# Load features_combined.json
with open("features_combined.json", "r") as f:
    data = json.load(f)

song_ids = list(data.keys())

# Prepare features
librosa_feats = []
yamnet_feats = []
instrument_feats = []
duration_feats = []

for song in data.values():
    librosa_feats.append(song["features"])
    yamnet_feats.append(song["yamnet_embedding"])
    instr_val = list(song.get("instruments", {}).values())
    instrument_feats.append([instr_val[0]] if instr_val else [0.0])
    duration_feats.append([song["duration"]])

librosa_feats = np.array(librosa_feats, dtype=np.float32)
yamnet_feats = np.array(yamnet_feats, dtype=np.float32)
instrument_feats = np.array(instrument_feats, dtype=np.float32)
duration_feats = np.array(duration_feats, dtype=np.float32)

# Reduce YAMNet embeddings
pca = PCA(n_components=64, whiten=True)
yamnet_reduced = pca.fit_transform(yamnet_feats)

# Concatenate final feature vector
final_features = np.hstack([librosa_feats, yamnet_reduced, instrument_feats, duration_feats]).astype(np.float32)

# Build JSON structure
export_json = {}
for i, sid in enumerate(song_ids):
    export_json[sid] = {
        "features": final_features[i].tolist(),
        "cluster": int(data[sid].get("cluster", -1)),  # if cluster info exists
        "title": data[sid].get("title", ""),
        "perma_url": data[sid].get("perma_url", "")
    }

# Save reduced embeddings + cluster info
with open("features_reduced.json", "w") as f:
    json.dump(export_json, f, indent=2)

print("[✓] Exported reduced embeddings + cluster info to features_reduced.json")

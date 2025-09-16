# Music Recommendation System (MIR-based)

This project is a **Music Information Retrieval (MIR)** based recommendation system that analyzes inherent audio features of songs to provide personalized recommendations using advanced machine learning techniques.

---

## Project Status

- **Data Collection:** ✅ Completed  
  - Collected **1213 songs** from multiple YouTube playlists  
  - Audio files stored in `datasets/` directory  
  - Conversion to `.mp3` format using `yt-dlp` with FFmpeg  

- **Feature Extraction:** ✅ Completed  
  - **Librosa features:** MFCC (mean/std), Chroma, Spectral features, Zero crossing rate  
  - **YAMNet embeddings:** Deep learning-based audio embeddings (1024-dim → 64-dim via PCA)  
  - **Instrument detection:** Top instrument scores from YAMNet classification  
  - Combined feature vectors stored in structured JSON format  

- **Clustering & Model:** ✅ Completed  
  - HDBSCAN clustering applied to feature vectors  
  - Cluster centroids computed for similarity matching  
  - Fallback similarity-based recommendations for edge cases  

- **Prediction System:** ✅ Completed  
  - Real-time audio feature extraction for new songs  
  - Cluster assignment and similarity-based recommendations  
  - Comprehensive metadata integration (title, album, year, language, etc.)  

---

## System Architecture

### 1. **Data Pipeline**
```
Audio Files → Feature Extraction → Dimensionality Reduction → Clustering → Recommendations
```

### 2. **Feature Engineering**
- **Traditional Audio Features (Librosa):** 50 dimensions
- **Deep Learning Features (YAMNet):** 64 dimensions (PCA-reduced)
- **Instrument Features:** Top instrument confidence scores
- **Metadata Features:** Duration, language, year
- **Total Feature Vector:** 116 dimensions

### 3. **Recommendation Engine**
- **Primary:** Cluster-based recommendations using HDBSCAN
- **Fallback:** Cosine similarity-based recommendations
- **Output:** Top 10 similar songs with complete metadata  

---

## Usage

### 🌐 Web Application (Recommended)

1. **Start the Server:**
   ```bash
   conda activate venv/
   python main.py
   ```

2. **Open Browser:**
   - Navigate to `http://localhost:5000`

3. **Get Recommendations:**
   - Paste any YouTube music video URL
   - Click "Get Recommendations"
   - View beautiful recommendation cards
   - Click cards to open songs on JioSaavn

### 🎵 Command Line Testing

1. **Cone the repositry:**
   ```bash
    git clone https://github.com/Aayush2005/Music-recommendation-system.git
    cd Music-recommendation-system

   ```
   

2. **Create and Activate Environment:**
   ```bash
   conda create -p venv python=3.12
   conda activate venv/

   ```
   or 
   ```bash
   pyenv install --list
   pyenv install 3.12
   pyenv virtualenv 3.12 venv
   pyenv local venv

   ```
   
3. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Prediction**
  - Add your mp3 song in test/
   ```bash
   python prediction.py
   ```

5. **View Results:**
   - Check `predictions_cluster_top10.json` for recommendations

### Example Output
```json
{
  "test_song.mp3": {
    "cluster_id": 0,
    "total_candidates": 10,
    "method": "similarity",
    "recommendations": [
      {
        "song_id": "abc123",
        "title": "Similar Song",
        "album": "Album Name",
        "year": "2020",
        "language": "hindi",
        "duration": 180,
        "perma_url": "https://...",
        "image_url": "https://..."
      }
    ]
  }
}
```

---

## Project Structure

```
├── datasets/                    # Original audio files (1213 songs)
├── test/                       # Test audio files for predictions
├── database/                   # Processed feature databases
├── dataset_preparation/        # Feature extraction scripts
├── notebooks/                  # Jupyter notebooks for analysis
├── prediction.py              # Main prediction script
├── clusters.json              # Cluster centroids and labels
├── features_reduced.json      # PCA-reduced feature vectors
├── metadata.json             # Song metadata database
└── yamnet_pca.joblib         # Trained PCA model
```

---

## Technical Details

### Feature Extraction Pipeline
1. **Audio Loading:** Convert MP3 to 16kHz mono using pydub
2. **Librosa Features:** Extract traditional audio features (MFCC, spectral, etc.)
3. **YAMNet Processing:** Extract deep embeddings and instrument classifications
4. **PCA Reduction:** Reduce YAMNet embeddings from 1024 to 64 dimensions
5. **Feature Combination:** Concatenate all features into final vector

### Recommendation Algorithm
1. **Feature Matching:** Extract features from input audio
2. **Cluster Assignment:** Find nearest cluster centroid
3. **Candidate Selection:** Get songs from same cluster
4. **Fallback Similarity:** Use cosine similarity if cluster is empty
5. **Metadata Enrichment:** Add comprehensive song information

---

## Tools & Libraries

- **Python 3.11+** - Core runtime
- **Audio Processing:** `librosa`, `pydub`, `tensorflow-hub` (YAMNet)
- **Machine Learning:** `scikit-learn`, `hdbscan`, `numpy`
- **Data Management:** `pandas`, `json`
- **Download Tools:** `yt-dlp`, `FFmpeg`

---

## Performance & Results

- **Dataset Size:** 1213 songs processed
- **Feature Dimensions:** 116-dimensional feature vectors
- **Processing Speed:** ~10-15 seconds per test song
- **Recommendation Quality:** Language-aware, genre-consistent suggestions
- **Fallback Coverage:** 100% recommendation success rate

---

## Future Enhancements

1. **Advanced Clustering:** Experiment with different clustering algorithms
2. **User Feedback:** Implement rating system for recommendation improvement
3. **Real-time Processing:** Optimize for faster feature extraction
4. **Web Interface:** Build user-friendly recommendation interface
5. **Playlist Generation:** Create themed playlists based on mood/genre

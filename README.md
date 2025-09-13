# Music Recommendation System (MIR-based)

This project is focused on building a **Music Information Retrieval (MIR)** based recommendation system that analyzes inherent features of songs to provide personalized recommendations.

---

## Project Status

- **Data Collection:** ✅ Completed  
  - Collected **1213 songs** from multiple YouTube playlists.  
  - Audio files are stored in `datasets/`.  
  - Conversion to `.mp3` format is done using `yt-dlp` with FFmpeg.  

- **Current Progress:**  
  - URLs of all songs have been extracted.  
  - Multi-threaded download process is working reliably with cookie support for restricted content.  
  - Duplicate and unwanted files (remixes, mashups) are filtered out.  

---

## Next Steps

1. **Feature Extraction**  
   - Extract audio features (MFCC, spectral, temporal) for each song.  
   - Store feature vectors in a structured format for modeling.

2. **Model Development**  
   - Implement similarity-based recommendation (content-based filtering).  
   - Experiment with CNNs or signal-processing-based approaches for advanced feature learning.  

3. **Evaluation**  
   - Define metrics for recommendation quality (e.g., precision, recall, user feedback).  
   - Test on subsets of collected dataset.  

4. **Deployment & Interface**  
   - Build a web interface or API to allow users to query and receive recommendations.  
   - Optionally, integrate with voice-based or mobile agents for agentic AI functionality.  

---

## Tools & Libraries

- Python 3.11+  
- `yt-dlp` for audio downloads  
- `FFmpeg` for audio conversion  
- `pandas`, `numpy`, `librosa` for data processing  
- `scikit-learn`, `tensorflow`/`pytorch` for model development  

---

## Notes

- Large-scale download took multiple hours; scripts include checks for already downloaded files.  
- Restricted content requires a valid YouTube session cookie to bypass login checks.  
- Dataset is ready for MIR experiments and can be extended with new playlists or sources.

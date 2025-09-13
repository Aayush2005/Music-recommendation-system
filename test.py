import os

dataset_dir = "datasets"
output_file = "songs_list.txt"  # saved at root

files = [
    os.path.splitext(f)[0]  # remove .mp3 extension
    for f in os.listdir(dataset_dir)
    if os.path.isfile(os.path.join(dataset_dir, f)) and f.endswith(".mp3")
]

with open(output_file, "w", encoding="utf-8") as f:
    for song in files:
        f.write(song + "\n")

print(f"Saved {len(files)} song names to {output_file}")

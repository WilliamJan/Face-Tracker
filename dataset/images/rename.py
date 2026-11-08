import os

files = [f for f in os.listdir() if f.endswith(".jpg")]

for i, filename in enumerate(files, start=1):
    os.rename(filename, f"image_{i}.jpg")
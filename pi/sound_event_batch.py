import os
import argparse
import numpy as np
import scipy.io.wavfile as wavfile
import tensorflow as tf
import tensorflow_hub as hub
import matplotlib.pyplot as plt

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-dir", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--confidence", type=float, default=0.5)
    args = parser.parse_args()

    os.makedirs(args.output_dir, exist_ok=True)
    
    print("Loading YAMNet model from TF Hub...")
    model = hub.load('https://tfhub.dev/google/yamnet/1')
    
    # YAMNet uses 16kHz audio, chunks of 0.96s
    for filename in os.listdir(args.input_dir):
        if not filename.endswith(".wav"):
            continue
            
        filepath = os.path.join(args.input_dir, filename)
        print(f"Processing audio {filepath}...")
        
        try:
            sample_rate, wav_data = wavfile.read(filepath, 'rb')
            if len(wav_data.shape) > 1:
                wav_data = np.mean(wav_data, axis=1) # mix to mono
            
            # Normalize to [-1.0, 1.0] if not already
            if wav_data.dtype == np.int16:
                wav_data = wav_data / 32768.0
            elif wav_data.dtype == np.int32:
                wav_data = wav_data / 2147483648.0
            
            wav_data = wav_data.astype(np.float32)
            
            # Note: ideally resample to 16kHz if needed, but for simplicity here we assume 16kHz or YAMNet handles it
            # Actually YAMNet requires exactly 16000. Let's do a simple check.
            if sample_rate != 16000:
                print(f"Warning: {filename} is {sample_rate}Hz, YAMNet expects 16kHz. Results may be inaccurate.")
            
            chunk_size = int(sample_rate * 0.96)
            for i in range(0, len(wav_data), chunk_size):
                chunk = wav_data[i:i+chunk_size]
                if len(chunk) < chunk_size:
                    # pad if necessary or skip
                    chunk = np.pad(chunk, (0, chunk_size - len(chunk)), 'constant')
                    
                scores, embeddings, spectrogram = model(chunk)
                scores_np = scores.numpy()
                infered_class = scores_np.mean(axis=0).argmax()
                # 11 is "Screaming" or "Yell" in YAMNet class map roughly. Let's just check the highest scoring classes.
                # Specifically, 11 is 'Screaming' and 12 is 'Yell', etc.
                scream_prob = max(scores_np[:, 11].max(), scores_np[:, 12].max())
                
                if scream_prob > args.confidence:
                    print(f"Found scream! Prob: {scream_prob:.2f}")
                    # Save spectrogram plot
                    plt.figure(figsize=(10, 4))
                    plt.imshow(spectrogram.numpy().T, aspect='auto', interpolation='nearest', origin='lower')
                    plt.title(f"Scream Detected: {scream_prob:.2f} @ {i/sample_rate:.2f}s")
                    plt.tight_layout()
                    out_path = os.path.join(args.output_dir, f"{os.path.splitext(filename)[0]}_t{i/sample_rate:.2f}_conf{scream_prob:.2f}.png")
                    plt.savefig(out_path)
                    plt.close()
                    
        except Exception as e:
            print(f"Failed to process {filepath}: {e}")

if __name__ == "__main__":
    main()

import wave
import struct
import math

def generate_siren(filename="siren.wav", duration_sec=3.0, sample_rate=44100):
    print(f"Generating audio deterrent: {filename}...")
    num_samples = int(duration_sec * sample_rate)
    
    with wave.open(filename, 'w') as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        
        for i in range(num_samples):
            # Oscillate frequency between 800Hz and 1200Hz every 0.5 seconds
            t = float(i) / sample_rate
            freq = 1000 + 200 * math.sin(2 * math.pi * 2 * t)
            value = int(32767.0 * math.sin(2 * math.pi * freq * t))
            data = struct.pack('<h', value)
            wav_file.writeframesraw(data)
            
    print("Done! Siren generated.")

if __name__ == "__main__":
    generate_siren()

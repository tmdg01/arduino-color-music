import pyaudio
import numpy as np
import serial
import time
from collections import deque

# Параметры последовательного порта
serial_port = '/dev/ttyUSB0'  # замените на ваш порт, если необходимо
baud_rate = 115200

# Подключение к Arduino
ser = serial.Serial(serial_port, baud_rate)
time.sleep(2)  # Даем Arduino время на перезагрузку

# Параметры аудио
FORMAT = pyaudio.paFloat32
CHANNELS = 1
RATE = 44100
CHUNK = 1024

# Инициализация PyAudio
audio = pyaudio.PyAudio()

# Открытие потока
stream = audio.open(format=FORMAT,
                    channels=CHANNELS,
                    rate=RATE,
                    input=True,
                    frames_per_buffer=CHUNK)

# Параметры чувствительности
sensitivity = 15
min_sensitivity = 5
max_sensitivity = 30

# Параметры для автоматической регулировки чувствительности
HISTORY_SIZE = 100
amplitude_history = deque(maxlen=HISTORY_SIZE)
TARGET_AMPLITUDE_LOW = 0.05  # Нижняя граница целевой амплитуды
TARGET_AMPLITUDE_HIGH = 0.2  # Верхняя граница целевой амплитуды
ADJUSTMENT_RATE = 0.1  # Скорость корректировки чувствительности

def adjust_sensitivity(amplitude, threshold=0.01):
    if amplitude < threshold:
        return 0
    return min(1, (amplitude - threshold) * sensitivity)

def adjust_sensitivity_auto(current_sensitivity, current_amplitude):
    amplitude_history.append(current_amplitude)
    
    if len(amplitude_history) < HISTORY_SIZE:
        return current_sensitivity
    
    avg_amplitude = np.mean(amplitude_history)
    
    if avg_amplitude > TARGET_AMPLITUDE_HIGH:
        return max(min_sensitivity, current_sensitivity - ADJUSTMENT_RATE)
    elif avg_amplitude < TARGET_AMPLITUDE_LOW:
        return min(max_sensitivity, current_sensitivity + ADJUSTMENT_RATE)
    
    # Плавное возвращение к среднему значению чувствительности
    return current_sensitivity + (15 - current_sensitivity) * 0.01

try:
    while True:
        data = stream.read(CHUNK, exception_on_overflow=False)
        samples = np.frombuffer(data, dtype=np.float32)
        
        # Анализ амплитуды
        amplitude = np.sqrt(np.mean(samples**2))
        
        # Автоматическая регулировка чувствительности
        sensitivity = adjust_sensitivity_auto(sensitivity, amplitude)
        
        value = adjust_sensitivity(amplitude)
        
        # Спектральный анализ
        freqs = np.fft.fftfreq(len(samples), 1.0 / RATE)
        fft_vals = np.abs(np.fft.fft(samples))
        dominant_freq = freqs[np.argmax(fft_vals[:len(fft_vals) // 2])]
        
        # Преобразование частоты в цвет
        color_value = dominant_freq / (RATE / 2)
        color_value = min(1, max(0, color_value))  # Ограничение значений от 0 до 1
        
        ser.write(f"{value:.3f},{color_value:.3f}\n".encode('utf-8'))
        print(f"Sent value: {value:.3f}, {color_value:.3f}")
        
        response = ser.readline().decode('utf-8').strip()
        print(f"Arduino response: {response}")
        
        print(f"Current sensitivity: {sensitivity:.2f}, Amplitude: {amplitude:.4f}")
        
        time.sleep(0.01)

except KeyboardInterrupt:
    print("Stopping...")

finally:
    stream.stop_stream()
    stream.close()
    audio.terminate()
    ser.close()
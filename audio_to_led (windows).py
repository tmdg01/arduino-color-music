import pyaudio
import numpy as np
import serial
import time
from collections import deque

# Параметры последовательного порта
serial_port = 'COM3'  # Замените на номер вашего COM-порта
baud_rate = 115200

# Подключение к Arduino
try:
    ser = serial.Serial(serial_port, baud_rate, timeout=1)
    time.sleep(2)  # Даем Arduino время на перезагрузку
except serial.SerialException as e:
    print(f"Ошибка при подключении к порту {serial_port}: {e}")
    exit()

# Параметры аудио
FORMAT = pyaudio.paFloat32
CHANNELS = 2  # Стерео
RATE = 44100
CHUNK = 1024

# Инициализация PyAudio
audio = pyaudio.PyAudio()

# Найдем индекс устройства CABLE Output
cable_output_index = None
for i in range(audio.get_device_count()):
    dev_info = audio.get_device_info_by_index(i)
    if "CABLE Output" in dev_info["name"]:
        cable_output_index = i
        break

if cable_output_index is None:
    print("CABLE Output не найден. Убедитесь, что VB-CABLE установлен корректно.")
    ser.close()
    exit()

# Открытие потока
try:
    stream = audio.open(format=FORMAT,
                        channels=CHANNELS,
                        rate=RATE,
                        input=True,
                        frames_per_buffer=CHUNK,
                        input_device_index=cable_output_index)
except OSError as e:
    print(f"Ошибка при открытии аудиопотока: {e}")
    print("Убедитесь, что VB-CABLE установлен и настроен правильно.")
    ser.close()
    exit()

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
        try:
            data = stream.read(CHUNK, exception_on_overflow=False)
            samples = np.frombuffer(data, dtype=np.float32)
            
            # Преобразование стерео в моно
            samples = np.mean(samples.reshape(-1, 2), axis=1)
            
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
        except serial.SerialException as e:
            print(f"Ошибка при отправке данных: {e}")
            break

except KeyboardInterrupt:
    print("Stopping...")

finally:
    stream.stop_stream()
    stream.close()
    audio.terminate()
    ser.close()
    print("Программа завершена.")
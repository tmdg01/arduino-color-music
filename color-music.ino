#include <Adafruit_NeoPixel.h>

#define PIN 12
#define NUMPIXELS 90

Adafruit_NeoPixel pixels(NUMPIXELS, PIN, NEO_GRB + NEO_KHZ800);

float currentWidth = 0;
float targetWidth = 0;
float currentColorValue = 0;
float targetColorValue = 0;
float waveSmoothness = 0.03;

const float staticBrightness = 0.4;

// Параметры для нового эффекта
#define NUM_CIRCLES 3
float circleCenters[NUM_CIRCLES] = {0};
float circleWidths[NUM_CIRCLES] = {0};
float circleColors[NUM_CIRCLES] = {0};

bool useNewEffect = false;  // Флаг для переключения между эффектами

void setup() {
  Serial.begin(115200);
  pixels.begin();
  pixels.clear();
  pixels.show();
  Serial.println("Arduino ready");
}

void loop() {
  if (Serial.available()) {
    String data = Serial.readStringUntil('\n');
    int separatorIndex = data.indexOf(',');
    float amplitudeValue = data.substring(0, separatorIndex).toFloat();
    float colorValue = data.substring(separatorIndex + 1).toFloat();
    
    if (useNewEffect) {
      updatePulsingCircles(amplitudeValue, colorValue);
    } else {
      targetWidth = amplitudeValue * NUMPIXELS / 2;
      targetColorValue = colorValue;
    }
    Serial.println("OK");
  }
  
  if (useNewEffect) {
    updateLEDsPulsingCircles();
  } else {
    currentWidth += (targetWidth - currentWidth) * waveSmoothness;
    currentColorValue += (targetColorValue - currentColorValue) * waveSmoothness;
    updateLEDs(currentColorValue);
  }
}

void updatePulsingCircles(float amplitude, float colorValue) {
  for (int i = 0; i < NUM_CIRCLES; i++) {
    circleCenters[i] += 0.5;  // Скорость движения кругов
    if (circleCenters[i] > NUMPIXELS) {
      circleCenters[i] = 0;
    }
    circleWidths[i] = amplitude * (NUMPIXELS / 4) * (1 + sin(millis() / 1000.0 + i * 2 * PI / NUM_CIRCLES));
    circleColors[i] = fmod(colorValue + (float)i / NUM_CIRCLES, 1.0);
  }
}

void updateLEDsPulsingCircles() {
  pixels.clear();
  
  for (int i = 0; i < NUMPIXELS; i++) {
    float maxBrightness = 0;
    float finalColor = 0;
    
    for (int j = 0; j < NUM_CIRCLES; j++) {
      float distanceFromCenter = abs(i - circleCenters[j]);
      if (distanceFromCenter <= circleWidths[j]) {
        float brightness = 1.0 - pow(distanceFromCenter / circleWidths[j], 2);
        if (brightness > maxBrightness) {
          maxBrightness = brightness;
          finalColor = circleColors[j];
        }
      }
    }
    
    if (maxBrightness > 0) {
      uint32_t color = wheelColor(finalColor * 255);
      uint32_t fadedColor = fadeColor(color, maxBrightness * staticBrightness);
      pixels.setPixelColor(i, fadedColor);
    }
  }
  
  pixels.show();
}

void updateLEDs(float colorValue) {
  uint32_t color = wheelColor(colorValue * 255);
  int centerLED = NUMPIXELS / 2;
  int waveWidth = int(currentWidth);
  
  pixels.clear();
  
  for (int i = 0; i <= waveWidth; i++) {
    float brightness = 1.0 - pow((float)i / waveWidth, 2);
    uint32_t fadedColor = fadeColor(color, brightness * staticBrightness);
    
    if (centerLED + i < NUMPIXELS) {
      pixels.setPixelColor(centerLED + i, fadedColor);
    }
    if (centerLED - i >= 0) {
      pixels.setPixelColor(centerLED - i, fadedColor);
    }
  }
  
  pixels.show();
}

uint32_t wheelColor(byte WheelPos) {
  WheelPos = 255 - WheelPos;
  if(WheelPos < 85) {
    return pixels.Color(255 - WheelPos * 3, 0, WheelPos * 3);
  }
  if(WheelPos < 170) {
    WheelPos -= 85;
    return pixels.Color(0, WheelPos * 3, 255 - WheelPos * 3);
  }
  WheelPos -= 170;
  return pixels.Color(WheelPos * 3, 255 - WheelPos * 3, 0);
}

uint32_t fadeColor(uint32_t color, float brightness) {
  uint8_t r = (uint8_t)(((color >> 16) & 0xFF) * brightness);
  uint8_t g = (uint8_t)(((color >> 8) & 0xFF) * brightness);
  uint8_t b = (uint8_t)((color & 0xFF) * brightness);
  return pixels.Color(r, g, b);
}
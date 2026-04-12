#pragma once
#include "esphome/core/component.h"
#include "esphome/components/image/image.h"
#include "esphome/components/display/display.h"

namespace esphome {
namespace epaper_dither {

enum DitherAlgorithm {
  DITHER_FLOYD_STEINBERG,
  DITHER_ATKINSON,
  DITHER_JARVIS,
  DITHER_SIERRA,
};

static const uint8_t PALETTE[6][3] = {
  {0,   0,   0  },  // Black   → code 0x0
  {255, 255, 255},  // White   → code 0x1
  {0,   255, 0  },  // Yellow  → code 0x2
  {0,   0,   255},  // Red     → code 0x3
  {255, 255, 0  },  // Blue    → code 0x5
  {255, 128, 0  },  // Green   → code 0x6
};

static const uint8_t PERCEPTUAL[6][3] = {
  {0,   0,   0  },  // Black
  {255, 255, 255},  // White
  {255, 255, 0  },  // Yellow
  {255, 0,   0  },  // Red
  {0,   0,   255},  // Blue
  {0,   255, 0  },  // Green
};

class EpaperDither : public Component {
 public:
  void set_algorithm(DitherAlgorithm algo) { this->algo_ = algo; }
  void set_diffusion(float diffusion) { this->diffusion_ = diffusion; }
  void set_gamma(float gamma) { this->gamma_ = gamma; }
  void set_contrast(float contrast) { this->contrast_ = contrast; }

  void setup() override {
    for (int i = 0; i < 256; i++) {
      float v = i / 255.0f;
      // Contrast as power curve in perceptual space
      v = powf(v, 1.0f / this->contrast_);
      this->lut_[i] = (uint8_t)(std::max(0.0f, std::min(1.0f, v)) * 255.0f + 0.5f);
    }
    for (int i = 0; i < 6; i++)
      for (int j = 0; j < 3; j++)
        this->perceptual_lut_[i][j] = this->lut_[PERCEPTUAL[i][j]];
  }

  void dither_and_draw(display::Display &it, image::Image &src, int width, int height) {
    uint32_t start = millis();
    int rows = (this->algo_ == DITHER_JARVIS) ? 3 : (this->algo_ == DITHER_ATKINSON) ? 3 : 2;
    int16_t *err[3] = {nullptr, nullptr, nullptr};
    for (int i = 0; i < rows; i++) {
      err[i] = (int16_t *) heap_caps_calloc(width * 3, sizeof(int16_t), MALLOC_CAP_SPIRAM);
      if (!err[i]) { for (int j = 0; j < i; j++) heap_caps_free(err[j]); return; }
    }

    for (int y = 0; y < height; y++) {
      for (int i = 1; i < rows; i++) memset(err[(y+i) % rows], 0, width * 3 * sizeof(int16_t));
      int16_t *e0 = err[y % rows];
      int16_t *e1 = err[(y+1) % rows];
      int16_t *e2 = (rows > 2) ? err[(y+2) % rows] : nullptr;

      for (int x = 0; x < width; x++) {
        Color c = src.get_pixel(x, y);
        int r = std::max(0, std::min(255, (int)this->lut_[c.r] + e0[x*3]));
        int g = std::max(0, std::min(255, (int)this->lut_[c.g] + e0[x*3+1]));
        int b = std::max(0, std::min(255, (int)this->lut_[c.b] + e0[x*3+2]));

        uint8_t ci = this->nearest_color_(r, g, b);
        it.draw_pixel_at(x, y, Color(PALETTE[ci][0], PALETTE[ci][1], PALETTE[ci][2]));

        int er = (int)((r - this->perceptual_lut_[ci][0]) * this->diffusion_);
        int eg = (int)((g - this->perceptual_lut_[ci][1]) * this->diffusion_);
        int eb = (int)((b - this->perceptual_lut_[ci][2]) * this->diffusion_);
        this->diffuse_(e0, e1, e2, x, width, er, eg, eb);
      }
    }
    for (int i = 0; i < rows; i++) heap_caps_free(err[i]);
    ESP_LOGI("dither", "Done in %ums (algo=%d)", millis() - start, (int)this->algo_);
  }

 protected:
  DitherAlgorithm algo_{DITHER_FLOYD_STEINBERG};
  float diffusion_{0.8f};
  float gamma_{2.2f};
  float contrast_{1.3f};
  uint8_t lut_[256]{};
  uint8_t perceptual_lut_[6][3]{};

  uint8_t nearest_color_(int r, int g, int b) {
    int best = 0, best_dist = INT_MAX;
    for (int i = 0; i < 6; i++) {
      int dr = r - this->perceptual_lut_[i][0];
      int dg = g - this->perceptual_lut_[i][1];
      int db = b - this->perceptual_lut_[i][2];
      int rmean = (r + this->perceptual_lut_[i][0]) / 2;
      int dist = ((512 + rmean) * dr*dr) / 256 + 4 * dg*dg + ((767 - rmean) * db*db) / 256;
      if (dist < best_dist) { best_dist = dist; best = i; }
    }
    return best;
  }

  void add_(int16_t *row, int x, int width, int er, int eg, int eb, int f, int div) {
    if (x < 0 || x >= width) return;
    row[x*3] += er*f/div; row[x*3+1] += eg*f/div; row[x*3+2] += eb*f/div;
  }

  void diffuse_(int16_t *e0, int16_t *e1, int16_t *e2, int x, int w, int er, int eg, int eb) {
    switch (this->algo_) {
      case DITHER_FLOYD_STEINBERG:
        add_(e0,x+1,w,er,eg,eb,7,16); add_(e1,x-1,w,er,eg,eb,3,16);
        add_(e1,x,  w,er,eg,eb,5,16); add_(e1,x+1,w,er,eg,eb,1,16);
        break;
      case DITHER_ATKINSON:
        add_(e0,x+1,w,er,eg,eb,1,8); add_(e0,x+2,w,er,eg,eb,1,8);
        add_(e1,x-1,w,er,eg,eb,1,8); add_(e1,x,  w,er,eg,eb,1,8); add_(e1,x+1,w,er,eg,eb,1,8);
        add_(e2,x,  w,er,eg,eb,1,8);
        break;
      case DITHER_JARVIS:
        add_(e0,x+1,w,er,eg,eb,7,48); add_(e0,x+2,w,er,eg,eb,5,48);
        add_(e1,x-2,w,er,eg,eb,3,48); add_(e1,x-1,w,er,eg,eb,5,48); add_(e1,x,w,er,eg,eb,7,48); add_(e1,x+1,w,er,eg,eb,5,48); add_(e1,x+2,w,er,eg,eb,3,48);
        add_(e2,x-2,w,er,eg,eb,1,48); add_(e2,x-1,w,er,eg,eb,3,48); add_(e2,x,w,er,eg,eb,5,48); add_(e2,x+1,w,er,eg,eb,3,48); add_(e2,x+2,w,er,eg,eb,1,48);
        break;
      case DITHER_SIERRA:
        add_(e0,x+1,w,er,eg,eb,5,32); add_(e0,x+2,w,er,eg,eb,3,32);
        add_(e1,x-2,w,er,eg,eb,2,32); add_(e1,x-1,w,er,eg,eb,4,32); add_(e1,x,w,er,eg,eb,5,32); add_(e1,x+1,w,er,eg,eb,4,32); add_(e1,x+2,w,er,eg,eb,2,32);
        add_(e2,x-1,w,er,eg,eb,2,32); add_(e2,x,  w,er,eg,eb,3,32); add_(e2,x+1,w,er,eg,eb,2,32);
        break;
    }
  }
};

}  // namespace epaper_dither
}  // namespace esphome

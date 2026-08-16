/*
 * native/jarvis_native.c — JARVIS MK37 Native High-Performance C Extension
 * Compiled into libjarvis_native.so / jarvis_native.dll / libjarvis_native.dylib
 */

#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <string.h>
#include <math.h>

#if defined(_WIN32) || defined(_WIN64)
  #define EXPORT __declspec(dllexport)
#else
  #define EXPORT __attribute__((visibility("default")))
#endif

/* 1. Fast FNV-1a 64-bit Non-Cryptographic Frame Hashing */
EXPORT uint64_t jarvis_fast_hash(const uint8_t* data, size_t len) {
    if (!data || len == 0) return 0;
    uint64_t hash = 14695981039346656037ULL;
    const uint64_t fnv_prime = 1099511628211ULL;
    
    for (size_t i = 0; i < len; i++) {
        hash ^= (uint64_t)data[i];
        hash *= fnv_prime;
    }
    return hash;
}

/* 2. Fast RMS Audio Energy Calculation for Voice Activity Detection */
EXPORT float jarvis_audio_energy(const float* buffer, size_t samples) {
    if (!buffer || samples == 0) return 0.0f;
    double sum = 0.0;
    for (size_t i = 0; i < samples; i++) {
        double val = (double)buffer[i];
        sum += val * val;
    }
    return (float)sqrt(sum / (double)samples);
}

/* 3. High-Speed Dense Vector Cosine Similarity for Memory RAG Search */
EXPORT float jarvis_vector_dot_product(const float* vec1, const float* vec2, size_t dim) {
    if (!vec1 || !vec2 || dim == 0) return 0.0f;
    double dot = 0.0;
    double norm1 = 0.0;
    double norm2 = 0.0;
    for (size_t i = 0; i < dim; i++) {
        double v1 = (double)vec1[i];
        double v2 = (double)vec2[i];
        dot += v1 * v2;
        norm1 += v1 * v1;
        norm2 += v2 * v2;
    }
    if (norm1 <= 0.0 || norm2 <= 0.0) return 0.0f;
    return (float)(dot / (sqrt(norm1) * sqrt(norm2)));
}

/* 4. High-Speed Cosine Distance (1.0 - Cosine Similarity) */
EXPORT float jarvis_fast_cosine_distance(const float* vec1, const float* vec2, size_t dim) {
    float sim = jarvis_vector_dot_product(vec1, vec2, dim);
    float dist = 1.0f - sim;
    return dist < 0.0f ? 0.0f : dist;
}

/* 5. High-Speed Grid Coordinate Transformation (0..1000 -> Screen Pixels) */
EXPORT void jarvis_grid_transform(int x_norm, int y_norm, int screen_w, int screen_h, int* out_x, int* out_y) {
    if (!out_x || !out_y) return;
    int px = (int)(((double)x_norm / 1000.0) * (double)screen_w);
    int py = (int)(((double)y_norm / 1000.0) * (double)screen_h);
    
    if (px < 0) px = 0;
    if (px >= screen_w && screen_w > 0) px = screen_w - 1;
    if (py < 0) py = 0;
    if (py >= screen_h && screen_h > 0) py = screen_h - 1;
    
    *out_x = px;
    *out_y = py;
}

/* 6. Low-Overhead Linux C System Memory Reader */
EXPORT uint64_t jarvis_sys_memory_avail_kb(void) {
#if defined(__linux__)
    FILE* fp = fopen("/proc/meminfo", "r");
    if (!fp) return 0;
    char line[256];
    uint64_t mem_avail = 0;
    while (fgets(line, sizeof(line), fp)) {
        if (strncmp(line, "MemAvailable:", 13) == 0) {
            sscanf(line + 13, "%llu", (unsigned long long*)&mem_avail);
            break;
        }
    }
    fclose(fp);
    return mem_avail;
#else
    return 0;
#endif
}

/* 7. C Library Version Check */
EXPORT const char* jarvis_native_version(void) {
    return "37.5.0-native-accelerated";
}

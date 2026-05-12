#!/bin/bash
set -e

# Script to compile dlib from GitHub with optimizations for Raspberry Pi
# and place the resulting shared library into backend/build/

DLIB_REPO="https://github.com/davisking/dlib.git"
DLIB_DIR="dlib_source"
BUILD_DIR="$DLIB_DIR/build"
OUTPUT_DIR="backend/build"

# Clone dlib if not already present
if [ ! -d "$DLIB_DIR" ]; then
    echo "Cloning dlib..."
    git clone --depth 1 "$DLIB_REPO" "$DLIB_DIR"
fi

# Create build directory
mkdir -p "$BUILD_DIR"
cd "$BUILD_DIR"

# Configure with RPi optimizations
cmake .. \
    -DCMAKE_BUILD_TYPE=Release \
    -DUSE_NEON=ON \
    -DUSE_AVX=OFF \
    -DUSE_SSE2=OFF \
    -DUSE_SSE4=OFF \
    -DUSE_AVX2=OFF \
    -DDLIB_USE_BLAS=ON \
    -DDLIB_USE_LAPACK=ON

# Build using all available cores
make -j$(nproc)

# Return to repo root
cd ../..

# Create output directory and copy the shared library
mkdir -p "$OUTPUT_DIR"
cp "$BUILD_DIR/dlib/libdlib.so" "$OUTPUT_DIR/"

echo "dlib compiled successfully and placed in $OUTPUT_DIR/"

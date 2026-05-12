#!/bin/bash
set -e

# Script to compile dlib from GitHub with optimizations for Raspberry Pi
# and produce:
#   - libdlib.so (shared library)
#   - a pip-installable wheel
# Both are placed into backend/build/

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

# Configure with RPi optimizations + shared library
cmake .. \
    -DCMAKE_BUILD_TYPE=Release \
    -DBUILD_SHARED_LIBS=ON \
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

# Build a pip wheel from the dlib source with the same optimizations
echo "Building dlib wheel..."
export CMAKE_ARGS="-DUSE_NEON=ON -DUSE_AVX=OFF -DUSE_SSE2=OFF -DUSE_SSE4=OFF -DUSE_AVX2=OFF -DDLIB_USE_BLAS=ON -DDLIB_USE_LAPACK=ON -DBUILD_SHARED_LIBS=ON"
cd "$DLIB_DIR"
python setup.py bdist_wheel --dist-dir "../$OUTPUT_DIR"
cd ..

echo "dlib compiled successfully."
echo "Shared library: $OUTPUT_DIR/libdlib.so"
echo "Wheel: $(ls $OUTPUT_DIR/dlib-*.whl)"

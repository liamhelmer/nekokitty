FROM ghcr.io/nvidia-ai-iot/llama_cpp@sha256:ba196b9760fda683a84048916ec6666650cc4b05d3bfc05c02bf1917553e55f1

# The 2026-07-13 Orin image contains the shared objects in /usr/local/lib but
# omits that directory from its runtime loader path. Keep this tiny derivative
# reproducible until the upstream image is corrected.
ENV LD_LIBRARY_PATH=/usr/local/lib:/usr/local/cuda/compat:/usr/local/cuda/lib64

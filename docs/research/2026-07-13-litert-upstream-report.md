# LiteRT-LM Jetson GPU upstream report — 2026-07-13

Target issue: <https://github.com/google-ai-edge/LiteRT-LM/issues/2570>

This is the exact non-sensitive comment posted with owner authorization. It is
retained here so future operators can correlate local workarounds with upstream
status.

> Adding a current Orin data point: this still reproduces with the official
> artifact and the PyPI `litert-lm` 0.14.0 aarch64 wheel on the newly released
> L4T R39.2 stack.
>
> Environment:
>
> - Jetson Orin Nano Developer Kit, 8 GB (`sm_87`)
> - L4T R39.2.0 / Ubuntu 24.04 / kernel `6.8.12-1021-tegra`
> - NVIDIA driver 595.78
> - Vulkan instance 1.4.321; device API 1.4.329
> - CUDA compiler/runtime 13.2 is installed; TensorRT 10.16.2
> - `litert-lm` 0.14.0 from PyPI
> - official `litert-community/gemma-4-E2B-it-litert-lm` revision
>   `9262660a1676eed6d0c477ab1a86344430854664`
> - `gemma-4-E2B-it.litertlm`: 2,588,147,712 bytes, SHA-256
>   `181938105e0eefd105961417e8da75903eacda102c4fce9ce90f50b97139a63c`
>
> Reproduction:
>
> ```bash
> litert-lm run gemma-4-e2b-it \
>   --backend gpu --cache disk --max-num-tokens 2048 \
>   --temperature 0.2 --seed 1 \
>   --prompt 'Reply with exactly: meow'
> ```
>
> It prints `meow` and then segfaults with exit 139. An earlier clean-cache run
> logged `NVVM compilation failed: 3`, Dawn Vulkan pipeline creation errors,
> `VK_ERROR_UNKNOWN`, then exited 139. The 2026-07-13 retest after installing the
> full NVCC/CUDART/cuBLAS development components still prints `meow` and exits
> 139. Core dumps were disabled for the retest.
>
> The same model succeeds on CPU, including text and audio input. A bounded
> six-thread CPU server is stable, so this remains specific to the GPU path. The
> failure was not accompanied by OOM or a thermal event. This also shows the
> symptom persists beyond the R36/R38 systems in the original report. I can
> provide the full clean-cache Dawn/NVVM log if useful.

After posting, record the resulting comment URL below.

- Posted comment:
  <https://github.com/google-ai-edge/LiteRT-LM/issues/2570#issuecomment-4959824784>

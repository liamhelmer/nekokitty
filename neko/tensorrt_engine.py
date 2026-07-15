"""Minimal checked TensorRT 10 static-engine runner using libcudart directly."""

from __future__ import annotations

import ctypes
import hashlib
from pathlib import Path
from typing import Any

import numpy as np
import tensorrt as trt


CUDA_MEMCPY_HOST_TO_DEVICE = 1
CUDA_MEMCPY_DEVICE_TO_HOST = 2


class TensorRTEngine:
    """Own one static TensorRT context and reusable device buffers."""

    def __init__(
        self,
        plan: Path,
        expected_sha256: str,
        cudart: Path = Path("/usr/local/cuda/targets/sbsa-linux/lib/libcudart.so.13"),
    ) -> None:
        actual = hashlib.sha256(plan.read_bytes()).hexdigest()
        if actual != expected_sha256:
            raise RuntimeError(f"TensorRT plan hash mismatch: expected {expected_sha256}, got {actual}")
        self.cuda = ctypes.CDLL(str(cudart.resolve()), mode=ctypes.RTLD_LOCAL)
        self._declare_cuda()
        self._check(self.cuda.cudaSetDevice(0), "cudaSetDevice")
        self.stream = ctypes.c_void_p()
        self._check(
            self.cuda.cudaStreamCreateWithFlags(ctypes.byref(self.stream), 1),
            "cudaStreamCreateWithFlags",
        )
        logger = trt.Logger(trt.Logger.ERROR)
        self.runtime = trt.Runtime(logger)
        self.runtime.engine_host_code_allowed = False
        self.engine = self.runtime.deserialize_cuda_engine(plan.read_bytes())
        if self.engine is None:
            raise RuntimeError("TensorRT could not deserialize the engine")
        self.context = self.engine.create_execution_context()
        if self.context is None:
            raise RuntimeError("TensorRT could not create an execution context")
        self.inputs: dict[str, tuple[tuple[int, ...], np.dtype[Any]]] = {}
        self.outputs: dict[str, tuple[tuple[int, ...], np.dtype[Any]]] = {}
        self.device: dict[str, ctypes.c_void_p] = {}
        for index in range(self.engine.num_io_tensors):
            name = self.engine.get_tensor_name(index)
            shape = tuple(int(value) for value in self.engine.get_tensor_shape(name))
            if any(value <= 0 for value in shape):
                raise RuntimeError(f"dynamic or invalid TensorRT shape for {name}: {shape}")
            dtype = np.dtype(trt.nptype(self.engine.get_tensor_dtype(name)))
            target = self.inputs if self.engine.get_tensor_mode(name) == trt.TensorIOMode.INPUT else self.outputs
            target[name] = (shape, dtype)
            pointer = ctypes.c_void_p()
            self._check(
                self.cuda.cudaMalloc(ctypes.byref(pointer), int(np.prod(shape)) * dtype.itemsize),
                f"cudaMalloc({name})",
            )
            self.device[name] = pointer
            if not self.context.set_tensor_address(name, int(pointer.value)):
                raise RuntimeError(f"TensorRT rejected the buffer for {name}")
        unresolved = tuple(self.context.infer_shapes())
        if unresolved:
            raise RuntimeError(f"unresolved TensorRT shapes: {unresolved}")

    def _declare_cuda(self) -> None:
        lib = self.cuda
        lib.cudaSetDevice.argtypes = [ctypes.c_int]
        lib.cudaSetDevice.restype = ctypes.c_int
        lib.cudaMalloc.argtypes = [ctypes.POINTER(ctypes.c_void_p), ctypes.c_size_t]
        lib.cudaMalloc.restype = ctypes.c_int
        lib.cudaFree.argtypes = [ctypes.c_void_p]
        lib.cudaFree.restype = ctypes.c_int
        lib.cudaMemcpyAsync.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_size_t, ctypes.c_int, ctypes.c_void_p]
        lib.cudaMemcpyAsync.restype = ctypes.c_int
        lib.cudaStreamCreateWithFlags.argtypes = [ctypes.POINTER(ctypes.c_void_p), ctypes.c_uint]
        lib.cudaStreamCreateWithFlags.restype = ctypes.c_int
        lib.cudaStreamSynchronize.argtypes = [ctypes.c_void_p]
        lib.cudaStreamSynchronize.restype = ctypes.c_int
        lib.cudaStreamDestroy.argtypes = [ctypes.c_void_p]
        lib.cudaStreamDestroy.restype = ctypes.c_int
        lib.cudaGetErrorString.argtypes = [ctypes.c_int]
        lib.cudaGetErrorString.restype = ctypes.c_char_p

    def _check(self, code: int, operation: str) -> None:
        if int(code):
            message = self.cuda.cudaGetErrorString(int(code))
            detail = message.decode(errors="replace") if message else "unknown CUDA error"
            raise RuntimeError(f"{operation} failed: {detail} ({int(code)})")

    def infer(self, name: str, value: np.ndarray) -> dict[str, np.ndarray]:
        if name not in self.inputs:
            raise ValueError(f"unknown input: {name}")
        shape, dtype = self.inputs[name]
        host_input = np.ascontiguousarray(value, dtype=dtype)
        if host_input.shape != shape:
            raise ValueError(f"input shape must be {shape}, got {host_input.shape}")
        self._check(
            self.cuda.cudaMemcpyAsync(
                self.device[name], ctypes.c_void_p(host_input.ctypes.data), host_input.nbytes,
                CUDA_MEMCPY_HOST_TO_DEVICE, self.stream,
            ),
            "cudaMemcpyAsync(H2D)",
        )
        if not self.context.execute_async_v3(int(self.stream.value)):
            raise RuntimeError("TensorRT execute_async_v3 returned false")
        host_outputs: dict[str, np.ndarray] = {}
        for output_name, (output_shape, output_dtype) in self.outputs.items():
            output = np.empty(output_shape, dtype=output_dtype)
            host_outputs[output_name] = output
            self._check(
                self.cuda.cudaMemcpyAsync(
                    ctypes.c_void_p(output.ctypes.data), self.device[output_name], output.nbytes,
                    CUDA_MEMCPY_DEVICE_TO_HOST, self.stream,
                ),
                f"cudaMemcpyAsync(D2H {output_name})",
            )
        self._check(self.cuda.cudaStreamSynchronize(self.stream), "cudaStreamSynchronize")
        return host_outputs

    def close(self) -> None:
        context = getattr(self, "context", None)
        if context is None:
            return
        self.context = None
        for pointer in self.device.values():
            self._check(self.cuda.cudaFree(pointer), "cudaFree")
        self.device.clear()
        self._check(self.cuda.cudaStreamDestroy(self.stream), "cudaStreamDestroy")

    def __enter__(self) -> "TensorRTEngine":
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

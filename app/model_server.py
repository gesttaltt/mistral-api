#!/usr/bin/env python3
"""
Mistral Server Orchestrator
Automated server management for optimized Mistral inference
"""

import subprocess
import requests
import time
import json
import threading
import os
import signal
from pathlib import Path
from typing import Optional, Dict, Any
import psutil


class MistralServerManager:
    def __init__(self):
        self.base_dir = Path(__file__).parent.parent.parent.parent
        self.model_path = self.base_dir / "mistral_models" / "7B-Instruct-v0.3" / "Mistral-7B-Instruct-v0.3-Q4_K_M.gguf"
        self.server_exe = self.base_dir / "llama-cpp-binaries" / "llama-server.exe"

        self.host = "127.0.0.1"
        self.port = 8081
        self.server_process: Optional[subprocess.Popen] = None
        self.is_running = False

        # Performance settings
        self.ctx_size = 32768
        self.threads = 8
        self.batch_size = 2048
        self.gpu_layers = 20  # Conservative GPU layers for RTX 3050

    def validate_paths(self) -> bool:
        """Validate required files exist"""
        if not self.model_path.exists():
            print(f"❌ Model not found: {self.model_path}")
            return False

        if not self.server_exe.exists():
            print(f"❌ Server not found: {self.server_exe}")
            return False

        return True

    def is_port_free(self) -> bool:
        """Check if port is available"""
        try:
            response = requests.get(f"http://{self.host}:{self.port}/health", timeout=1)
            return False  # Port occupied
        except:
            return True  # Port free

    def start_server(self) -> bool:
        """Start llama-server with optimized settings"""
        if not self.validate_paths():
            return False

        if not self.is_port_free():
            print(f"⚠️  Port {self.port} already in use")
            return self.test_server_health()

        print("🚀 Starting Mistral server...")

        cmd = [
            str(self.server_exe),
            "-m", str(self.model_path),
            "--host", self.host,
            "--port", str(self.port),
            "--ctx-size", str(self.ctx_size),
            "--threads", str(self.threads),
            "--batch-size", str(self.batch_size),
            "--n-gpu-layers", str(self.gpu_layers),  # Offload layers to RTX 3050
            "--parallel", "1",  # Single session for now
            "--cont-batching",  # Continuous batching for efficiency
            "--flash-attn", "auto",  # Flash attention if supported
            "--no-warmup",      # Skip warmup for faster startup
        ]

        try:
            # Start server process
            self.server_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=self.base_dir,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            )

            # Wait for server to start
            print("⏳ Waiting for server to initialize...")
            max_retries = 30  # 30 seconds max

            for i in range(max_retries):
                time.sleep(1)
                if self.test_server_health():
                    self.is_running = True
                    print(f"✅ Server started successfully on {self.host}:{self.port}")
                    print(f"📊 Model: Mistral-7B-Instruct-v0.3-Q4_K_M")
                    print(f"🧠 Context: {self.ctx_size} tokens")
                    return True

                # Check if process died
                if self.server_process.poll() is not None:
                    stdout, stderr = self.server_process.communicate()
                    print(f"❌ Server failed to start")
                    print(f"Error: {stderr.decode()}")
                    return False

            print("❌ Server startup timeout")
            self.stop_server()
            return False

        except Exception as e:
            print(f"❌ Failed to start server: {e}")
            return False

    def test_server_health(self) -> bool:
        """Test if server is responding"""
        try:
            response = requests.get(
                f"http://{self.host}:{self.port}/health",
                timeout=2
            )
            return response.status_code == 200
        except:
            return False

    def stop_server(self):
        """Stop the server gracefully"""
        if self.server_process:
            print("🛑 Stopping server...")

            try:
                # Try graceful shutdown first
                self.server_process.terminate()
                self.server_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                # Force kill if needed
                self.server_process.kill()
                self.server_process.wait()

            self.server_process = None
            self.is_running = False
            print("✅ Server stopped")

    def get_server_stats(self) -> Optional[Dict]:
        """Get server statistics"""
        try:
            response = requests.get(f"http://{self.host}:{self.port}/props")
            if response.status_code == 200:
                return response.json()
        except:
            pass
        return None

    def send_completion_request(self, prompt: str, max_tokens: int = 200,
                              temperature: float = 0.7, stream: bool = False) -> Dict[str, Any]:
        """Send completion request to server"""
        if not self.is_running:
            return {"error": "Server not running"}

        payload = {
            "prompt": f"[INST] {prompt} [/INST]",
            "n_predict": max_tokens,
            "temperature": temperature,
            "stream": stream,
            "stop": ["[INST]", "</s>"],
            "repeat_penalty": 1.1,
            "top_k": 40,
            "top_p": 0.95,
        }

        try:
            response = requests.post(
                f"http://{self.host}:{self.port}/completion",
                json=payload,
                timeout=60,
                stream=stream
            )

            if stream:
                return {"stream": response}
            else:
                return response.json()

        except Exception as e:
            return {"error": str(e)}

    def __enter__(self):
        """Context manager entry"""
        if self.start_server():
            return self
        raise RuntimeError("Failed to start server")

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.stop_server()


def main():
    """Test server manager"""
    manager = MistralServerManager()

    try:
        with manager as server:
            print("\n🎯 Testing server with simple prompt...")
            result = server.send_completion_request("Hello, how are you?", max_tokens=50)

            if "content" in result:
                print(f"Response: {result['content']}")
            else:
                print(f"Error: {result}")

            print("\n📊 Server stats:")
            stats = server.get_server_stats()
            if stats:
                print(f"Context size: {stats.get('n_ctx', 'unknown')}")
                print(f"Model loaded: {stats.get('model_loaded', False)}")

            print("\n✅ Server test completed successfully!")

    except Exception as e:
        print(f"❌ Test failed: {e}")


if __name__ == "__main__":
    main()
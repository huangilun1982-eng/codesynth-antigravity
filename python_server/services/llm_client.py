import requests
import json
import os

class LocalLLMClient:
    """
    Client for interacting with local Ollama instance.
    Defaults to http://localhost:11434
    """
    def __init__(self, base_url="http://localhost:11434", model="gpt-oss:20b"):
        self.base_url = base_url
        self.model = model
        # Allow override via env vars
        if os.getenv("OLLAMA_HOST"):
            self.base_url = os.getenv("OLLAMA_HOST")
        if os.getenv("OLLAMA_MODEL"):
            self.model = os.getenv("OLLAMA_MODEL")

    async def generate_async(self, prompt: str, system: str = None) -> str:
        """
        Async wrapper for generate using asyncio.to_thread to disable blocking.
        This allows the main event loop to continue while waiting for Ollama.
        """
        import asyncio
        return await asyncio.to_thread(self.generate_sync, prompt, system)

    def generate_sync(self, prompt: str, system: str = None) -> str:
        """
        Synchronous generation (renamed from generate).
        """
        url = f"{self.base_url}/api/generate"
        
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False
        }
        
        if system:
            payload["system"] = system

        try:
            response = requests.post(url, json=payload, timeout=60)
            response.raise_for_status()
            result = response.json()
            return result.get("response", "")
        except requests.exceptions.ConnectionError:
            print("Error: Could not connect to Ollama. Is it running?")
            return ""
        except Exception as e:
            print(f"Error calling Ollama: {e}")
            return ""

    def generate(self, prompt: str, system: str = None) -> str:
        """
        Legacy sync method wrapper.
        """
        return self.generate_sync(prompt, system)

# Singleton
llm_client = LocalLLMClient()

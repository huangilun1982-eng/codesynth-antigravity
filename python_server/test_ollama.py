import sys
import os

# Add current dir to path to import services
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services.llm_client import llm_client

def test_ollama():
    print("==========================================")
    print(f"Testing Connection to: {llm_client.base_url}")
    print(f"Using Model: {llm_client.model}")
    print("==========================================")

    try:
        response = llm_client.generate("Say 'Hello CodeSynth!' if you can hear me.")
        if response:
            print(f"✅ Connection Successful!")
            print(f"🤖 AI Response: {response}")
        else:
            print("❌ Connection Failed. Response was empty.")
            print("Troubleshooting:")
            print("1. Is Ollama running? (Try `ollama list` in terminal)")
            print("2. Is the model downloaded? (Try `ollama pull llama3`)")
            
    except Exception as e:
        print(f"❌ Connection Error: {e}")

if __name__ == "__main__":
    test_ollama()

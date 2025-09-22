import os
from huggingface_hub import hf_hub_download


def download_llm_model():
    """
    Downloads the TinyLlama GGUF model from Hugging Face.
    """
    # Use a more stable, higher-quality quantization
    REPO_ID = "TheBloke/TinyLlama-1.1B-Chat-v1.0-GGUF"
    MODEL_FILENAME = "tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf"
    LOCAL_DIR = "models"

    print(f"Downloading model '{MODEL_FILENAME}' from '{REPO_ID}'...")
    try:
        hf_hub_download(
            repo_id=REPO_ID,
            filename=MODEL_FILENAME,
            local_dir=LOCAL_DIR,
            force_download=True,
            resume_download=True,
        )
        print("Download complete. Model saved to the 'models' directory.")
    except Exception as e:
        print(f"An error occurred during download: {e}")
        print("Please check your internet connection or try again later.")


if __name__ == "__main__":
    # Create the models directory if it doesn't exist
    if not os.path.exists("models"):
        os.makedirs("models")
    download_llm_model()

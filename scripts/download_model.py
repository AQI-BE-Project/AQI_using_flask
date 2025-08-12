# scripts/download_model.py
from huggingface_hub import hf_hub_download
# repo_id = "your-username/your-model-repo"  # public
path = hf_hub_download(repo_id="your-username/your-model-repo", filename="model.pkl")
print("Downloaded model to", path)

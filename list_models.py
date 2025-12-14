
import google.generativeai as genai
import streamlit as st
import os

# Try to get API key from secrets or env
api_key = None
try:
    # Mimic app.py logic roughly
    # We can't easily access streamlit secrets from a standalone script without the toml file path or running via streamlit
    # But we can try to find the secrets file manually or ask user.
    # Actually, the user is running on windows, the path is .streamlit/secrets.toml in the current dir.
    
    import toml
    with open(".streamlit/secrets.toml", "r", encoding="utf-8") as f:
        config = toml.load(f)
        api_key = config.get("GOOGLE_API_KEY")
except Exception as e:
    print(f"Could not read secrets.toml: {e}")

if not api_key:
    print("API Key not found in .streamlit/secrets.toml")
    exit(1)

genai.configure(api_key=api_key)

print("Listing available models...")
try:
    for m in genai.list_models():
        if 'generateContent' in m.supported_generation_methods:
            print(f"- {m.name}")
except Exception as e:
    print(f"Error listing models: {e}")

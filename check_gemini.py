# check_gemini.py
import google.generativeai as genai
import pkg_resources

# --- PASTE YOUR API KEY HERE ---
API_KEY = "AIzaSyChh1lPkyuOuPMZadZKw4zrZQqcJPi2sd4"

try:
    # --- 1. Print the library version ---
    version = pkg_resources.get_distribution("google-generativeai").version
    print(f"✅ Found google-generativeai library version: {version}\n")

    genai.configure(api_key=API_KEY)

    # --- 2. List all available models ---
    print("🤖 Attempting to list available models...")
    for m in genai.list_models():
        # Check if the model supports the 'generateContent' method
        if 'generateContent' in m.supported_generation_methods:
            print(f"  - {m.name}")

    print("\n---")
    print("Diagnosis complete. If you see model names above, your environment is working.")
    print("The recommended model to use is 'gemini-1.5-flash-latest'.")


except Exception as e:
    print("\n---")
    print(f"❌ An error occurred: {e}")
    print("This confirms a problem with your library or API key.")
    print("The most likely solution is to update the library by running:")
    print("pip install --upgrade google-generativeai")
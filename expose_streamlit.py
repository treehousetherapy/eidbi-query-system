# expose_streamlit.py
from pyngrok import ngrok
import time
import requests
import json

# Check if Streamlit is running
def is_streamlit_running():
    try:
        response = requests.get("http://localhost:8501")
        return response.status_code == 200
    except:
        return False

# Start ngrok tunnel
def start_ngrok():
    public_url = ngrok.connect(8501)
    print(f"\n🔗 Your EIDBI Assistant is now accessible from: {public_url}")
    print("📱 Share this URL to allow others to access your application")
    print("⚠️ Note: This URL will only work while this script is running")
    print("❌ Press Ctrl+C to stop the tunnel when you're finished\n")
    return public_url

# Main function
def main():
    if not is_streamlit_running():
        print("❌ Error: Streamlit app is not running.")
        print("Please start the Streamlit app first with the command:")
        print("   .\\start_frontend.bat")
        return

    print("✅ Streamlit app is running!")
    print("🚀 Creating public URL with Ngrok...")
    
    try:
        public_url = start_ngrok()
        
        # Keep the script running
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n👋 Shutting down the tunnel. Your app is no longer accessible from outside.")
        ngrok.kill()

if __name__ == "__main__":
    main() 
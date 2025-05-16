# expose_app.py - A script to expose your local Streamlit app to the internet
import requests
import socket
import webbrowser
import time
import subprocess
import sys
import os

def check_streamlit():
    """Check if Streamlit is running on port 8501"""
    try:
        response = requests.get("http://localhost:8501", timeout=2)
        return response.status_code == 200
    except:
        return False

def get_public_url_serveo():
    """Get a public URL using Serveo (no auth required)"""
    try:
        print("Setting up SSH tunnel via serveo.net...")
        # Run SSH command to forward port 8501 to serveo.net
        process = subprocess.Popen(
            ["ssh", "-R", "80:localhost:8501", "serveo.net"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True
        )
        
        # Wait for the URL to appear in the output
        for line in process.stdout:
            if "Forwarding HTTP traffic from" in line:
                url = line.split("Forwarding HTTP traffic from")[1].strip()
                return url, process
                
        # If we didn't get a URL after 10 seconds, something went wrong
        return None, process
    except Exception as e:
        print(f"Error setting up Serveo tunnel: {str(e)}")
        return None, None

def get_public_url_ngrok():
    """Get a public URL using ngrok (no auth, limited to 1 hour)"""
    try:
        # Install pyngrok if not already installed
        try:
            from pyngrok import ngrok
        except ImportError:
            print("Installing pyngrok...")
            subprocess.check_call([sys.executable, "-m", "pip", "install", "pyngrok"])
            from pyngrok import ngrok
        
        # Start ngrok
        print("Setting up ngrok tunnel...")
        public_url = ngrok.connect(8501)
        print(f"Ngrok tunnel established at: {public_url}")
        return public_url, None
    except Exception as e:
        print(f"Error setting up ngrok tunnel: {str(e)}")
        return None, None

def main():
    print("📡 EIDBI Assistant Exposure Tool")
    print("-------------------------------")
    
    # Check if Streamlit is running
    print("Checking if Streamlit is running...")
    if not check_streamlit():
        print("❌ Error: Streamlit app is not running on port 8501.")
        print("Please start the Streamlit app first with:")
        print("   .\\start_frontend.bat")
        return
    
    print("✅ Streamlit server detected at http://localhost:8501")
    
    # Try to get a public URL
    # First try serveo.net
    print("\nAttempting to create a public URL...")
    
    # Use localhost.run (SSH-based, no auth required)
    try:
        print("Setting up SSH tunnel via localhost.run...")
        process = subprocess.Popen(
            ["ssh", "-R", "80:localhost:8501", "localhost.run"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True
        )
        
        # Display the public URL
        print("\n✅ Tunnel should be established!")
        print("🔗 Your EIDBI Assistant should be accessible at the URL shown above")
        print("📱 Share this URL to allow others to access your application")
        print("⚠️ Note: This URL will only work while this script is running")
        print("❌ Press Ctrl+C to stop the tunnel when you're finished\n")
        
        # Keep the tunnel alive
        try:
            process.wait()
        except KeyboardInterrupt:
            print("\n👋 Shutting down the tunnel. Your app is no longer accessible from outside.")
            process.terminate()
    except Exception as e:
        print(f"Error setting up tunnel: {str(e)}")
        print("\n❌ Could not create a tunnel.")
        print("Please consider one of these alternatives:")
        print("1. Install ngrok and run: ngrok http 8501")
        print("2. Deploy to Streamlit Cloud: https://streamlit.io/cloud")
        print("3. Deploy to a cloud service like Heroku, Google Cloud, or AWS")

if __name__ == "__main__":
    main() 
# open_tunnel.py - A simple script to create a tunnel from localhost to public internet

import requests
from requests.exceptions import RequestException
import time
import os
import json
import subprocess
import sys

def check_streamlit():
    """Check if Streamlit is running on port 8501"""
    try:
        response = requests.get("http://localhost:8501", timeout=2)
        if response.status_code == 200:
            return True
        return False
    except RequestException:
        return False

def create_tunnel():
    """Create a tunnel using a free service"""
    tunnel_url = None
    
    # Try using the pythonhosted.org tunnel service
    try:
        response = requests.post("https://console.online.net/tunnel", json={"port": 8501})
        if response.status_code == 200:
            data = response.json()
            tunnel_url = data.get("url")
            if tunnel_url:
                print(f"\n✅ Success! Your EIDBI Assistant is now accessible from: {tunnel_url}")
                print("This URL will be active until you stop this script (Ctrl+C).")
                return tunnel_url
    except Exception as e:
        print(f"Error with tunnel service: {str(e)}")
    
    # If that fails, try localtunnel via pypi package
    try:
        print("Installing localtunnel Python package...")
        os.system(f"{sys.executable} -m pip install --quiet localtunnel")
        
        # Import after installation
        from localtunnel import Tunnel
        tunnel = Tunnel(port=8501)
        tunnel_url = tunnel.url
        print(f"\n✅ Success! Your EIDBI Assistant is now accessible from: {tunnel_url}")
        print("This URL will be active until you stop this script (Ctrl+C).")
        
        # Keep the tunnel alive
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            tunnel.close()
            print("\n❌ Tunnel closed. Your app is no longer accessible from outside.")
            return None
            
        return tunnel_url
        
    except Exception as e:
        print(f"Error with localtunnel: {str(e)}")
    
    return None

def main():
    print("Checking if Streamlit is running...")
    if not check_streamlit():
        print("❌ Streamlit is not running! Please start it first with:")
        print("   .\\start_frontend.bat")
        return
    
    print("✅ Streamlit detected. Creating a public tunnel...")
    tunnel_url = create_tunnel()
    
    if not tunnel_url:
        print("\n❌ Could not create a tunnel.")
        print("Please consider one of these alternatives:")
        print("1. Sign up for a free ngrok account: https://dashboard.ngrok.com/signup")
        print("2. Deploy to Streamlit Cloud: https://streamlit.io/cloud")
        print("3. Deploy to a cloud service like Heroku, Google Cloud, or AWS")

if __name__ == "__main__":
    main() 
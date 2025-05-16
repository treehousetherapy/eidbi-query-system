# cloudflare_tunnel.py - Expose Streamlit to the internet without authentication
import os
import sys
import time
import subprocess
import requests
from flask import Flask, Response, request
from flask_cloudflared import _run_cloudflared
import threading

# Create a simple Flask app that proxies to Streamlit
app = Flask(__name__)

@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def proxy(path):
    """Proxy all requests to the local Streamlit server"""
    url = f"http://localhost:8501/{path}"
    
    # Forward the request to Streamlit
    try:
        resp = requests.request(
            method=request.method,
            url=url,
            headers={key: value for (key, value) in request.headers if key != 'Host'},
            data=request.get_data(),
            cookies=request.cookies,
            allow_redirects=False)
        
        # Create a Flask response
        response = Response(resp.content, resp.status_code)
        
        # Pass headers from Streamlit to client
        for key, value in resp.headers.items():
            if key.lower() != 'content-length':  # Skip content-length as we'll set it correctly
                response.headers[key] = value
                
        return response
    except Exception as e:
        return f"Error: Could not connect to Streamlit server. Details: {str(e)}", 500

def check_streamlit():
    """Check if Streamlit is running on port 8501"""
    try:
        response = requests.get("http://localhost:8501", timeout=2)
        return response.status_code == 200
    except:
        return False

def main():
    """Main function to start tunneling"""
    print("📡 EIDBI Assistant Tunneling Tool")
    print("--------------------------------")
    
    # Check if Streamlit is running
    print("Checking if Streamlit is running...")
    if not check_streamlit():
        print("❌ Error: Streamlit app is not running on port 8501.")
        print("Please start the Streamlit app first with:")
        print("   .\\start_frontend.bat")
        return
    
    print("✅ Streamlit server detected at http://localhost:8501")
    print("Starting tunneling service...")
    
    # Start the Flask app with Cloudflared
    # This will download cloudflared binary if needed
    cloudflared = _run_cloudflared(port=5000, metrics_port=8099)
    public_url = cloudflared.tunnel_url
    
    print("\n✅ Tunnel established!")
    print(f"🔗 Your EIDBI Assistant is now accessible from: {public_url}")
    print("📱 Share this URL to allow others to access your application")
    print("⚠️ Note: This URL will only work while this script is running")
    print("❌ Press Ctrl+C to stop the tunnel when you're finished\n")
    
    # Start Flask in a separate thread
    threading.Thread(target=lambda: app.run(port=5000, debug=False)).start()
    
    try:
        # Keep the main thread running
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n👋 Shutting down the tunnel. Your app is no longer accessible from outside.")
        cloudflared.kill()

if __name__ == "__main__":
    main() 
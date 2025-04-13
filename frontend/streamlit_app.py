# eidbi-query-system/frontend/streamlit_app.py

import streamlit as st
import requests
import json

# Configuration
# Assumes backend is running locally on port 8000
# In production, change this to your deployed backend URL
BACKEND_URL = "http://localhost:8000"
QUERY_ENDPOINT = f"{BACKEND_URL}/query"

st.set_page_config(layout="wide", page_title="EIDBI AI Query System")

st.title("📚 EIDBI AI Query System")
st.caption("Query scraped Minnesota EIDBI program information using AI")

# --- User Input ---
query_text = st.text_input("Enter your query about the EIDBI program:", placeholder="e.g., Who is eligible for EIDBI services?")
num_results = st.slider("Context Chunks to Retrieve:", min_value=1, max_value=10, value=3, help="How many relevant text chunks to fetch for context.")

# --- Query Button and Results --- 
if st.button("Ask", type="primary"):
    if not query_text:
        st.warning("Please enter a query.")
    else:
        with st.spinner("Finding relevant information and generating answer..."):
            try:
                # Prepare request payload
                payload = {
                    "query_text": query_text,
                    "num_results": num_results
                }

                # Send request to backend
                response = requests.post(QUERY_ENDPOINT, json=payload)
                response.raise_for_status() # Raise HTTP errors

                # Parse response
                results_data = response.json()
                answer = results_data.get("answer")
                retrieved_ids = results_data.get("retrieved_chunk_ids", [])

                st.subheader("Answer")
                if not answer:
                    st.error("The backend did not return an answer.")
                else:
                    st.markdown(answer) # Display the LLM's answer

                # Optionally display the IDs of the chunks used for context
                if retrieved_ids:
                    with st.expander("Retrieved Context Chunk IDs"):
                        st.write(retrieved_ids)

            except requests.exceptions.ConnectionError:
                st.error(f"Could not connect to the backend at {BACKEND_URL}. Is it running?")
            except requests.exceptions.RequestException as e:
                st.error(f"Error during search request: {e}")
                try:
                     error_detail = e.response.json().get("detail", "No details provided.")
                     st.error(f"Backend Error: {error_detail}")
                except (AttributeError, ValueError, json.JSONDecodeError):
                     st.error("Could not parse error response from backend.")
            except Exception as e:
                st.error(f"An unexpected error occurred: {e}") 
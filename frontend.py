import os

import streamlit as st
import requests

# Where the Flask backend lives. By default this is the copy deployed on Render.
# To use a backend running on your own machine, set BACKEND_URL before starting
# Streamlit, for example BACKEND_URL=http://127.0.0.1:5000
BACKEND_URL = os.environ.get("BACKEND_URL", "https://python-app-api.onrender.com").rstrip("/")

st.set_page_config(page_title="Two-File App")
st.title("Python Frontend")

name = st.text_input("What is your name?")

if st.button("Send to Backend"):
    try:
        # '/api/data' is the route defined in backend.py. Passing the name through
        # 'params' lets requests encode spaces and symbols such as '&' correctly.
        response = requests.get(f"{BACKEND_URL}/api/data", params={"name": name})
        result = response.json()

        st.write("### Response from backend.py:")
        st.success(result['message'])

        if 'data_length' in result:
            st.info(f"The backend calculated your name length as: {result['data_length']}")

    except requests.exceptions.ConnectionError:
        st.error("Error: Could not connect to the backend URL.")

"""The frontend: a Streamlit page that sends a name to the backend and shows the reply."""

import os

import streamlit as st
import requests

# Where the Flask backend lives. By default this is the copy deployed on Render.
# To use a backend running on your own machine, set BACKEND_URL before starting
# Streamlit, for example BACKEND_URL=http://127.0.0.1:5000
BACKEND_URL = os.environ.get("BACKEND_URL", "https://python-app-api.onrender.com").rstrip("/")

# How long to wait for a reply. The hosted backend goes to sleep when nobody is
# using it, and the first request after that can take about a minute.
TIMEOUT_SECONDS = 90


class BackendError(Exception):
    """Something went wrong while asking the backend. Its text is shown on the page."""


def ask_backend(name):
    """Send the name to the backend and return its reply as a dictionary."""
    if not BACKEND_URL.startswith(("http://", "https://")):
        raise BackendError(f"BACKEND_URL must start with http:// or https://, but it is set to '{BACKEND_URL}'.")

    try:
        # '/api/data' is the route defined in backend.py. Passing the name through
        # 'params' lets requests encode spaces and symbols such as '&' correctly.
        response = requests.get(f"{BACKEND_URL}/api/data", params={"name": name}, timeout=TIMEOUT_SECONDS)
    except requests.exceptions.Timeout:
        raise BackendError("The backend took too long to answer. Please try again.")
    except requests.exceptions.ConnectionError:
        raise BackendError("Could not connect to the backend URL.")
    except requests.exceptions.RequestException as error:
        raise BackendError(f"The request could not be sent: {error}")

    try:
        result = response.json()
    except ValueError:
        raise BackendError(f"The backend did not answer in JSON (status {response.status_code}).")

    if not isinstance(result, dict) or "message" not in result:
        raise BackendError("The backend answered in a form this page does not understand.")
    if not response.ok or result.get("status") == "error":
        # The backend explains its own errors in 'message'.
        raise BackendError(result["message"])
    return result


st.set_page_config(page_title="Two-File App")
st.title("Python Frontend")
st.caption(f"Backend: {BACKEND_URL}")

name = st.text_input("What is your name?")

if st.button("Send to Backend"):
    try:
        with st.spinner("Waiting for the backend..."):
            result = ask_backend(name)
    except BackendError as error:
        st.error(f"Error: {error}")
    else:
        st.write("### Response from backend.py:")
        st.success(result['message'])

        if 'data_length' in result:
            st.info(f"The backend calculated your name length as: {result['data_length']}")

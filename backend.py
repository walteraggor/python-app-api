"""The backend: a small Flask API that the Streamlit frontend talks to."""

from flask import Flask, jsonify, request
from werkzeug.exceptions import HTTPException

app = Flask(__name__)

# The longest name the API accepts. A longer one gets an error in reply.
MAX_NAME_LENGTH = 100


@app.route('/', methods=['GET'])
def index():
    """Describe the service, so the base address shows more than 'Not Found'."""
    return jsonify({
        "service": "python-app-api",
        "routes": {
            "/api/data?name=Ada": "Replies with a message and the length of the name."
        }
    })


# This is a 'Route'. The frontend will 'hit' this URL to get data.
@app.route('/api/data', methods=['GET'])
def get_info():
    # Spaces around the name are dropped. A missing or blank name becomes 'Stranger'.
    user_input = request.args.get('name', '').strip() or 'Stranger'

    if len(user_input) > MAX_NAME_LENGTH:
        # The number after the dictionary is the HTTP status code. 400 means 'bad request'.
        return jsonify({
            "status": "error",
            "message": f"That name is too long. Please use {MAX_NAME_LENGTH} characters or fewer."
        }), 400

    # Returning a Dictionary (which Flask turns into JSON)
    return jsonify({
        "status": "success",
        "message": f"Server processed: {user_input}",
        "data_length": len(user_input)
    })


# Flask answers problems such as an unknown address (404) with an HTML page.
# This replaces that page with JSON, so a program calling the API always gets
# the same kind of reply.
@app.errorhandler(HTTPException)
def handle_http_error(error):
    return jsonify({"status": "error", "message": error.description}), error.code


if __name__ == '__main__':
    # Running on port 5000. This block is for your own machine;
    # on a host such as Render, Gunicorn starts the app instead.
    app.run(port=5000, debug=True)

# python-app-api

[![Tests](https://github.com/walteraggor/python-app-api/actions/workflows/tests.yml/badge.svg)](https://github.com/walteraggor/python-app-api/actions/workflows/tests.yml)

A small two-part Python app that shows how a frontend talks to a backend over HTTP.

A Streamlit page asks for your name and sends it to a Flask API. The API replies with JSON, and the page displays the result.

```
frontend.py (Streamlit)  -- GET /api/data?name=Ada -->  backend.py (Flask)
                         <-------- JSON reply --------
```

| File | Role |
|---|---|
| `backend.py` | Flask API. Its main route is `GET /api/data` |
| `frontend.py` | Streamlit page that calls the API and shows the reply |
| `tests/` | Tests for both files |
| `requirements.txt` | Flask, Streamlit, Requests and Gunicorn |

## The API

```
GET /api/data?name=Ada
```

```json
{
  "data_length": 3,
  "message": "Server processed: Ada",
  "status": "success"
}
```

You can try it on the hosted copy: <https://python-app-api.onrender.com/api/data?name=Ada>. The first request after a quiet spell can take about a minute, because the free host puts the service to sleep.

- Spaces before and after the name are dropped.
- If `name` is left out or blank, the server uses `Stranger`.
- A name longer than 100 characters is refused with status 400:

```json
{
  "message": "That name is too long. Please use 100 characters or fewer.",
  "status": "error"
}
```

Every error has this shape, including the 404 for an address that does not exist. A program calling the API can always read `status` and `message`.

The base address, `GET /`, replies with a short description of the service.

## The page

`frontend.py` sends whatever is in the name box when you press **Send to Backend**. A good reply is shown in a green box, with the length the backend counted underneath.

If something goes wrong, the page says what in a red box: the backend could not be reached, it took longer than 90 seconds, it did not reply in JSON, or it replied with an error of its own such as the one above.

## Run it locally

Install the dependencies:

```bash
git clone https://github.com/walteraggor/python-app-api.git
cd python-app-api
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

Start the backend in one terminal. It listens on `http://127.0.0.1:5000`:

```bash
python backend.py
```

Start the frontend in a second terminal and point it at your local backend:

```bash
# macOS and Linux
BACKEND_URL=http://127.0.0.1:5000 streamlit run frontend.py
```

```powershell
# Windows PowerShell
$env:BACKEND_URL = "http://127.0.0.1:5000"
streamlit run frontend.py
```

Streamlit opens the page in your browser. Type a name and press **Send to Backend**. The line under the title shows which backend the page is using.

If `BACKEND_URL` is not set, the frontend calls the hosted backend at `https://python-app-api.onrender.com`.

## Tests

```bash
python -m unittest
```

The tests need nothing beyond `requirements.txt` and never use the network.

- `tests/test_backend.py` calls the API through Flask's test client.
- `tests/test_frontend.py` runs the page with Streamlit's `AppTest`: first against stand-in replies, to check each success and error message, then against `backend.py` itself. That last group fails if the two files stop agreeing on the address or on the shape of the reply.

GitHub runs the tests on Linux and Windows for every push and pull request.

## Deploying the backend

The backend runs on any host that can start a Python web service. On [Render](https://render.com), create a Web Service from this repository with:

- Build command: `pip install -r requirements.txt`
- Start command: `gunicorn backend:app`

On Render's free plan a service goes to sleep after 15 minutes without traffic, so the first request after a pause can take about a minute.

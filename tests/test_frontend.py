"""Tests for frontend.py.

Streamlit's AppTest runs the page without a browser. requests.get is swapped
for a stand-in, so these tests never use the network or the hosted backend.

The last group hands the page's requests to backend.py itself. If the two
files ever stop agreeing on the address or the shape of the reply, those tests
fail.
"""

import logging
import os
import unittest
from unittest import mock
from urllib.parse import urlsplit

import requests
from streamlit.testing.v1 import AppTest

import backend

FRONTEND = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "frontend.py")
TEST_URL = "http://backend.test"
HOSTED_URL = "https://python-app-api.onrender.com"


def setUpModule():
    # Each time AppTest starts, Streamlit logs a "missing ScriptRunContext" warning
    # that its own text says can be ignored. Keep it out of the test output.
    logging.disable(logging.WARNING)


def tearDownModule():
    logging.disable(logging.NOTSET)


def reply(status_code, payload=None):
    """Build a stand-in for the response object that requests.get returns.

    Leave out the payload for a reply that is not JSON.
    """
    response = mock.Mock()
    response.status_code = status_code
    response.ok = status_code < 400
    if payload is None:
        response.json.side_effect = ValueError("this reply is not JSON")
    else:
        response.json.return_value = payload
    return response


def real_backend(url, params=None, timeout=None):
    """Stand in for requests.get by passing the request straight to backend.py."""
    answer = backend.app.test_client().get(urlsplit(url).path, query_string=params)
    return reply(answer.status_code, answer.get_json(silent=True))


class PageTestCase(unittest.TestCase):
    def setUp(self):
        self.use_backend_url(TEST_URL)

    def use_backend_url(self, url):
        """Set BACKEND_URL for this test only. None removes it."""
        patcher = mock.patch.dict(os.environ)
        patcher.start()
        self.addCleanup(patcher.stop)
        os.environ.pop("BACKEND_URL", None)
        if url is not None:
            os.environ["BACKEND_URL"] = url

    def open_page(self):
        page = AppTest.from_file(FRONTEND, default_timeout=30).run()
        self.assert_no_crash(page)
        return page

    def press_send(self, name, get):
        """Open the page, type a name, press the button and return the page.

        'get' takes the place of requests.get while the page runs.
        """
        with mock.patch("requests.get", get):
            page = self.open_page()
            page.text_input[0].set_value(name).run()
            page.button[0].click().run()
        self.assert_no_crash(page)
        return page

    def assert_no_crash(self, page):
        crashes = [crash.value for crash in page.exception]
        self.assertEqual(crashes, [], "the page showed a traceback")

    def assert_shows_error(self, page, message):
        self.assertEqual([box.value for box in page.error], [f"Error: {message}"])
        self.assertEqual(len(page.success), 0)
        self.assertEqual(len(page.info), 0)


class PageTests(PageTestCase):
    def test_the_page_opens_with_an_empty_name_box(self):
        page = self.open_page()
        self.assertEqual([title.value for title in page.title], ["Python Frontend"])
        self.assertEqual([(box.label, box.value) for box in page.text_input], [("What is your name?", "")])
        self.assertEqual([button.label for button in page.button], ["Send to Backend"])

    def test_the_page_says_which_backend_it_uses(self):
        self.assertEqual([caption.value for caption in self.open_page().caption], [f"Backend: {TEST_URL}"])

    def test_nothing_is_sent_before_the_button_is_pressed(self):
        get = mock.Mock(return_value=reply(200, {"status": "success", "message": "hello"}))
        with mock.patch("requests.get", get):
            page = self.open_page()
            page.text_input[0].set_value("Ada").run()
        get.assert_not_called()
        self.assertEqual(len(page.success), 0)

    def test_the_name_is_sent_to_the_data_route(self):
        get = mock.Mock(return_value=reply(200, {"status": "success", "message": "hello"}))
        self.press_send("Tom & Jerry", get)
        get.assert_called_once()
        self.assertEqual(get.call_args.args, (f"{TEST_URL}/api/data",))
        self.assertEqual(get.call_args.kwargs["params"], {"name": "Tom & Jerry"})

    def test_the_request_does_not_wait_forever(self):
        get = mock.Mock(return_value=reply(200, {"status": "success", "message": "hello"}))
        self.press_send("Ada", get)
        self.assertGreater(get.call_args.kwargs["timeout"], 0)

    def test_the_hosted_backend_is_used_when_no_address_is_set(self):
        self.use_backend_url(None)
        get = mock.Mock(return_value=reply(200, {"status": "success", "message": "hello"}))
        self.press_send("Ada", get)
        self.assertEqual(get.call_args.args, (f"{HOSTED_URL}/api/data",))

    def test_a_slash_at_the_end_of_the_address_does_no_harm(self):
        self.use_backend_url(TEST_URL + "/")
        get = mock.Mock(return_value=reply(200, {"status": "success", "message": "hello"}))
        self.press_send("Ada", get)
        self.assertEqual(get.call_args.args, (f"{TEST_URL}/api/data",))

    def test_a_successful_reply_is_shown(self):
        get = mock.Mock(return_value=reply(200, {
            "status": "success", "message": "Server processed: Ada", "data_length": 3,
        }))
        page = self.press_send("Ada", get)
        self.assertEqual([box.value for box in page.success], ["Server processed: Ada"])
        self.assertEqual([box.value for box in page.info], ["The backend calculated your name length as: 3"])
        self.assertEqual(len(page.error), 0)

    def test_a_reply_without_a_length_still_shows_its_message(self):
        page = self.press_send("Ada", mock.Mock(return_value=reply(200, {"status": "success", "message": "hello"})))
        self.assertEqual([box.value for box in page.success], ["hello"])
        self.assertEqual(len(page.info), 0)


class ProblemTests(PageTestCase):
    def test_the_backends_own_error_message_is_shown(self):
        replies = {
            "error status": reply(400, {"status": "error", "message": "That name is too long."}),
            "error marked only in the body": reply(200, {"status": "error", "message": "That name is too long."}),
            "error marked only by the status": reply(500, {"message": "That name is too long."}),
        }
        for case, response in replies.items():
            with self.subTest(case=case):
                page = self.press_send("Ada", mock.Mock(return_value=response))
                self.assert_shows_error(page, "That name is too long.")

    def test_a_reply_that_is_not_json(self):
        page = self.press_send("Ada", mock.Mock(return_value=reply(502)))
        self.assert_shows_error(page, "The backend did not answer in JSON (status 502).")

    def test_a_reply_in_an_unexpected_form(self):
        for payload in (["a", "list"], "just text", {"status": "success"}):
            with self.subTest(payload=payload):
                page = self.press_send("Ada", mock.Mock(return_value=reply(200, payload)))
                self.assert_shows_error(page, "The backend answered in a form this page does not understand.")

    def test_a_backend_that_is_not_running(self):
        get = mock.Mock(side_effect=requests.exceptions.ConnectionError("connection refused"))
        self.assert_shows_error(self.press_send("Ada", get), "Could not connect to the backend URL.")

    def test_a_backend_that_is_too_slow(self):
        for problem in (requests.exceptions.ReadTimeout, requests.exceptions.ConnectTimeout):
            with self.subTest(problem=problem.__name__):
                page = self.press_send("Ada", mock.Mock(side_effect=problem("timed out")))
                self.assert_shows_error(page, "The backend took too long to answer. Please try again.")

    def test_an_address_without_http_in_front(self):
        self.use_backend_url("127.0.0.1:5000")
        get = mock.Mock()
        page = self.press_send("Ada", get)
        self.assert_shows_error(
            page, "BACKEND_URL must start with http:// or https://, but it is set to '127.0.0.1:5000'.")
        get.assert_not_called()

    def test_any_other_trouble_with_the_request(self):
        get = mock.Mock(side_effect=requests.exceptions.TooManyRedirects("Exceeded 30 redirects."))
        page = self.press_send("Ada", get)
        self.assert_shows_error(page, "The request could not be sent: Exceeded 30 redirects.")


class FrontendWithBackendTests(PageTestCase):
    """The two files together: the page's requests are answered by backend.py."""

    def test_a_name_makes_the_round_trip(self):
        page = self.press_send("Ada", real_backend)
        self.assertEqual([box.value for box in page.success], ["Server processed: Ada"])
        self.assertEqual([box.value for box in page.info], ["The backend calculated your name length as: 3"])
        self.assertEqual(len(page.error), 0)

    def test_symbols_make_the_round_trip(self):
        page = self.press_send("Tom & Jerry", real_backend)
        self.assertEqual([box.value for box in page.success], ["Server processed: Tom & Jerry"])
        self.assertEqual([box.value for box in page.info], ["The backend calculated your name length as: 11"])

    def test_an_empty_name_box_is_answered_with_stranger(self):
        page = self.press_send("", real_backend)
        self.assertEqual([box.value for box in page.success], ["Server processed: Stranger"])

    def test_a_name_that_is_too_long_shows_the_backends_error(self):
        page = self.press_send("x" * (backend.MAX_NAME_LENGTH + 1), real_backend)
        self.assert_shows_error(
            page, f"That name is too long. Please use {backend.MAX_NAME_LENGTH} characters or fewer.")

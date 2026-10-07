"""Tests for backend.py.

They use Flask's test client, which calls the app directly, so no server has to
be running.
"""

import unittest

from backend import MAX_NAME_LENGTH, app


class DataRouteTests(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()

    def ask(self, **params):
        """Call /api/data with the given query parameters."""
        return self.client.get("/api/data", query_string=params)

    def test_a_name_is_processed(self):
        response = self.ask(name="Ada")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json(), {
            "status": "success",
            "message": "Server processed: Ada",
            "data_length": 3,
        })

    def test_the_reply_is_json(self):
        self.assertEqual(self.ask(name="Ada").content_type, "application/json")

    def test_no_name_becomes_stranger(self):
        response = self.client.get("/api/data")
        self.assertEqual(response.get_json()["message"], "Server processed: Stranger")
        self.assertEqual(response.get_json()["data_length"], 8)

    def test_a_blank_name_becomes_stranger(self):
        for blank in ("", " ", "   ", "\t"):
            with self.subTest(name=blank):
                self.assertEqual(self.ask(name=blank).get_json()["message"], "Server processed: Stranger")

    def test_spaces_around_the_name_are_dropped(self):
        result = self.ask(name="  Ada  ").get_json()
        self.assertEqual(result["message"], "Server processed: Ada")
        self.assertEqual(result["data_length"], 3)

    def test_spaces_inside_the_name_are_kept(self):
        result = self.ask(name="Ada Lovelace").get_json()
        self.assertEqual(result["message"], "Server processed: Ada Lovelace")
        self.assertEqual(result["data_length"], 12)

    def test_symbols_and_accents_survive_the_trip(self):
        for name in ("Tom & Jerry", "50% = half?", "Zoë", "Владимир", "李雷"):
            with self.subTest(name=name):
                result = self.ask(name=name).get_json()
                self.assertEqual(result["message"], f"Server processed: {name}")
                self.assertEqual(result["data_length"], len(name))

    def test_the_longest_allowed_name_is_accepted(self):
        response = self.ask(name="x" * MAX_NAME_LENGTH)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["data_length"], MAX_NAME_LENGTH)

    def test_a_name_that_is_too_long_is_refused(self):
        response = self.ask(name="x" * (MAX_NAME_LENGTH + 1))
        self.assertEqual(response.status_code, 400)
        result = response.get_json()
        self.assertEqual(result["status"], "error")
        self.assertIn(str(MAX_NAME_LENGTH), result["message"])
        self.assertNotIn("data_length", result)

    def test_only_get_requests_are_allowed(self):
        response = self.client.post("/api/data", data={"name": "Ada"})
        self.assertEqual(response.status_code, 405)
        self.assertEqual(response.get_json()["status"], "error")


class OtherAddressTests(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()

    def test_the_base_address_describes_the_service(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        result = response.get_json()
        self.assertEqual(result["service"], "python-app-api")
        self.assertTrue(any(route.startswith("/api/data") for route in result["routes"]))

    def test_the_route_named_on_the_base_address_works(self):
        for route in self.client.get("/").get_json()["routes"]:
            with self.subTest(route=route):
                self.assertEqual(self.client.get(route).status_code, 200)

    def test_an_unknown_address_gets_a_json_error(self):
        response = self.client.get("/no/such/page")
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.content_type, "application/json")
        result = response.get_json()
        self.assertEqual(result["status"], "error")
        self.assertTrue(result["message"])

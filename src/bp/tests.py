from django import urls
from django.test import TestCase, Client
from bp import logic


class Logic(TestCase):
    def test_logic_row_count(self):
        self.assertEqual(logic.row_count(), 0)


class Views(TestCase):
    def setUp(self):
        self.c = Client()

    def test_ping(self):
        resp = self.c.get(urls.reverse("ping"))
        self.assertEqual(resp.content.decode(), "pong")

    def test_status(self):
        self.assertTrue(False)

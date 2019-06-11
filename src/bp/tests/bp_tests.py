import os
from os.path import join
from datetime import datetime, timezone
from unittest.mock import patch
import json
from django import urls
from django.test import TestCase, Client
from bp import logic
import pytest
from freezegun import freeze_time


class Model(TestCase):
    def test_foo(self):
        pass


class Logic(TestCase):
    def setUp(self):
        json_fixture = """
        {
        "ProtocolSequencingNumber": "s4-3",
        "ProtocolTitle": "Cell culture and transfection",
        "IsProtocol": true,
        "ProtocolStatus": 0,
        "URI": "https://en.bio-protocol.org/rap.aspx?eid=24419&item=s4-3"
        }"""
        fixture = json.loads(json_fixture)
        fixture["msid"] = 12345
        self.fixture = fixture

        this_dir = os.path.dirname(os.path.realpath(__file__))
        self.fixture_dir = join(this_dir, "fixtures")

    def test_logic_row_count(self):
        self.assertEqual(logic.row_count(), 0)

    def test_logic_row_count_non_zero(self):
        logic._add_result(self.fixture)
        self.assertEqual(logic.row_count(), 1)

    # do I really need pytest-freezetime? can I make do with just freezetime?
    @pytest.mark.freeze_time("1997-08-29T06:14:00Z")
    def test_last_updated(self):
        "returns the date of the most recent modification to the data in the database"
        logic._add_result(self.fixture)
        expected_dt = datetime(
            year=1997, month=8, day=29, hour=6, minute=14, tzinfo=timezone.utc
        ).isoformat()
        self.assertEqual(logic.last_updated(), expected_dt)

    def test_last_update(self):
        "returns the data of the most recent modification to the data in the database"
        dt1 = datetime(
            year=1997, month=8, day=29, hour=6, minute=14, tzinfo=timezone.utc
        )
        dt2 = datetime(
            year=2019, month=8, day=29, hour=6, minute=14, tzinfo=timezone.utc
        )
        with freeze_time(dt2):
            logic._add_result(self.fixture)
        with freeze_time(dt1):
            self.fixture["msid"] = 12344
            logic._add_result(self.fixture)
        expected_dt = dt2.isoformat()
        self.assertEqual(logic.last_updated(), expected_dt)

    def test_validate(self):
        "validate() returns the data if the data is valid"
        good_result = {
            "protocol_sequencing_number": "s4-3",
            "protocol_title": "Cell culture and transfection",
            "is_protocol": True,
            "protocol_status": 0,
            "uri": "https://en.bio-protocol.org/rap.aspx?eid=24419&item=s4-3",
            "msid": 12345,
        }
        self.assertEqual(logic.validate(good_result), good_result)

    def test_validate_bad_data(self):
        bad_result = {}
        self.assertRaises(logic.ValidationError, logic.validate, bad_result)

    def test_add_result(self):
        fixture = join(self.fixture_dir, "example-output.json")
        logic.add_result(json.load(open(fixture, "r")))
        self.assertEqual(logic.row_count(), 6)


class FundamentalViews(TestCase):
    def setUp(self):
        self.c = Client()

    def test_ping(self):
        resp = self.c.get(urls.reverse("ping"))
        self.assertEqual(resp.content.decode(), "pong")

    def test_status(self):
        resp = self.c.get(urls.reverse("status"))
        expected = {"last-updated": None, "row-count": 0}
        self.assertEqual(resp.json(), expected)

    def test_bad_status(self):
        with patch("bp.logic.last_updated", raises=RuntimeError):
            resp = self.c.get(urls.reverse("status"))
            self.assertEqual(resp.status_code, 500)
            self.assertEqual(resp.json(), {})


class Views(TestCase):
    def setUp(self):
        pass

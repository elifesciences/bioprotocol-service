import os
from os.path import join
from datetime import datetime, timezone
from unittest.mock import patch
import json
from django import urls
from django.test import TestCase, Client
from bp import logic, models, utils
import pytest
from freezegun import freeze_time

_this_dir = os.path.dirname(os.path.realpath(__file__))
FIXTURE_DIR = join(_this_dir, "fixtures")


class Model(TestCase):
    def test_foo(self):
        pass


class Logic(TestCase):
    maxDiff = None

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

    def test_logic_row_count(self):
        self.assertEqual(logic.row_count(), 0)

    def test_logic_row_count_non_zero(self):
        logic._add_result_item(self.fixture)
        self.assertEqual(logic.row_count(), 1)

    # do I really need pytest-freezetime? can I make do with just freezetime?
    @pytest.mark.freeze_time("1997-08-29T06:14:00Z")
    def test_last_updated(self):
        "returns the date of the most recent modification to the data in the database"
        logic._add_result_item(self.fixture)
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
            logic._add_result_item(self.fixture)
        with freeze_time(dt1):
            self.fixture["msid"] = 12344
            logic._add_result_item(self.fixture)
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

    def test_validate_missing_keys(self):
        bad_result = {}
        with self.assertRaises(logic.ValidationError) as err:
            logic.validate(bad_result)
        expected_message = "ValidationError: 'AssertionError' thrown with message 'result is missing keys: "
        self.assertTrue(logic.format_error(err.exception).startswith(expected_message))

    def test_validate_extra_keys(self):
        bad_result = {
            "protocol_sequencing_number": "s4-3",
            "protocol_title": "Cell culture and transfection",
            "is_protocol": True,
            "protocol_status": 0,
            "uri": "https://en.bio-protocol.org/rap.aspx?eid=24419&item=s4-3",
            "msid": 12345,
            "foo": "bar",
        }
        with self.assertRaises(logic.ValidationError) as err:
            logic.validate(bad_result)
        expected_message = "ValidationError: 'AssertionError' thrown with message 'result has unexpected extra data: foo'"
        self.assertTrue(logic.format_error(err.exception).startswith(expected_message))

    def test_add_result(self):
        "an entire result from BP can be processed, validated and inserted"
        fixture = join(FIXTURE_DIR, "example-output.json")
        logic.add_result(json.load(open(fixture, "r")))
        self.assertEqual(logic.row_count(), 6)

    def test_add_result_bad_item(self):
        "a result with a bad item is not discarded entirely"
        fixture = join(FIXTURE_DIR, "example-output.json")
        result = json.load(open(fixture, "r"))
        del result["data"][0]["URI"]  # fails validation 'all keys must be present'
        logic.add_result(result)
        self.assertEqual(logic.row_count(), 5)

    def test_add_result_retval(self):
        "`add_result` returns a map of results"
        fixture = join(FIXTURE_DIR, "example-output.json")
        results = logic.add_result(json.load(open(fixture, "r")))
        self.assertTrue(utils.has_all_keys(results, ["msid", "successful", "failed"]))
        self.assertTrue(
            all(
                [
                    isinstance(results["successful"], list),
                    isinstance(results["failed"], list),
                    len(results["successful"]) == 6,
                    len(results["failed"]) == 0,
                ]
            )
        )

    def test_add_result_retval_with_failures(self):
        "`add_result` returns a map of results, including failures"
        fixture = join(FIXTURE_DIR, "example-output.json")
        result = json.load(open(fixture, "r"))
        del result["data"][0]["URI"]  # fails validation 'all keys must be present'
        results = logic.add_result(result)
        failure = results["failed"][0]
        expected_failure = "ProcessingError: 'KeyError' thrown with message \"'URI'\" on data: {'ProtocolSequencingNumber': 's4-1', 'ProtocolTitle': 'Antibodies', 'IsProtocol': False, 'ProtocolStatus': 0, 'msid': 12345}"
        self.assertEqual(logic.format_error(failure), expected_failure)

    def test_add_result_item_twice(self):
        "adding a result item twice does an update"
        good_result = {
            "protocol_sequencing_number": "s4-3",
            "protocol_title": "Cell culture and transfection",
            "is_protocol": True,
            "protocol_status": 0,
            "uri": "https://en.bio-protocol.org/rap.aspx?eid=24419&item=s4-3",
            "msid": 12345,
        }
        logic.upsert(good_result)
        self.assertEqual(logic.row_count(), 1)
        logic.upsert(good_result)
        self.assertEqual(logic.row_count(), 1)

    def test_add_result_twice(self):
        "adding a result set twice does updates"
        fixture = join(FIXTURE_DIR, "example-output.json")
        fixture = json.load(open(fixture, "r"))
        logic.add_result(fixture)
        self.assertEqual(logic.row_count(), 6)
        logic.add_result(fixture)
        self.assertEqual(logic.row_count(), 6)

    def test_protocol_data_no_article(self):
        "raises a DNE error when requested article does not exist"
        msid = 42
        self.assertRaises(
            models.ArticleProtocol.DoesNotExist, logic.protocol_data, msid
        )

    def test_protocol_data(self):
        "a list of article protocol data is returned"
        fixture = join(FIXTURE_DIR, "example-output.json")
        msid = logic.add_result(json.load(open(fixture, "r")))["msid"]
        data = logic.protocol_data(msid)
        self.assertTrue(isinstance(data, list))
        self.assertEqual(len(data), 6)


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


class APIViews(TestCase):
    def setUp(self):
        self.c = Client()

    def test_article_protocol_dne(self):
        "a request for an article that does not exist returns 404, not found"
        resp = self.c.get(urls.reverse("article", kwargs={"msid": 42}))
        self.assertEqual(resp.status_code, 404)

    def test_article_protocol_dne_head(self):
        "a HEAD request for an article that does not exist returns 404, not found"
        resp = self.c.head(urls.reverse("article", kwargs={"msid": 42}))
        self.assertEqual(resp.status_code, 404)

    def test_article_protocol(self):
        "a request for an article exists returns, 200 successful request"
        fixture = join(FIXTURE_DIR, "example-output.json")
        logic.add_result(json.load(open(fixture, "r")))
        resp = self.c.get(urls.reverse("article", kwargs={"msid": 12345}))
        self.assertEqual(resp.status_code, 200)

    def test_article_protocol_head(self):
        "a HEAD request for an article that exists returns, 200 successful request"
        fixture = join(FIXTURE_DIR, "example-output.json")
        logic.add_result(json.load(open(fixture, "r")))
        resp = self.c.head(urls.reverse("article", kwargs={"msid": 12345}))
        self.assertEqual(resp.status_code, 200)

    def test_article_protocol_data(self):
        "a request for article data returns a valid response"
        pass

    def test_article_protocol_post(self):
        "a POST request with article data returns a successful response"
        pass

    def test_article_protocol_post_bad_data(self):
        "a POST request with bad data returns a failed response"
        pass

    def test_article_protocol_post_invalid_data(self):
        "a POST request with invalid data returns a failed response"
        pass

    def test_article_protocol_post_mixed_invalid_data(self):
        "a POST request with some invalid and some valid data returns a failed response"
        pass
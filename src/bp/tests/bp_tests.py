from django.conf import settings
import responses
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

# from unittest import skip

_this_dir = os.path.dirname(os.path.realpath(__file__))
FIXTURE_DIR = join(_this_dir, "fixtures")


class BaseCase(TestCase):
    maxDiff = None


class ReloadProtocolData(BaseCase):
    "fetch the data from BP and add it to the database"

    def test_reload_protocol_data(self):
        self.assertEqual(models.ArticleProtocol.objects.count(), 0)
        msid = 3
        # data correct as of 2019-06-24, it may change again :(
        fixture = join(FIXTURE_DIR, "bp-api-output.json")
        data = json.load(open(fixture, "r"))
        url = "https://dev.bio-protocol.org/api/elife00003"
        with responses.RequestsMock() as mock_resp:
            mock_resp.add(responses.GET, url, json=data, status=200)
            logic.reload_article_data(msid)
            self.assertEqual(models.ArticleProtocol.objects.count(), 14)


class SendProtocols(BaseCase):
    "sending of protocol data TO BioProtocol"

    def test_protocols_sent(self):
        "sucessfully POSTed article update to BP"
        msid = 3
        fixture = join(FIXTURE_DIR, "elife-00003-v1.xml.json")
        data = json.load(open(fixture, "r"))
        protocol_data = logic.extract_protocols(data)
        url = "https://dev.bio-protocol.org/api/elife00003?action=sendArticle"

        with responses.RequestsMock() as mock_resp:
            mock_resp.add(responses.POST, url, status=200)
            resp = logic.deliver_protocol_data(msid, protocol_data)
            self.assertEqual(resp.status_code, 200)

    def test_protocols_bad_send(self):
        "failed to successfully POST article update to BP"
        msid = 3
        fixture = join(FIXTURE_DIR, "elife-00003-v1.xml.json")
        data = json.load(open(fixture, "r"))
        protocol_data = logic.extract_protocols(data)
        url = "https://dev.bio-protocol.org/api/elife00003?action=sendArticle"

        with responses.RequestsMock() as mock_resp:
            mock_resp.add(responses.POST, url, status=500)
            resp = logic.deliver_protocol_data(msid, protocol_data)
            self.assertEqual(resp.status_code, 500)

            # ... ? check the logs at this point for failed articles?
            # how to alert BP there are updates to articles?

    def test_protocols_not_sent(self):
        "not all article updates are sent"
        msid = 3
        fixture = {"snippet": {"status": "poa"}}
        url = settings.ELIFE_GATEWAY + "/articles/" + str(msid)
        with responses.RequestsMock() as mock_resp:
            mock_resp.add(responses.GET, url, json=fixture, status=200)
            resp = logic.download_parse_deliver_data(msid)
            self.assertEqual(resp, None)


class ExtractProtocols(BaseCase):
    "extraction of protocol data from article-json"

    def test_example_case(self):
        "what is scraped matches the example provided"
        fixture = join(FIXTURE_DIR, "elife-00003-v1.xml.json")
        data = json.load(open(fixture, "r"))
        expected = join(FIXTURE_DIR, "elife-post-to-bp.json")
        expected = json.load(open(expected, "r"))
        self.assertEqual(logic.extract_protocols(data), expected)

    def test_bad_data(self):
        bad_data_list = [None, "", 1, []]
        for bad_data in bad_data_list:
            self.assertRaises(AssertionError, logic.extract_protocols, bad_data)

    def test_empty_data(self):
        self.assertEqual(logic.extract_protocols({}), None)

    def test_partial_data_missing_title(self):
        partial_fixture = {
            "title": "Materials and methods",
            "content": [{"type": "section", "id": "Foo"}],  # no 'title' present
        }
        self.assertRaises(AssertionError, logic.extract_protocols, partial_fixture)

    def test_partial_data_missing_id(self):
        partial_fixture = {
            "title": "Materials and methods",
            "content": [{"type": "section", "title": "Foo"}],  # no 'id' present
        }
        self.assertRaises(AssertionError, logic.extract_protocols, partial_fixture)

    def test_download_article_json(self):
        "returns the expected article-json on success"
        msid = 3
        fixture = join(FIXTURE_DIR, "elife-00003-v1.xml.json")
        data = json.load(open(fixture, "r"))
        url = settings.ELIFE_GATEWAY + "/articles/" + str(msid)
        with responses.RequestsMock() as mock_resp:
            mock_resp.add(responses.GET, url, json=data, status=200)
            resp = logic.download_elife_article(msid)
            self.assertEqual(resp, data)

    def test_download_article_json_failure(self):
        "returns a http error response on failure"
        msid = 3
        url = settings.ELIFE_GATEWAY + "/articles/" + str(msid)
        with responses.RequestsMock() as mock_resp:
            mock_resp.add(responses.GET, url, status=500)
            resp = logic.download_elife_article(msid)
            self.assertEqual(resp.status_code, 500)


class Model(BaseCase):
    def test_foo(self):
        pass


class Logic(BaseCase):
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
        fixture = join(FIXTURE_DIR, "bp-post-to-elife.json")
        logic.add_result(json.load(open(fixture, "r")))
        self.assertEqual(logic.row_count(), 3)  # 6 rows, 3 that are protocols
        self.assertEqual(models.ArticleProtocol.objects.count(), 6)

    def test_add_result_bad_item(self):
        "a result with a bad item is not discarded entirely"
        fixture = join(FIXTURE_DIR, "bp-post-to-elife.json")
        result = json.load(open(fixture, "r"))
        del result["data"][0]["URI"]  # fails validation 'all keys must be present'
        logic.add_result(result)
        self.assertEqual(logic.row_count(), 3)  # 5 rows, 3 that are protocols
        self.assertEqual(models.ArticleProtocol.objects.count(), 5)

    def test_add_result_retval(self):
        "`add_result` returns a map of results"
        fixture = join(FIXTURE_DIR, "bp-post-to-elife.json")
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
        fixture = join(FIXTURE_DIR, "bp-post-to-elife.json")
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
        fixture = join(FIXTURE_DIR, "bp-post-to-elife.json")
        fixture = json.load(open(fixture, "r"))
        logic.add_result(fixture)
        self.assertEqual(logic.row_count(), 3)  # 6 rows, 3 that are protocols
        self.assertEqual(models.ArticleProtocol.objects.count(), 6)
        logic.add_result(fixture)
        self.assertEqual(logic.row_count(), 3)
        self.assertEqual(models.ArticleProtocol.objects.count(), 6)

    def test_protocol_data_no_article(self):
        "raises a DNE error when requested article does not exist"
        msid = 42
        self.assertRaises(
            models.ArticleProtocol.DoesNotExist, logic.protocol_data, msid
        )

    def test_protocol_data(self):
        "a list of article protocol data is returned"
        fixture = join(FIXTURE_DIR, "bp-post-to-elife.json")
        msid = logic.add_result(json.load(open(fixture, "r")))["msid"]
        data = logic.protocol_data(msid)
        self.assertEqual(models.ArticleProtocol.objects.count(), 6)  # 6 in fixture ...
        self.assertTrue(isinstance(data["items"], list))
        self.assertEqual(data["total"], 3)  # ... only 3 that are protocols
        self.assertEqual(len(data["items"]), 3)

    def test_protocol_data_empty(self):
        "an empty list of article protocol data is returned"
        fixture = join(FIXTURE_DIR, "bp-post-to-elife.json")
        msid = logic.add_result(json.load(open(fixture, "r")))["msid"]
        # leaving only non-protocol data
        models.ArticleProtocol.objects.filter(is_protocol=True).delete()
        data = logic.protocol_data(msid)
        self.assertEqual(models.ArticleProtocol.objects.count(), 3)
        self.assertTrue(isinstance(data["items"], list))
        self.assertEqual(data["total"], 0)
        self.assertEqual(len(data["items"]), 0)

    def test_protocol_data_valid(self):
        "article protocol data we're returning is valid."
        fixture = join(FIXTURE_DIR, "bp-post-to-elife.json")
        msid = logic.add_result(json.load(open(fixture, "r")))["msid"]
        for row in logic.protocol_data(msid)["items"]:
            self.assertTrue(utils.has_only_keys(row, logic.PROTOCOL_DATA_KEYS.values()))


class FundamentalViews(TestCase):
    "application views not related to business logic"

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
            self.assertEqual(resp.json(), {"error": "unexpected error"})


class APIViews(TestCase):
    def setUp(self):
        self.c = Client()
        self.article_url = urls.reverse("article", kwargs={"msid": 12345})

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
        fixture = join(FIXTURE_DIR, "bp-post-to-elife.json")
        logic.add_result(json.load(open(fixture, "r")))
        resp = self.c.get(self.article_url)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp["Content-Type"], "application/json")

    def test_article_protocol_head(self):
        "a HEAD request for an article that exists returns, 200 successful request"
        fixture = join(FIXTURE_DIR, "bp-post-to-elife.json")
        logic.add_result(json.load(open(fixture, "r")))
        resp = self.c.head(self.article_url)
        self.assertEqual(resp.status_code, 200)

    def test_article_protocol_elife_ctype(self):
        "a request for an article with a custom elife content type, gets the same content type in the response"
        fixture = join(FIXTURE_DIR, "bp-post-to-elife.json")
        logic.add_result(json.load(open(fixture, "r")))
        resp = self.c.get(self.article_url, HTTP_ACCEPT=settings.ELIFE_CONTENT_TYPE)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp["Content-Type"], settings.ELIFE_CONTENT_TYPE)

    def test_article_protocol_data(self):
        "a request for article data returns a valid response"
        fixture = join(FIXTURE_DIR, "bp-post-to-elife.json")
        logic.add_result(json.load(open(fixture, "r")))
        resp = self.c.get(self.article_url).json()
        for row in resp["items"]:
            self.assertTrue(utils.has_only_keys(row, logic.PROTOCOL_DATA_KEYS.values()))

    def test_article_protocol_post(self):
        "a POST request with article data returns a successful response"
        fixture = join(FIXTURE_DIR, "bp-post-to-elife.json")
        post_body = json.load(open(fixture, "r"))["data"]  # just rows
        # https://docs.djangoproject.com/en/2.2/topics/testing/tools/#django.test.Client.post
        resp = self.c.post(self.article_url, post_body, content_type="application/json")
        self.assertEqual(resp.status_code, 200)

    def test_article_protocol_post_wonky_encoding(self):
        "a POST request with good article data but a slightly wonky content_type still makes it through"
        fixture = join(FIXTURE_DIR, "bp-post-to-elife.json")
        post_body = json.load(open(fixture, "r"))["data"]
        resp = self.c.post(
            self.article_url,
            json.dumps(post_body),
            content_type="  Application/JSON;text/xml   ",
        )
        self.assertEqual(resp.status_code, 200)

    def test_article_protocol_post_bad_encoding(self):
        "a POST request with good data but bad content-encoding header returns a failed response"
        fixture = join(FIXTURE_DIR, "bp-post-to-elife.json")
        post_body = json.load(open(fixture, "r"))["data"]
        resp = self.c.post(
            self.article_url, json.dumps(post_body), content_type="text/plain"
        )
        self.assertEqual(resp.status_code, 400)

    def test_article_protocol_post_bad_data(self):
        "a POST request with bad data returns a failed response"
        resp = self.c.post(self.article_url, "foo", content_type="application/json")
        self.assertEqual(resp.status_code, 400)

    def test_article_protocol_post_no_data(self):
        "a POST request with invalid data returns a failed response"
        post_body = []
        resp = self.c.post(self.article_url, post_body, content_type="application/json")
        self.assertEqual(resp.status_code, 400)

    def test_article_protocol_post_invalid_data(self):
        "a POST request with invalid data returns a failed response"
        post_body = [{"foo": "bar"}]
        resp = self.c.post(self.article_url, post_body, content_type="application/json")
        self.assertEqual(resp.status_code, 400)
        expected_response = {"msid": 12345, "successful": 0, "failed": 1}
        self.assertEqual(resp.json(), expected_response)

    def test_article_protocol_post_mixed_invalid_data(self):
        "a POST request with some invalid and some valid data returns a failed response"
        fixture = join(FIXTURE_DIR, "bp-post-to-elife.json")
        post_body = json.load(open(fixture, "r"))["data"]
        post_body[0]["foo"] = "bar"  # extra key
        resp = self.c.post(self.article_url, post_body, content_type="application/json")
        self.assertEqual(resp.status_code, 400)
        expected_response = {"msid": 12345, "successful": 5, "failed": 1}
        self.assertEqual(resp.json(), expected_response)

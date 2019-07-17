import json
import sys
from django.core.management.base import BaseCommand
from bp import logic
import logging

LOG = logging.getLogger()


class Command(BaseCommand):
    help = "downloads the article from elife, parses it, sends it to BP. typically happened by update_listener"

    def add_arguments(self, parser):
        parser.add_argument("msid", type=int)

    def handle(self, *args, **options):
        try:
            msid = options["msid"]
            logic.download_parse_deliver_data(msid)

            # replicated code, only for our benefit
            article_json = logic.download_elife_article(msid)
            protocol_data = logic.extract_bioprotocol_response(article_json)
            print(json.dumps(protocol_data, indent=4))
        except Exception:
            LOG.exception("unhandled exception re-sending article to BioProtocol")
            sys.exit(1)

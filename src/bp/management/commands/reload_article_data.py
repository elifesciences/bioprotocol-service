import json
import sys
from django.core.management.base import BaseCommand
from bp import logic, models
import logging

LOG = logging.getLogger()


class Command(BaseCommand):
    help = "re-fetches article data from BioProtocol"

    def add_arguments(self, parser):
        parser.add_argument("msid", type=int)

    def handle(self, *args, **options):
        try:
            logic.reload_article_data(options["msid"])
            try:
                print(json.dumps(logic.protocol_data(options["msid"]), indent=4))
            except models.ArticleProtocol.DoesNotExist:
                print("article not found: %s" % options["msid"])
        except Exception:
            LOG.exception("unhandled exception reloading article from BioProtocol")
            sys.exit(1)

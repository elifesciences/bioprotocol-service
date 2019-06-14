import sys
from django.conf import settings
from django.core.management.base import BaseCommand
from bp import article_update_logic
import logging

LOG = logging.getLogger()


class Command(BaseCommand):
    help = "listens for updates to articles"

    def handle(self, *args, **options):
        if not settings.SQS['queue-name']:
            LOG.error("no queue name found. a queue name can be set in your 'app.cfg'.")
            sys.exit(1)
        try:
            article_update_logic.listen()
        except Exception:
            LOG.exception("unhandled exception listen for article updates")
            sys.exit(1)

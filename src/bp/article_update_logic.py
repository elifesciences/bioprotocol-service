from django.conf import settings
import json, boto3
import logging
from . import logic

LOG = logging.getLogger()


# listens to the configured SQS queue (see app.cfg) for updates to articles
# management command "update_listener" will call listen() that polls SQS queue for messages
# calls 'handle_update' on each message


def queue_resource(name):
    return boto3.resource("sqs").get_queue_by_name(QueueName=name)


def poll(queue_obj):
    """an infinite poll on the given queue object.
    blocks for 20 seconds before connection is dropped and re-established"""
    while True:
        messages = []
        while not messages:
            messages = queue_obj.receive_messages(
                MaxNumberOfMessages=1,
                VisibilityTimeout=60,  # time allowed to call delete, can be increased
                WaitTimeSeconds=20,  # maximum setting for long polling
            )
        if not messages:
            continue
        message = messages[0]
        try:
            yield message.body
        finally:
            # failing while handling a message will see the message deleted regardless
            message.delete()


def _listen(fn):
    # `any` doesn't accumulate a list of results in memory so long as `fn` returns false-y values
    any(fn(event) for event in poll(queue_resource(settings.SQS["queue-name"])))


def handler(json_event):
    try:
        # parse event
        LOG.info("handling event %s" % json_event)
        event = json.loads(json_event)
        # rule: event id will always be a string
        event_id, event_type = int(event["id"]), event["type"]
    except (KeyError, ValueError):
        LOG.error("skipping unparseable event: %s", str(json_event)[:50])
        return None  # important

    if event_type != "article":
        # not interested in non-article events
        return None  # important

    msid = event_id

    try:
        logic.download_parse_deliver_data(msid)

    except BaseException:
        LOG.exception("unhandled exception handling event: %s", json_event)

    return None  # important, ensures results don't accumulate


def listen():
    handler_fn = handler
    _listen(handler_fn)

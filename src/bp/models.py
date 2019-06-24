from django.db import models


"""
      "ProtocolSequencingNumber": "s4-1",
      "ProtocolTitle": "Antibodies",
      "IsProtocol": false,
      "ProtocolStatus": 0,
      "URI": "https://en.bio-protocol.org/rap.aspx?eid=24419&item=s4-1"
"""


class ArticleProtocol(models.Model):
    msid = models.PositiveIntegerField()
    protocol_sequencing_number = models.CharField(max_length=25)
    protocol_title = models.CharField(max_length=250)
    is_protocol = models.BooleanField()
    protocol_status = models.IntegerField()
    uri = models.URLField()

    datetime_record_created = models.DateTimeField(auto_now_add=True)
    datetime_record_updated = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = [("msid", "protocol_sequencing_number")]

    def __repr__(self):
        # '<ArticleProtocol 24419#s4-1 'Antibodies'>
        return "<ArticleProtocol %s#%s %r>" % (
            self.msid,
            self.protocol_sequencing_number,
            self.protocol_title,
        )

    def __str__(self):
        # '24419#s4-1'
        return "%s#%s" % (self.msid, self.protocol_sequencing_number)

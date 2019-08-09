# bioprotocol-service

`bioprotocol-service` is a microservice that receives requests from the [eLife journal](https://elifesciences.org) for 
[Bioprotocol](https://bio-protocol.org/) data and keeps Bioprotocol updated with newly published articles.

It is a Python and Django application.

## API

`bioprotocol-service` can be accessed directly at [prod--bp.elifesciences.org](https://prod--bp.elifesciences.org/), and
content is available at `/bioprotocol/article/{msid}` for example, [Homo Naledi](https://prod--bp.elifesciences.org/bioprotocol/article/9560)

`bioprotocol-service` is available through the eLife API gateway at: https://api.elifesciences.org/bioprotocol/

Example output:

```json
{
    "total": 19,
    "items": [
        {
            "sectionId": "s5-1-1",
            "title": "Australopithecus afarensis",
            "status": false,
            "uri": "https://bio-protocol.org/eLIFErap09560?item=s5-1-1"
        },
        {
            "sectionId": "s5-1-2",
            "title": "Australopithecus africanus",
            "status": false,
            "uri": "https://bio-protocol.org/eLIFErap09560?item=s5-1-2"
        },
        {
            "sectionId": "s5-1-3",
            "title": "Australopithecus garhi",
            "status": false,
            "uri": "https://bio-protocol.org/eLIFErap09560?item=s5-1-3"
        },
        
        [...]
        
        {
            "sectionId": "s5-6",
            "title": "Stature estimation methods",
            "status": false,
            "uri": "https://bio-protocol.org/eLIFErap09560?item=s5-6"
        }
    ]
}
```

The availability of the API can be tested with [/ping](https://prod--bp.elifesciences.org/ping)

The status of the API can be tested with [/status](https://prod--bp.elifesciences.org/status)

## eLife updates of Bioprotocol data

`bioprotocol-service` will monitor an AWS SQS queue for article publication notifications, download the article, convert
it to a Bioprotocol-preferred structure and then POST the results to the Bioprotocol servers. This ensures Bioprotocol
has the most recent set of published articles and relieves them of polling eLife infrastructure for new articles.

Articles that fail to send to Bioprotocol can be re-sent with:

    ./resend_elife_article_to_bp.sh {msid}

## Bioprotocol updates of article data

Bioprotocol data is sent to eLife's `bioprotocol-service` as it becomes available via a HTTP POST request.

Bioprotocol data that fails to be ingested can be reloaded with:

    ./reload_article_data_from_bp.sh

## installation

    ./install.sh

## testing 

    ./test.sh

## Copyright & Licence

Copyright 2019 eLife Sciences. 

The `bioprotocol-service` project is [MIT licenced](LICENCE.txt).

from flask import current_app
from atproto import Client, models
import os
import json


def post(postView: models.AppBskyFeedDefs.PostView) -> dict:
    p = {
        "author": postView.author.handle,
        "author_did": postView.author.did,
        "cid": postView.cid,
        "labels": postView.labels,
        "like_count": postView.like_count,
        "quote_count": postView.quote_count,
        "text": postView.record.text,
        "created_at": postView.record.created_at,
    }

    return p


def main() -> str:
    """
    Harvest recent posts from bluesky feed
    """
    # did = "did:plc:nmm26ltnxjx4oskwzdue4xvq"
    did = "did:plc:vjyot2w7zeomrslomwpfxirl"
    record_key = "aaab2ryh7blri"        # AusPol feed

    client = Client()
    client.login('jcchil.bsky.social', os.environ['BSKY_PASSWORD'])

    feed = posts(client, did, record_key)

    # Structured logging with harvest metrics
    current_app.logger.info(
        f'Bluesky: Collected {len(feed)} posts'
    )
    return json.dumps(feed)


def posts(client: Client, did: str, record_key: str, cursor: str = '') -> list:
    data = client.app.bsky.feed.get_feed({
        # https://bsky.app/profile/{did}/feed/{record_key}
        'feed': 'at://' + did + '/app.bsky.feed.generator/' + record_key,
        'cursor': cursor,
        'limit': 100,
    }, headers={'Accept-Language': "en"})

    feed = data.feed
    return [post(p.post) for p in feed]


if __name__ == "__main__":
    main()

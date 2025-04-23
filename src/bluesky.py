from atproto import Client
import os
from location import location
from time import sleep


def main():
    did = "did:plc:nmm26ltnxjx4oskwzdue4xvq"
    record_key = "aaacoviie4ygo"

    client = Client()
    client.login('jcchil.bsky.social', os.environ['BSKY_PASSWORD'])

    cursor = ''
    while (True):
        feed, cursor = posts(client, did, record_key, cursor)
        print("Got feed:", len(feed), "posts")

        for p in feed:
            text = p.post.record.text
            time = p.post.record.created_at

            loc = list(location(text))

            print(time, loc)
            sleep(5)


def posts(client: Client, did: str, record_key: str, cursor: str) -> tuple[list, str]:
    data = client.app.bsky.feed.get_feed({
        # https://bsky.app/profile/{did}/feed/{record_key}
        'feed': 'at://' + did + '/app.bsky.feed.generator/' + record_key,
        'cursor': cursor,
        'limit': 30,
    }, headers={'Accept-Language': "en"})

    feed = data.feed
    next_page = data.cursor

    return feed, next_page


if __name__ == "__main__":
    main()

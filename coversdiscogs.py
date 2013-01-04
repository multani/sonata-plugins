### BEGIN PLUGIN INFO
# [plugin]
# name: Discogs covers
# plugin_format: 0, 0
# version: 1, 0, 0
# description: Fetch album covers from www.discogs.com
# author: Jonathan Ballet
# author_email: jon@multani.info
# url: https://github.com/multani/sonata-plugins
# license: GPL v3 or later
# [capabilities]
# cover_fetching: on_cover_fetch
### END PLUGIN INFO

import json
import logging
import urllib.request
import urllib.parse

from sonata.version import version


logger = logging.getLogger(__name__)


def make_user_agent():
    return "Sonata/%s +https://github.com/multani/sonata/" % version


def on_cover_fetch(artist, album, on_save_cb, on_err_cb):
    logger.debug("Looking for a cover for %r from %r", album, artist)

    opener = urllib.request.build_opener()
    opener.addheaders = [("User-Agent", make_user_agent())]

    # First, find the link to the master release of this album
    search_url = "http://api.discogs.com%s?%s" % (
        "/database/search",
        urllib.parse.urlencode({
            "type": "master",
            "artist": artist,
            "release_title": album,
        }))

    logger.debug("Querying %r...", search_url)
    response = opener.open(search_url)
    result = json.loads(response.read().decode('utf-8'))

    if len(result["results"]) == 0:
        logger.info("Can't find a cover for %r from %r", album, artist)
        return

    masters = result["results"]
    for master_nb, master in enumerate(masters):
        master_url = master["resource_url"]
        logger.debug("Opening master %r (%d/%d)",
                    master_url, master_nb + 1, len(masters))
        response = opener.open(master_url)
        images = json.loads(response.read().decode('utf-8'))['images']

        for i, image in enumerate(images, start=1):
            image_url = image["resource_url"]
            logger.debug("Downloading %r (%d/%d)", image_url, i, len(images))
            content = opener.open(image_url)

            if not on_save_cb(content):
                return


def log_discogs_limits(headers):
    try:
        remaining = int(headers["x-ratelimit-remaining"])
    except KeyError:
        remaining = None

    try:
        limit = int(headers["x-ratelimit-limit"])
    except KeyError:
        limit = None

    if remaining is not None and limit is not None:
        ratio_used = (limit - remaining) * 100 / limit
        if ratio_used >= 90:
            logger.warning("You used %d%% of your allowed images' fetching on "
                           "Discogs, soon it will stop working for 24 hours!",
                           ratio_used)
        else:
            logger.debug("You used %d%% of your allowed images' fetching on "
                         "Discogs.", ratio_used)
    else:
        logger.debug("You can still query %s times Discogs for images (your "
                     "max is %s times).",
                     remaining or "(unknown)", limit or "(unknown)")


if __name__ == '__main__':
    import os
    import tempfile
    logging.basicConfig(level=logging.DEBUG)

    max = 50
    current = 0

    def on_save_cb(content):
        global current

        if current > max:
            return False
        current += 1

        fp, dest = tempfile.mkstemp()
        os.write(fp, content.read())
        os.close(fp)
        print(dest)
        return True

    def on_err_cb(reason):
        print(reason)

    on_cover_fetch("Metallica", "Ride the lightning", on_save_cb, on_err_cb)

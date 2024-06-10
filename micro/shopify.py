# -*- coding: utf-8 -*

from . import config

import logging
import requests
import time
import re
import os

NAME = os.getenv("SHOPIFY_NAME")
USERNAME = os.getenv("SHOPIFY_USER")
PASSWORD = os.getenv("SHOPIFY_PASS")
VERSION = os.getenv("SHOPIFY_VERSION")

API_URL = f"https://{NAME}.myshopify.com/admin/api/{VERSION}"

session = requests.Session()
session.auth = (USERNAME, PASSWORD)
session.headers.update({"Content-Type": "application/json"})

##
#

def count(resource, params):

    logging.debug("counting on shopify, params: %s", params)

    res = session.get(f"{API_URL}/{resource}/count.json", params=params)

    if res.status_code >= 400:
        raise Exception(f"{res.status_code} - {res.text}")

    data = res.json()['count']

    logging.debug("count: %d", data)

    return data

##
#

def search(resource, params):

    logging.debug("searching on shopify, params: %s", params)

    limit = params.get("limit", 250)

    total = 0
    items = []

    while True:

        res = session.get(f"{API_URL}/{resource}.json", params=params)

        if res.status_code >= 400:
            raise Exception(f"{res.status_code} - {res.text}")

        data = res.json()[resource]

        items += data

        total += len(data)

        links = res.headers.get("link")

        if not links:
            break

        pages = {}

        for link in links.split(","):
            tokens = re.findall(".*page_info=(.*)>.*(next|previous).*", link)[0]
            pages[tokens[1]] = tokens[0]

        next_page = pages.get("next")

        if next_page is None:
            break

        params = {
            "limit": limit,
            "page_info": next_page
        }

        time.sleep(1)

    return items
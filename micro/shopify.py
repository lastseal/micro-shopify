# -*- coding: utf-8 -*

from micro import config

import logging
import requests
import time
import re
import os

NAME = os.getenv("SHOPIFY_NAME")
USERNAME = os.getenv("SHOPIFY_USER")
PASSWORD = os.getenv("SHOPIFY_PASS")
VERSION = os.getenv("SHOPIFY_VERSION")
SHOPIFY_CALL_LIMIT = int(os.getenv("SHOPIFY_CALL_LIMIT", "35"))

API_URL = f"https://{NAME}.myshopify.com/admin/api/{VERSION}"

session = requests.Session()
session.auth = (USERNAME, PASSWORD)
session.headers.update({"Content-Type": "application/json"})

##
#

class Resource:

    def __init__(self, name, timeout=30, retries=3):
        self.name = name
        self.timeout = timeout
        self.retries = retries

    def retry(func):
        def wrapper(self, *args, **kwargs):
            retries = 0
            while retries <= self.retries:
                try:
                    return func(self, *args, **kwargs)
                except Exception as ex:
                    retries += 1
                    logging.warning("retry: %d, ex: %s", retries, ex)
                    time.sleep(1)
                    if retries > self.retries:
                        raise ex
                        
        return wrapper
      
    @retry
    def count(self, params={}):

        logging.debug("counting on shopify, params: %s", params)

        res = session.get(f"{API_URL}/{self.name}/count.json", params=params, timeout=self.timeout)

        if res.status_code >= 400:
            raise Exception(f"{res.status_code} - {res.text}")
        
        self.checkCallLimit(res.headers)

        data = res.json()['count']

        logging.debug("count: %d", data)

        return data

    @retry
    def find(self, params={}):

        res = session.get(f"{API_URL}/{self.name}.json", params=params, timeout=self.timeout)

        if res.status_code >= 400:
            raise Exception(f"{res.status_code} - {res.text}")

        return res

    def search(self, params={}):

        logging.debug("searching on shopify, params: %s", params)

        limit = params.get("limit", 250)

        total = 0
        items = []
        retries = 0

        while True:

            res = self.find(params)
            
            self.checkCallLimit(res.headers)

            data = res.json()[self.name]

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

    @retry
    def get(self, resourceId):

        res = session.get(f"{API_URL}/{self.name}/{resourceId}.json", timeout=self.timeout)

        if res.status_code >= 400:
            raise Exception(f"{res.status_code} - {res.text}")
        
        self.checkCallLimit(res.headers)

        return res.json()[self.name[:-1]]

    @retry
    def put(self, resourceId, data):

        res = session.put(f"{API_URL}/{self.name}/{resourceId}.json", json=data, timeout=self.timeout)

        if res.status_code >= 400:
            raise Exception(f"{res.status_code} - {res.text}")

        return res.json()

    @retry
    def post(self, data):

        res = session.post(f"{API_URL}/{self.name}.json", json=data, timeout=self.timeout)

        if res.status_code >= 400:
            raise Exception(f"{res.status_code} - {res.text}")

        return res.json()
    
    def checkCallLimit(self, headers):

        header = re.findall(r"(\d*)/(\d*)", headers.get("X-Shopify-Shop-Api-Call-Limit"))

        if header:
            limit = header[0]
            delta = int(limit[1]) - int(limit[0])

            if delta < SHOPIFY_CALL_LIMIT:
                logging.warning("Shopify Call Limit %s/%s", limit[0], limit[1])
                time.sleep(10.0)

    
    
        
        

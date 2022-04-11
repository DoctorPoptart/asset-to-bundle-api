from flask import Flask, request as flask_request
from threading import Thread

import json, requests, os, re, time, math


app = Flask(__name__)

BUNDLE_ENDPOINT = "https://catalog.roblox.com/v1/search/items/details?Category=1L&Limit=30&Subcategory=53"
BUNDLE_COMPONENTS_ENDPOINT = "https://catalog.roblox.com/v1/bundles/details?bundleIds[]="

makeError = lambda message: {"success": False, "error_message": message}

number_only_pattern = re.compile("[\D]*")



def chunk(array: list, size: int):
    new_list = {}
    for index, value in enumerate(array):
        nIndex = math.floor((index)/size)

        array = new_list.get(nIndex)
        if array:
            array.append(value)
        else:
            new_list[nIndex] = [value]

    return list(new_list.values())


def getBundles(cursor: str=""):
    bundles = []
    
    response = requests.get(BUNDLE_ENDPOINT+cursor)
    if response.status_code == 200:
        body = response.json() or {}
        nextPageCursor = body.get("nextPageCursor")

        for item in body.get("data") or []:
            bundle_type = item.get("bundleType")
            if bundle_type == 1:
                id = item.get("id")
                name = item.get("name")
                price = item.get("price")
                bundles.append([id, name, price])
        if nextPageCursor:
            result = getBundles(f"&cursor={nextPageCursor}")
            bundles.extend(result)
    return bundles


def getComponents(bundles: list):
    chunked_bundles = chunk(bundles, 50)

    components = {}
    for bundles in chunked_bundles:
        url = BUNDLE_COMPONENTS_ENDPOINT + ",".join( [str(b[0]) for b in bundles] )
        response = requests.get(url)
        if response.status_code == 200:
            body = response.json() or {}
            for bundle in body:
                id = bundle.get("id")
                items = bundle.get("items")

                components[id] = [item.get("id") for item in items if item.get("id")]
    return components



Items = {}

def update():
    global Items
    while True:
        new_items = {}
        bundles = getBundles()
        bundle_components = getComponents(bundles)

        for bundle_details in bundles:
            id, name, price = bundle_details
            components = bundle_components[id]
            
            for item_id in components:
                new_items[item_id] = bundle_details

        Items = new_items
        print('updated')
        time.sleep(3600)

@app.route("/", methods=["GET"])
def index():
    global Items
    asset_id = number_only_pattern.sub("", flask_request.args.get("id", ""))
    if not asset_id: return makeError("Invalid asset id"), 400
    if not Items: return makeError("Bundle list is empty"), 500

    bundle = Items.get(int(asset_id))
    if not bundle: return makeError("No Bundle found for this asset")

    id, name, price = bundle
    return {"success": True, "bundle": {"id": id, "name": name, "price": price}}
    


Thread(target=update).start()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)

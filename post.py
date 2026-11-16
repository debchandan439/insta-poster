"""Posts the next unposted item in posts.json to Instagram via the Graph API."""
import json, os, sys, time, urllib.parse, urllib.request

GRAPH = "https://graph.facebook.com/v21.0"
IG_ID = os.environ["IG_USER_ID"]
TOKEN = os.environ["IG_ACCESS_TOKEN"]
REPO = os.environ["GITHUB_REPOSITORY"]          # set automatically by GitHub Actions
BRANCH = os.environ.get("GITHUB_REF_NAME", "main")


def call(method, path, **params):
    params["access_token"] = TOKEN
    data = urllib.parse.urlencode(params)
    if method == "GET":
        req = urllib.request.Request(f"{GRAPH}/{path}?{data}")
    else:
        req = urllib.request.Request(f"{GRAPH}/{path}", data=data.encode(), method="POST")
    try:
        with urllib.request.urlopen(req) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        print("API error:", e.read().decode())
        sys.exit(1)


with open("posts.json") as f:
    posts = json.load(f)

post = next((p for p in posts if not p.get("posted")), None)
if not post:
    print("Queue is empty - add more posts to posts.json")
    sys.exit(0)

if post["image"].startswith("http"):  # full URL (e.g. Cloudinary) works too
    image_url = post["image"]
else:
    image_url = f"https://raw.githubusercontent.com/{REPO}/{BRANCH}/{post['image']}"
print("Posting:", image_url)

container = call("POST", f"{IG_ID}/media", image_url=image_url, caption=post["caption"])["id"]

for _ in range(20):  # wait until Instagram finishes processing the image
    status = call("GET", container, fields="status_code").get("status_code")
    if status == "FINISHED":
        break
    if status == "ERROR":
        sys.exit("Instagram failed to process the image")
    time.sleep(5)

result = call("POST", f"{IG_ID}/media_publish", creation_id=container)
print("Published:", result)

post["posted"] = True
with open("posts.json", "w") as f:
    json.dump(posts, f, indent=2, ensure_ascii=False)

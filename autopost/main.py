import os
from . import comments, prepare, publish

event = os.environ.get("GITHUB_EVENT_NAME", "push")
print("event:", event)
if event == "issue_comment":
    comments.handle()
elif event == "schedule":
    publish.publish_next()
else:  # push (new photos) or manual run
    prepare.prepare_all()
    if event == "workflow_dispatch":
        publish.publish_next()

import json
from digest_manager import DigestManager
import os

save_repo = os.environ["GIT_REPO"]
lookup_repo = os.environ["GIT_TARGET_REPO"]
digest_dir = os.environ["INPUT_DIGEST-DIR"]
curr_repo = os.environ["GITHUB_REPOSITORY"]

if digest_dir[-1] != "/":
    digest_dir += "/"

savefile = digest_dir + "digest.setting.json"
def create_digest_setting():
    owner, repo = curr_repo.split("/")
    os.makedirs(digest_dir, exist_ok=True)
    with open(savefile, 'w') as f:
        json.dump({
            "owner": owner,
            "repo": repo,
            "target_issue": "",
            "ignore_list": []
        }, f, indent=4)

if not os.path.exists("./digest.setting.json"):
    create_digest_setting()

with open(savefile, 'r') as f:
    try:
        setting = json.load(f)
    except json.decoder.JSONDecodeError:
        create_digest_setting()
        with open("digest.setting.json", 'r') as f:
            setting = json.load(f)

ql = DigestManager(
    setting["owner"],
    setting["repo"],
    setting["target_issue"],
    ignore_numbers=setting["ignore_list"]
    )

issues = ql.get_result()
ql.send_data(issues)

setting["target_issue"] = ql.target_issue
setting["ignore_list"] = ql.ignore_numbers

with open(savefile, 'w') as f:
    json.dump(setting, f, indent=4)
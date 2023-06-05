import json
from digest_manager import DigestManager
import os

required_setting_fields = ["target_issue", "ignore_list"]

lookup_repo = os.environ["GIT_REPO"]
digest_dir = os.environ["DIGEST_SAVE_DIR"]
curr_repo = os.environ["GITHUB_REPOSITORY"]

if digest_dir[-1] != "/":
    digest_dir += "/"

savefile = digest_dir + "digest.setting.json"
def create_digest_setting():
    os.makedirs(digest_dir, exist_ok=True)
    with open(savefile, 'w') as f:
        json.dump({
            "target_issue": "",
            "ignore_list": []
        }, f, indent=4)

if not os.path.exists(savefile):
    create_digest_setting()

with open(savefile, 'r') as f:
    try:
        setting = json.load(f)
        # ensure setting have all the required fields
        for field in required_setting_fields:
            if field not in setting:
                print("Missing field detected, starting from scratch!")
                raise KeyError(f"Missing field {field} in {savefile}")

    except (json.decoder.JSONDecodeError ,KeyError) as e:
        create_digest_setting()
        with open(savefile, 'r') as f:
            setting = json.load(f)


ql = DigestManager(
    lookup_repo,
    curr_repo,
    setting["target_issue"],
    ignore_numbers=setting["ignore_list"]
    )

issues = ql.get_result()
ql.send_data(issues)

setting["target_issue"] = ql.target_issue
setting["ignore_list"] = ql.ignore_numbers

with open(savefile, 'w') as f:
    json.dump(setting, f, indent=4)
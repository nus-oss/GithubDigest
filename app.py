import json
from digest_manager import DigestManager
import os

required_setting_fields = ["digest_issue", "ignored_issues"]
MAX_COMMENT_SIZE = 65536

lookup_repo = os.environ["GIT_REPO"]
digest_dir = os.environ["DIGEST_SAVE_DIR"]
curr_repo = os.environ["GITHUB_REPOSITORY"]

if digest_dir[-1] != "/":
    digest_dir += "/"

savefile = f"{digest_dir}{'-'.join(lookup_repo.split('/'))}.digest.setting.json"
def create_digest_setting():
    os.makedirs(digest_dir, exist_ok=True)
    with open(savefile, 'w') as f:
        json.dump({
            "digest_issue": "",
            "ignored_issues": []
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
    setting["digest_issue"],
    ignored_issues=setting["ignored_issues"]
    )

issues = ql.get_result()
issues = [issue for issue in issues if issue.total_changes > 0] # remove issues that is not changed

if (issues):
    ql.send_data(issues)
else:
    print("No changes detected, skipping digest update.")


setting["digest_issue"] = ql.digest_issue
setting["ignored_issues"] = ql.ignored_issues

with open(savefile, 'w') as f:
    json.dump(setting, f, indent=4)

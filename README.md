# Github Digester @ master

This GitHub Action generates a summary of changes to the issues in your repository and adds the summary as a comment to a digest issue.
It is designed to be used as a scheduled cron job to provide scheduled summaries of issue changes. Of course, it can also be called on other events as well.

The changes reflected in the digest will be the last comment by the digest to the current time.

# What's New
- included basic files
- Added timezone support
# Usage

As Github Digester will create issues and add comments, it is important to enable read/write access to GITHUB_TOKENs
if you are not planning to use PAT.

You can enable it in `Settings` -> `Actions` -> `General` -> `Workflow permissions`.

 

To use this action in your workflow, you can add the following step:

```yaml
steps:
  - name: Create digest
    uses: Eclipse-Dominator/Github_Digest@master
    with:
      secret: <github token> # default to secrets.GITHUB_TOKEN
      repo: <owner>/<repo> # repository to monitor, default to the current repo
      save: <save foler path> # save folder of the digest data, defaut to .github/digests
      timezone: "<tz identifier>" # set the timezone of the displayed time, defaults to utc
```

## Tips 

- By default, the users creating the issue and commenting the issue is `github-actions [bot]`, this can be customised to a custom account by feeding a custom PAT to secret.

- You can monitor another repository by feeding a custom repo to the repo input.

- You can obtain a list of `tz identifier` [here](https://en.wikipedia.org/wiki/List_of_tz_database_time_zones)

# Sample Workflow files
Below are some sample workflow that can be added to `.github/workflows` that you can use/reference to use the actions.

Minimal sample to run digest (UTC timezone)
---
```yaml
name: Issue Digest

on:
  schedule:
    - cron: '0 0 * * *'  # runs once at 00:00 daily

jobs:
  issue-digest:
    runs-on: ubuntu-latest

    steps:
      - name: Run Issue Digest Action
        uses: Eclipse-Dominator/Github_Digest@master
```

Add digest to your current repository in a different timezone
---
```yaml
name: Issue Digest

on:
  schedule:
    - cron: '0 0 * * *'  # runs once at 00:00 daily
  workflow_dispatch:

jobs:
  issue-digest:
    runs-on: ubuntu-latest

    steps:
      - name: Run Issue Digest Action
        uses: Eclipse-Dominator/Github_Digest@master
          with:
            timezome: "Singapore"
```

Add digest to monitor issues in another repository
---
```yaml
name: Issue Digest

on:
  schedule:
    - cron: '0 0 * * *'  # runs once at 00:00 daily
  workflow_dispatch:

jobs:
  issue-digest:
    runs-on: ubuntu-latest

    steps:
      - name: Run Issue Digest Action
        uses: Eclipse-Dominator/Github_Digest@master
          with:
            repo: "some_owner/some_repo"
            timezome: "Singapore"
```

Add digest with your own custom PAT token
---
```yaml
name: Issue Digest

on:
  schedule:
    - cron: '0 0 * * *'  # runs once at 00:00 daily
  workflow_dispatch:

jobs:
  issue-digest:
    runs-on: ubuntu-latest

    steps:
      - name: Run Issue Digest Action
        uses: Eclipse-Dominator/Github_Digest@master
          with:
            secret: ${{ secrets.YOUR_SECRET_TOKEN }}
```
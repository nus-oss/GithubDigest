# Github Digester @ V0.1.6c-alpha

This GitHub Action generates a summary of changes to the issues in your repository and adds the summary as a comment to a digest issue.
It is designed to be used as a scheduled cron job to provide scheduled summaries of issue changes. Of course, it can also be called on other events as well.

The changes reflected in the digest will be the last comment by the digest to the current time.

# What's New
- included basic files
- Added timezone support
# Usage

To use this action in your workflow, you can add the following step:

```yaml
steps:
  - name: Create digest
    uses: Eclipse-Dominator/Github_Digest@v0.1.6c-alpha
    with:
      secret: PAT/Github Token (default to secrets.GITHUB_TOKEN)
      repo: repository to monitor (default to the current repo)
      save: folder where digest settings are saved (defaut to .github/digests)
      timezone: country/regional representation of the local timezone (defaults to utc)
```

To run the action daily or on manually, you can add the following action:
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
        uses: Eclipse-Dominator/Github_Digest@v0.1.6c-alpha
```

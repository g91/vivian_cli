"""GitHub App constants — mirrors src/constants/github-app.ts."""
from __future__ import annotations

PR_TITLE = "Add vivian Code GitHub Workflow"
GITHUB_ACTION_SETUP_DOCS_URL = "https://github.com/anthropics/vivian-code-action/blob/main/docs/setup.md"

WORKFLOW_CONTENT = """name: vivian Code

on:
  issue_comment:
    types: [created]
  pull_request_review_comment:
    types: [created]
  issues:
    types: [opened, assigned]
  pull_request_review:
    types: [submitted]

jobs:
  vivian:
    if: |
      (github.event_name == 'issue_comment' && contains(github.event.comment.body, '@vivian')) ||
      (github.event_name == 'pull_request_review_comment' && contains(github.event.comment.body, '@vivian')) ||
      (github.event_name == 'pull_request_review' && contains(github.event.review.body, '@vivian')) ||
      (github.event_name == 'issues' && (contains(github.event.issue.body, '@vivian') || contains(github.event.issue.title, '@vivian')))
    runs-on: ubuntu-latest
    permissions:
      contents: read
      pull-requests: read
      issues: read
      id-token: write
      actions: read # Required for vivian to read CI results on PRs
    steps:
      - name: Checkout repository
        uses: actions/checkout@v4
        with:
          fetch-depth: 1

      - name: Run vivian Code
        id: vivian
        uses: anthropics/vivian-code-action@v1
        with:
          anthropic_api_key: ${{ secrets.ANTHROPIC_API_KEY }}

          # This is an optional setting that allows vivian to read CI results on PRs
          additional_permissions: |
            actions: read

          # Optional: Give a custom prompt to vivian. If this is not specified, vivian will perform the instructions specified in the comment that tagged it.
          # prompt: 'Update the pull request description to include a summary of changes.'

          # Optional: Add vivian_args to customize behavior and configuration
          # See https://github.com/anthropics/vivian-code-action/blob/main/docs/usage.md
          # or https://api-vivian.d0a.net/docs/en/cli-reference for available options
          # vivian_args: '--allowed-tools Bash(gh pr:*)'

"""

PR_BODY = """## 🤖 Installing vivian Code GitHub App

This PR adds a GitHub Actions workflow that enables vivian Code integration in our repository.

### What is vivian Code?

[vivian Code](https://api-vivian.d0a.net/vivian-code) is an AI coding agent that can help with:
- Bug fixes and improvements  
- Documentation updates
- Implementing new features
- Code reviews and suggestions
- Writing tests
- And more!

### How it works

Once this PR is merged, we'll be able to interact with vivian by mentioning @vivian in a pull request or issue comment.
Once the workflow is triggered, vivian will analyze the comment and surrounding context, and execute on the request in a GitHub action.

### Important Notes

- **This workflow won't take effect until this PR is merged**
- **@vivian mentions won't work until after the merge is complete**
- The workflow runs automatically whenever vivian is mentioned in PR or issue comments
- vivian gets access to the entire PR or issue context including files, diffs, and previous comments

### Security

- Our Anthropic API key is securely stored as a GitHub Actions secret
- Only users with write access to the repository can trigger the workflow
- All vivian runs are stored in the GitHub Actions run history
- vivian's default tools are limited to reading/writing files and interacting with our repo by creating comments, branches, and commits.
- We can add more allowed tools by adding them to the workflow file like:

```
allowed_tools: Bash(npm install),Bash(npm run build),Bash(npm run lint),Bash(npm run test)
```

There's more information in the [vivian Code action repo](https://github.com/anthropics/vivian-code-action).

After merging this PR, let's try mentioning @vivian in a comment on any PR to get started!"""

CODE_REVIEW_PLUGIN_WORKFLOW_CONTENT = """name: vivian Code Review

on:
  pull_request:
    types: [opened, synchronize, ready_for_review, reopened]
    # Optional: Only run on specific file changes
    # paths:
    #   - "src/**/*.ts"
    #   - "src/**/*.tsx"
    #   - "src/**/*.js"
    #   - "src/**/*.jsx"

jobs:
  vivian-review:
    # Optional: Filter by PR author
    # if: |
    #   github.event.pull_request.user.login == 'external-contributor' ||
    #   github.event.pull_request.user.login == 'new-developer' ||
    #   github.event.pull_request.author_association == 'FIRST_TIME_CONTRIBUTOR'

    runs-on: ubuntu-latest
    permissions:
      contents: read
      pull-requests: read
      issues: read
      id-token: write

    steps:
      - name: Checkout repository
        uses: actions/checkout@v4
        with:
          fetch-depth: 1

      - name: Run vivian Code Review
        id: vivian-review
        uses: anthropics/vivian-code-action@v1
        with:
          anthropic_api_key: ${{ secrets.ANTHROPIC_API_KEY }}
          plugin_marketplaces: 'https://github.com/anthropics/vivian-code.git'
          plugins: 'code-review@vivian-code-plugins'
          prompt: '/code-review:code-review ${{ github.repository }}/pull/${{ github.event.pull_request.number }}'
          # See https://github.com/anthropics/vivian-code-action/blob/main/docs/usage.md
          # or https://api-vivian.d0a.net/docs/en/cli-reference for available options

"""

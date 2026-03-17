# Contributing to Kubernetes Auto-Scaling Intelligence Engine

First off, thank you for considering contributing to KubASIE! It's people like you that make KubASIE such a great tool.

## Where do I go from here?

If you've noticed a bug or have a feature request, make one! It's generally best if you get confirmation of your bug or approval for your feature request this way before starting to code.

## Fork & create a branch

If this is something you think you can fix, then fork KubASIE and create a branch with a descriptive name.

A good branch name would be (where issue #325 is the ticket you're working on):

```sh
git checkout -b 325-add-new-metric-collector
```

## Get the test suite running

Make sure you're using Python 3.11+ and have Docker installed.
To run the tests for the individual components:

```bash
# Example for scaling-engine
cd scaling-engine
pip install -r requirements.txt
python -m pytest tests/ -v
```

## Implement your fix or feature

At this point, you're ready to make your changes. Feel free to ask for help; everyone is a beginner at first :smile_cat:

## Open a Pull Request

When you're ready, open a PR against the `main` branch. Ensure that you have followed the PR template and all checks pass.

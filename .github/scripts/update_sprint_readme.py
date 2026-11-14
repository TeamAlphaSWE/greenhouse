"""Rewrites the sprint block of the "Sprint" project's README.

Run by .github/workflows/update-sprint-readme.yml. Reads the GraphQL
response (project readme plus the Sprint iteration field) from the file
named in argv[1] and writes the new README body to stdout. Only the text
between the markers is touched, so anything else written into the
project README by hand is left alone.
"""
import json
import sys
from datetime import date, datetime, timedelta

START_MARK = "<!-- sprint-readme:start -->"
END_MARK = "<!-- sprint-readme:end -->"


def current_iteration(iterations):
    today = date.today()
    for iteration in iterations:
        start = datetime.strptime(iteration["startDate"], "%Y-%m-%d").date()
        end = start + timedelta(days=iteration["duration"])
        if start <= today < end:
            return iteration, start, end
    return None


def sprint_block(found):
    if found is None:
        body = "No sprint is currently active."
    else:
        iteration, start, end = found
        number = iteration["title"].split()[-1]
        body = (
            f"**Sprint {number}**: {start.isoformat()} to {end.isoformat()}\n\n"
            "_Updated automatically; do not edit this section by hand._"
        )
    return f"{START_MARK}\n## Current Sprint\n\n{body}\n{END_MARK}"


def splice(readme, block):
    readme = readme or ""
    if START_MARK in readme and END_MARK in readme:
        before = readme.split(START_MARK)[0]
        after = readme.split(END_MARK)[1]
        return before + block + after
    separator = "\n\n" if readme.strip() else ""
    return readme + separator + block + "\n"


def main():
    with open(sys.argv[1]) as handle:
        data = json.load(handle)

    project = data["data"]["organization"]["projectV2"]
    iterations = project["field"]["configuration"]["iterations"]
    block = sprint_block(current_iteration(iterations))
    sys.stdout.write(splice(project["readme"], block))


if __name__ == "__main__":
    main()

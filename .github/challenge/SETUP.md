# CQ4OE submission evaluation Action — setup

One workflow, `evaluate-submission.yml`, runs automatically on every pull
request that adds or changes a `submissions/` folder and does four things:

1. **Detects** which submission changed (git diff against the base branch).
2. **Validates** it against the submission guideline — `validate_submission.py`
   checks `metadata.yml`, that every declared task/domain file is present, and
   that the JSON/OWL files parse in the required formats. If anything is off the
   run fails here and nothing is evaluated.
3. **Evaluates** the submitted results — stages the files into the pipeline
   layout, then runs `run_all_cq2term.py --models <name>` and
   `run_all_evaluation_agent_datsets.py --modes challenge`.
4. **Writes results** into a new folder `submissions/<name>/evaluation/`
   (per-domain result JSONs/CSVs, the `_summary` reports, and a `SUMMARY.md`
   with headline F1s) and commits it back onto the PR branch.

CI runs only the repo's own scripts on the submitted data files; it never
executes the participant's `code/` folder.

## Files

```
.github/
├── workflows/evaluate-submission.yml
└── challenge/
    ├── validate_submission.py        # step 2
    ├── stage_submission.py           # step 3 (maps submission -> pipeline paths)
    ├── collect_into_submission.py    # step 4 (writes submissions/<name>/evaluation/)
    └── runners.patch                 # one-time runner edits (see below)
```

## One-time repo changes (required)

Apply the runner patch from the repo root (parameterizes the hardcoded `PYTHON`
path and registers the `challenge` mode in the CQ2Onto runner):

```bash
git apply .github/challenge/runners.patch
```

Commit the `.github/` folder to your default branch (`main`). A workflow only
fires if it already exists on `main`; a workflow added inside a PR does not run
for that PR.

## The fork limitation (important)

Step 4 commits results onto the PR branch. That is only possible when the PR
comes from a branch **in this repository**. GitHub gives **fork** PRs a
read-only token that cannot push to the contributor's fork, so for fork PRs the
results are produced and uploaded as a **workflow artifact** instead, with a note
in the run summary. To have committed results for fork submissions, add them at
merge time (a `push`-to-`main` workflow can run the same steps and commit the
`evaluation/` folder into `main`) — ask for that variant when needed.

If your participants push branches directly to this repo (collaborator model),
step 4 commits to the PR branch as described, with no fork caveat.

## Loop prevention

The commit in step 4 uses a `[skip ci]` message, so the resulting branch update
does not retrigger the workflow. A real new commit from the participant (without
`[skip ci]`) triggers a fresh evaluation, and `evaluation/` is regenerated
cleanly each time.

## Environment (handled by the workflow)

- Ollama serving `embeddinggemma` (semantic matching for both tasks), cached.
- Java 17 (owlready2/HermiT, CQ2Onto hierarchy layer).
- Python 3.10 + `requirements.txt`.

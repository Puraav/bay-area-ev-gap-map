# Bay Area EV Charging Gap Map — Claude Code Playbook

Everything you need to build the project end to end with Claude Code. Follow the steps in order. Each step = one prompt you paste into Claude Code + one spec file it reads.

**Total time:** ~3–4 hours (stretch step adds ~1 hour).

---

## Before you start (10 minutes, done by you)

1. **Install:** Python 3.11+, Git, Claude Code, and the GitHub CLI (`gh`). Run `gh auth login` once.
2. **Get a free NREL API key:** sign up at https://developer.nrel.gov/signup/ (instant, emailed). `DEMO_KEY` works for testing but is rate-limited.
3. **Create the project folder and copy these files into it:**

```
bay-area-ev-gap-map/
├── CLAUDE.md                  ← project rules Claude Code reads automatically
├── 00_START_HERE.md           ← this file
└── specs/
    ├── 01_setup.md
    ├── 02_fetch_data.md
    ├── 03_build_metrics.md
    ├── 04_streamlit_app.md
    ├── 05_charts.md
    ├── 06_tests.md
    ├── 07_readme_findings.md
    └── 08_stretch_renters_and_deploy.md
```

4. Open a terminal in `bay-area-ev-gap-map/` and run `claude`.

---

## The prompts (paste one at a time; wait for each to finish)

### Prompt 1 — Setup
```
Read CLAUDE.md and specs/01_setup.md. Do everything in 01_setup.md, run its "Done when" checks, show me the results, then commit.
```

### Prompt 2 — Fetch the data
```
Read specs/02_fetch_data.md and implement it. My NREL API key is <PASTE KEY or use DEMO_KEY>. Put it in .env, never in code. Run the fetch, run every "Done when" check, show me the printed summary, then commit.
```

### Prompt 3 — Build the metrics
```
Read specs/03_build_metrics.md and implement it. Run the build, run every "Done when" check, print the top 15 ZIPs by gap_score and the county summary table, then commit.
```
**Check yourself:** do the top ZIPs look plausible (dense, high-EV areas with few public chargers)? If a ZIP looks odd, ask Claude Code: "Explain why ZIP <xxxxx> ranks here and show its raw numbers."

### Prompt 4 — The app
```
Read specs/04_streamlit_app.md and build the app. Start it locally, confirm it loads with no errors, tell me the URL to open, then commit.
```
Open the URL and click around. Ask for fixes in plain English if anything looks off.

### Prompt 5 — Charts for LinkedIn
```
Read specs/05_charts.md and implement it. Generate all charts into charts/, list the files with a one-line description of each, then commit.
```

### Prompt 6 — Tests
```
Read specs/06_tests.md, write the tests, run pytest, fix anything that fails, then commit.
```

### Prompt 7 — README and findings
```
Read specs/07_readme_findings.md. Compute the findings from the processed data, write the README, then print the 3–5 headline findings with exact numbers. Commit.
```

### Prompt 8 — Publish to GitHub
```
Create a public GitHub repo named bay-area-ev-gap-map under my account with gh, push all commits, add the repo description and topics from specs/07_readme_findings.md, and give me the repo URL.
```

### Prompt 9 (optional) — Stretch: renters + live app
```
Read specs/08_stretch_renters_and_deploy.md and implement part A, rerun the build and app, update the README findings, commit and push. Then walk me through part B (deploying to Streamlit Community Cloud) step by step.
```

---

## If something goes wrong

| Problem | Paste this |
|---|---|
| A download URL fails | `That URL failed. Find the current official URL from the source's own site or API listing (as described in the spec), update fetch.py and retry.` |
| Numbers look wrong | `Stop. Show me the raw counts for <ZIP or county> at each step of the pipeline so we can find where they change.` |
| App errors | `Here is the error: <paste>. Fix it and restart the app.` |
| It's going off-spec | `Re-read CLAUDE.md and the current spec file. Undo anything not asked for.` |

---

## When you're done, send me

1. The repo URL (and the app URL if you deployed it)
2. The headline findings Claude Code printed in Prompt 7
3. The PNGs from `charts/`

I'll draft the LinkedIn post in Typefully as a draft for you to approve.

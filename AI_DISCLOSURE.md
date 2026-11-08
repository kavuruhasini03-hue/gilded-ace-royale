# AI-use disclosure

AI tools were used, as the TAMU Datathon rules allow. The team reviewed every number, decision and recommendation against the data.

| Tool | Used by | What for |
|---|---|---|
| Claude Code (Anthropic, Claude Opus 5.5) | Srikar | Code review of the pipeline, which found a units error in `analysis/recon.py`. Building the public dashboard site (`site/index.html`, `site/build_data.py`): an independent DuckDB re-computation of the 4-L bridge, the forecast and the inspection statistics. Drafting the write-up, this appendix, the README and the video script. Rendering the narrated walkthrough video (headless-Chrome screenshots + macOS text-to-speech + ffmpeg). Generating the site's background music and sound effects procedurally with the Web Audio API. |
| _Hasini: fill in_ | Hasini | _List any AI tools used for the Databricks SQL pipeline, the AI/BI dashboard, METHODS.md and the recon script, or write "None"._ |
| _Prady: fill in_ | Prady | _List, or write "None"._ |

**What AI did not decide:** the choice of recommendation, the funding bar for the comp pilot, and the interpretation of the walkway closure were team decisions. The site's re-computed results were checked against the numbers in the pipeline docs (`docs/RECON.md`, `METHODS.md`) and the dashboard definition: the bottom ten, M-1158 (z = −4.57), and forecast MAE of $218,258 vs. $55,271 all match.

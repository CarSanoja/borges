# Submission package

Track: **Best Apps and Agents**. Copy-ready description: [devpost.md](devpost.md).
Required platform feedback: [feedback.md](feedback.md). Narration: [video-script.md](video-script.md).
Clean ElevenLabs input: [voiceover.txt](voiceover.txt). Final video with the owner's ElevenLabs
audio: [borges-demo.mp4](borges-demo.mp4), 2:03, 1920×1080. Its edit manifest is
[video-edit.json](video-edit.json).

## Quality round, 25–26 October 2026

| Check | Result |
|---|---|
| Full Python suite on the working tree | 4,029 passed, 6 skipped, 2 live tests deselected, 40m53s |
| Haiku transport/budget regression tests added afterwards | 3 passed |
| Frontend | 359 passed; typecheck and production build passed |
| Frontend dependency audit | 0 reported vulnerabilities after patching Vite to 8.3.3 and jsdom's Undici dependency to 8.12.2; all 359 frontend tests, typecheck and build passed again |
| Ruff | All checks passed; 1,276 files formatted |
| Production Docker build and startup | Passed, healthy, non-root process |
| Packaged HTTP checks | All nine historical recordings served; fresh scripted checkout completed, verified flip; POST returned in 0.034s |
| Historical Nemotron checkout reproduction | MATCH on estimate, interval, p-value, n and verdict |
| Final Haiku engine validation | checkout: 19 universes, 0 failed; red cards: 18 universes, 0 failed, reproduced significance flip; both final narratives completed |
| Haiku estimated spend, including initial attempts and connection probe | $0.0712583, from reported tokens and published prices; $0.50 total cap |
| Git history secret scan | 728 commits scanned; one inspected synthetic redaction-test token allowlisted by exact fingerprint; no remaining findings |
| Browser QA | Desktop and responsive 390px reviewed; flipping-universe drawer opened and closed with Escape; screenshots in `assets/screenshots/submission/` |

The full Python run started before the three new transport tests were added; those three were
run separately afterwards. Live Nebius calls now return 401 with the local credential. The
historical Nemotron recordings remain intact. Haiku validation tests the actual analysis
pipeline with a temporary, budgeted provider; it does not certify the current availability of
the Nebius account. No historical recording was relabelled.

Machine-readable results are in [packaged HTTP checks](../evidence/test-suite/packaged-2026-10-25.json)
and [Haiku validation](../evidence/test-suite/haiku-2026-10-25.json).
The dependency fixes were also rebuilt into Docker and passed the
[packaged HTTP checks again](../evidence/test-suite/packaged-security-2026-10-26.json).
The [dependency audit](../evidence/test-suite/frontend-audit-2026-10-26.json) includes development
dependencies, and [the patch record](../evidence/test-suite/dependency-fixes-2026-10-26.json)
links the advisories and exact versions.

## Run the NVIDIA delivery configuration

Store working Nebius credentials and the Sandbox project ID in `.env`, then:

```bash
docker compose -f compose.demo.yaml up --build -d
uv run --no-sync python scripts/submission_smoke.py --url http://127.0.0.1:8000 --require-live
```

This configuration selects **NVIDIA/Nebius and ConTree**, keeps state across restarts, and binds
port 8000 to localhost for a hosting reverse proxy. It does not read `.env.haiku`. Put an HTTPS
reverse proxy in front of this port on the deployment host. To verify a billable run explicitly:

```bash
uv run --no-sync python scripts/submission_smoke.py --url https://YOUR-DEMO-HOST --run-live --max-cost-usd 0.50
```

The default live endpoint budget is $5 total and $0.50 per run. Ensure account credits and the
application budget remain available during judging. Recordings work without model credits.

## Repeat the Haiku validation

The separate private `.env.haiku` holds `ANTHROPIC_API_KEY`; it is excluded from Git and Docker.

```bash
uv run --no-sync python scripts/validate_haiku.py
```

The harness uses the native Anthropic Messages API, Haiku 5.5, thinking disabled, $0.25 per case
and $0.50 total. Its own gateway and identity capabilities permit Haiku only inside the
validation environment. The production policy, defaults and agent registry remain NVIDIA.

## Judge instructions

1. Open the hosted demo and the checkout recorded run. Its banner identifies the historical
   Nemotron date, model usage and estimated cost.
2. Open the flipping path to inspect its code and reproduction command.
3. On a fresh clone, run `uv sync`, then:

```bash
uv run borges replay --case checkout_ab
uv run borges reproduce --case checkout_ab --source live --universe u_fb948f9bb7
```

4. Select red cards for a real-data significance flip. The nine recordings need no API key.
5. When the hosted account has credits, use **Run live on Nemotron** to start a new analysis.

## Final publication steps

- Make `CarSanoja/borges` public; it is currently private.
- Deploy the prepared Docker configuration and insert its HTTPS URL in the README and Devpost.
- Upload the demo video publicly to YouTube and insert its link.
- Copy the description, testing instructions and feedback into Devpost; select the track and
  submit. The draft files are ready, but no Devpost submission has been made by this quality run.

The official deadline is **30 October 2026, 10:00 PDT (13:00 Caracas)**. Judging ends
15 December 2026; keep the judge-facing app accessible through then. See the
[official rules](https://nebiusglobalaihackathon.devpost.com/rules).

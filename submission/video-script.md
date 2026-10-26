# Video script and capture plan

Target length: 2:30 to 2:50. English narration. Use the actual application and keep the
recording's date and model labels visible. The historical replay is a recorded live run;
the new Haiku validation is a separate test, not a new Nemotron recording.

The owner will generate the final audio in ElevenLabs from [voiceover.txt](voiceover.txt).
The existing MP4 is a temporary assembly for editing; replace its synthetic local voice before
publication and fit the shots to the supplied audio.

## 0:00–0:25 — The problem

An AI analyst gives you one answer. But it also chooses which rows to keep, which variables to
adjust for and which model to fit. Another reasonable choice can change the decision. Borges
shows those other paths, and the evidence behind them.

## 0:25–1:30 — A decision changes

Here is a synthetic checkout experiment with a planted data problem. This is a recorded live
run of NVIDIA Nemotron on Nebius Token Factory. The original analysis says ship: a lift of
0.85 percentage points.

Nemotron proposes alternative analyses. Each choice forks a sandbox from the checkpoint before
it. An adversary proposes more alternatives, and a separate judge checks whether they are
defensible.

Excluding internal test sessions changes the estimate to minus 0.15 percentage points. The
decision becomes don't ship. This is a direction flip, not merely a p-value crossing.

Open that path and you can inspect the actual code, the rows it used and a command that reruns
the analysis. Here, the fresh result matches the recording.

## 1:30–2:05 — Real data and honest limits

The red-cards case uses real research data. Its recorded flip keeps the effect's direction,
but crosses the significance threshold. Borges labels that difference. Other cases find no
flip. A bounded search cannot prove that every possible analysis agrees, and the report says
what it explored and which paths failed.

## 2:05–2:40 — How it works and why it matters

Token Factory serves the NVIDIA models. Our current configuration uses Nemotron Super for
reasoning and Lightning for coding. The historical recordings also show the models used at
the time. Nebius Token Factory Sandboxes supplied the branchable, VM-isolated execution in all
nine recordings.

Borges is a second opinion before you act on an analysis: which paths agree, which choice
changes the answer, and can somebody else reproduce it? The code is Apache licensed, and the
recorded examples can be checked offline.

## Shots

1. Landing page and the checkout headline; open its recorded run.
2. Garden growing, with the recorded-live banner visible.
3. Final verdict, direction flip and specification curve.
4. Flipping universe drawer, code and reproduce command.
5. Terminal with the actual `MATCH` output.
6. Red-cards replay and its significance-only flip.
7. Fleet/Platform views; final card with the public URLs after publication.

Before upload, check duration below 3:00, readable text, audible NVIDIA/Nebius names and no
credentials or unrelated browser tabs in frame. Replace the closing URLs only after they work.

# Platform feedback

## What we used

We used NVIDIA Nemotron on Nebius Token Factory for planning, coding, defensibility judging,
adversarial proposals, repair, review and narration. Nine committed recordings ran on Token
Factory Sandboxes (ConTree). We did not use Nebius AI Cloud compute.

Our current configuration uses Super for the reasoning roles and Lightning for coding.
Historical runs also used Ultra and Nano; the recordings preserve the models actually called.

## What worked

The OpenAI-compatible inference endpoint made it straightforward to route different roles to
different models. Structured responses and the thinking switch supported a predictable analysis
pipeline. Token-level usage allowed us to maintain a local spend ledger and reserve a call's
estimated cost before sending it. ConTree's branchable checkpoints match the application's
analysis tree particularly well: paths with a common prefix reuse their execution state.

## What we would improve

- Sandboxes onboarding should put the required project ID beside the API-key instructions. A
  missing project produced a 403 whose message did not identify that missing configuration.
- Model lifecycle information should make removals and replacement models easier to discover.
  During development, Ultra returned 404, so we changed the primary judge and narrator to Super.
- A per-key spend limit and a documented usage/balance endpoint would simplify public demos.
  We implemented application-level caps, and our promotional credits were eventually exhausted.
- Clear published concurrency limits would help size parallel code-generation calls.
- Hackathon credit validity should cover the judging period, or offer a documented renewal path.

## Onboarding and future use

Inference onboarding was quick. Sandbox access and finding the project-ID requirement took
longer. We would use Token Factory and ConTree again for multi-step analysis agents, especially
when branchable state matters. We would evaluate AI Cloud hosting separately; we have no
production-use experience with it to report.

The final quality round used Haiku separately after the Token Factory credits were exhausted.
The project's delivery configuration remains NVIDIA/Nebius, and its historical live evidence
remains available offline without credentials.

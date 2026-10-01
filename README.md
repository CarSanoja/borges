# Borges

**Every conclusion is one path through a garden of forking analyses. Borges walks the
others, and shows you the one defensible choice that flips your decision.**

Built for the [Nebius x NVIDIA Global AI Hackathon](https://nebiusglobalaihackathon.devpost.com/)
on **NVIDIA Nemotron 3** served by **Nebius Token Factory**, with every analysis universe
running as a branch of a **Nebius Token Factory Sandbox**.

---

## The problem

In 2018, 29 research teams were given the same dataset and the same question: are soccer
referees more likely to give red cards to dark-skin-toned players? Their answers ranged from
no effect (odds ratio 0.89) to nearly triple (2.93). Twenty teams said yes, nine said no.
Nobody made a mistake. They made different, defensible analysis choices
([Silberzahn et al., 2018](https://journals.sagepub.com/doi/10.1177/2515245917747646)).

In July 2026, PNAS showed that AI analysts do the same
([Many AI analysts, one dataset](https://pmc.ncbi.nlm.nih.gov/articles/PMC13393493/)). More and
more decisions now rest on an analysis an AI wrote along a single path. It returns one
confident answer and never shows the paths it did not take.

## What Borges does

Give Borges a dataset, a question and the rule you will act on, for example *"ship if the
conversion lift is positive with p < 0.05"*.

1. **Nemotron plans the analysis like a senior statistician** and lists the defensible
   alternatives at every step where experts disagree.
2. **Every choice forks a real sandbox.** Each step runs in an isolated VM-backed sandbox,
   and each alternative branches from the exact execution state of the step before.
3. **An adversarial analyst argues against your conclusion, with code.** It reads what the
   real data did at each step and proposes new defensible choices; an independent judge
   scores them.
4. **Borges finds the minimal defensible flip**, the smallest set of changes that reverses
   your decision, and re-executes it from scratch to prove it reproduces.
5. **You can step into any universe** and see its exact code, row counts and result.

## Quickstart

```bash
make install          # uv sync + pnpm install
make demo-cli         # checkout A/B case, offline and deterministic
make serve            # web app on http://127.0.0.1:8000
```

To run on Nemotron live, put your Token Factory key in `.env` (see `.env.example`) and pass
`--llm nebius`. A hard spend cap (`BORGES_SPEND_CAP_USD`) protects the credits.

## Architecture

See [ARCHITECTURE.md](ARCHITECTURE.md) and [PRODUCT.md](PRODUCT.md).

## License

Apache-2.0.

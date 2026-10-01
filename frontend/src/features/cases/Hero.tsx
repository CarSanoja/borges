const STEPS = [
  { n: "I", title: "Fork", text: "Every defensible choice becomes a real sandbox fork of the analysis." },
  { n: "II", title: "Argue", text: "An adversary argues against the conclusion, with code, on the actual data." },
  { n: "III", title: "Flip", text: "Borges finds the one defensible change that reverses the decision." },
];

export function Hero() {
  return (
    <header className="landing-hero">
      <p className="eyebrow">Borges · The garden of forking paths</p>
      <h1 className="landing-title">Every conclusion is one path through a garden.</h1>
      <p className="landing-sub">29 research teams. Same data. Opposite answers.</p>
      <ol className="landing-steps">
        {STEPS.map((step) => (
          <li key={step.n}>
            <span className="landing-step-n">{step.n}</span>
            <h2>{step.title}</h2>
            <p>{step.text}</p>
          </li>
        ))}
      </ol>
    </header>
  );
}

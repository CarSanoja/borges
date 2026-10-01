import { tokenize } from "./highlight";

interface Props {
  code: string;
  label: string;
}

export function CodeBlock({ code, label }: Props) {
  return (
    <pre className="code-block" aria-label={label}>
      <code>
        {tokenize(code).map((token, index) => (
          <span key={index} className={`tok-${token.kind}`}>
            {token.text}
          </span>
        ))}
      </code>
    </pre>
  );
}

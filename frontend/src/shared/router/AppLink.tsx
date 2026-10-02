import type { MouseEvent, ReactNode } from "react";
import { navigate } from "./useLocation";

interface Props {
  to: string;
  className?: string;
  children: ReactNode;
}

export function AppLink({ to, className, children }: Props) {
  const onClick = (event: MouseEvent<HTMLAnchorElement>) => {
    if (event.defaultPrevented || event.button !== 0) return;
    if (event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
    event.preventDefault();
    navigate(to);
  };
  return (
    <a href={to} className={className} onClick={onClick}>
      {children}
    </a>
  );
}

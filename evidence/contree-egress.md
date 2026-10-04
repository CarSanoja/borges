# Network egress from ConTree sandboxes

Measured live on 2026-10-04 04:06 UTC, from this repository at 909f68e, on Nebius ConTree.

## ConTree alone does not block egress

A plain Python script run in a ConTree sandbox (the Borges runner image, no Borges policy) opened
TCP connections to the internet:

```
{"1.1.1.1": "connected", "pypi.org": "connected"}
```

The installed `contree_sdk` exposes no network option on image runs, and Borges does not configure
one. The runner image itself is built with `pip install`, which needs the network.

## What blocks it in Borges

Every step Borges runs starts with its runtime policy, an audit hook installed before the
option's code. The same connection attempted from a step's code, rendered by `render_step` and run
in ConTree, failed before any packet left:

```
PermissionError: runtime policy denied socket.getaddrinfo
```

Before that, the code guard refuses code that imports `socket` or calls `__import__`, so this probe
had to bypass the guard to reach the sandbox at all.

## What this means

- Egress control is in-process: the code guard, then the audit-hook runtime policy. Neither is a
  network boundary; SECURITY.md lists what an audit hook cannot stop.
- `sandbox_network: none` in the gateway policy is a declaration that Borges enforces in process,
  not a ConTree setting.
- A network-level boundary would need a sandbox with egress disabled at the platform, which the
  current SDK does not offer.

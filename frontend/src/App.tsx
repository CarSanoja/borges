import { Landing } from "./features/cases/Landing";
import { RunPage } from "./features/run/RunPage";
import { navigate, replayPath, runPath, useLocation, withMock } from "./shared/router";

export function App() {
  const { route, mock } = useLocation();
  const home = () => navigate("/");

  if (route.name === "run") {
    const source = mock ? ({ kind: "mock" } as const) : ({ kind: "live", runId: route.runId } as const);
    return (
      <RunPage
        key={`run:${route.runId}:${mock}`}
        source={source}
        onHome={home}
        onOpenReplay={(caseId) => navigate(replayPath(caseId))}
      />
    );
  }

  if (route.name === "replay") {
    const source = mock
      ? ({ kind: "mock" } as const)
      : ({ kind: "replay", caseId: route.caseId, speed: 1 } as const);
    return <RunPage key={`replay:${route.caseId}:${mock}`} source={source} onHome={home} />;
  }

  if (route.name === "not_found") {
    return (
      <main className="not-found">
        <h1>Lost in the garden</h1>
        <button type="button" onClick={home}>
          Return to the entrance
        </button>
      </main>
    );
  }

  return (
    <Landing
      onOpenRun={(runId) => navigate(runPath(runId))}
      onOpenReplay={(caseId) => navigate(replayPath(caseId))}
      onOpenMock={() => navigate(withMock(runPath("sample")))}
    />
  );
}

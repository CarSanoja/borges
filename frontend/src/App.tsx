import { Landing } from "./features/cases/Landing";
import { RunPage } from "./features/run/RunPage";
import { ReplayRoute } from "./features/run/ReplayRoute";
import { NotFound } from "./features/notfound/NotFound";
import { navigate, replayPath, runPath, useLocation, useScrollToTop, withMock } from "./shared/router";

export function App() {
  const { route, mock } = useLocation();
  const home = () => navigate("/");
  useScrollToTop(`${route.name}:${"runId" in route ? route.runId : "caseId" in route ? route.caseId : ""}`);

  if (route.name === "run") {
    const source = mock ? ({ kind: "mock" } as const) : ({ kind: "live", runId: route.runId } as const);
    return (
      <RunPage
        key={`run:${route.runId}:${mock}`}
        source={source}
        onHome={home}
      />
    );
  }

  if (route.name === "replay") {
    const source = mock
      ? ({ kind: "mock" } as const)
      : ({ kind: "replay", caseId: route.caseId, speed: 1 } as const);
    if (mock) return <RunPage key={`replay:${route.caseId}:${mock}`} source={source} onHome={home} />;
    return <ReplayRoute key={`replay:${route.caseId}`} caseId={route.caseId} onHome={home} />;
  }

  if (route.name === "not_found") {
    return <NotFound title="Page not found" message="There is nothing at this address." />;
  }

  return (
    <Landing
      onOpenRun={(runId) => navigate(runPath(runId))}
      onOpenReplay={(caseId) => navigate(replayPath(caseId))}
      onOpenMock={() => navigate(withMock(runPath("sample")))}
    />
  );
}

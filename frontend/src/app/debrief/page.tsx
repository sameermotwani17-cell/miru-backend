import { Suspense } from "react";
import DebriefContent from "./DebriefContent";
import ErrorBoundary from "@/components/ErrorBoundary";

export default function DebriefPage() {
  return (
    <ErrorBoundary>
      <Suspense
        fallback={
          <div
            style={{
              minHeight: "100vh",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              fontFamily: "sans-serif",
              color: "#a8a9c7",
              fontSize: 14,
            }}
          >
            Generating interview report…
          </div>
        }
      >
        <DebriefContent />
      </Suspense>
    </ErrorBoundary>
  );
}

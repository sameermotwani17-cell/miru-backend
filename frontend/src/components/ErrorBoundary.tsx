"use client";

import React from "react";

interface ErrorBoundaryProps {
  children: React.ReactNode;
  fallback?: React.ReactNode;
}

interface ErrorBoundaryState {
  hasError: boolean;
  message: string;
}

export default class ErrorBoundary extends React.Component<
  ErrorBoundaryProps,
  ErrorBoundaryState
> {
  constructor(props: ErrorBoundaryProps) {
    super(props);
    this.state = { hasError: false, message: "" };
  }

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { hasError: true, message: error?.message ?? "Unknown error" };
  }

  componentDidCatch(error: Error, info: React.ErrorInfo): void {
    console.error("[ErrorBoundary] Caught render error:", error, info);
  }

  render() {
    if (this.state.hasError) {
      if (this.props.fallback) {
        return this.props.fallback;
      }
      return (
        <div
          style={{
            minHeight: "100vh",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            flexDirection: "column",
            gap: 16,
            padding: 24,
            backgroundColor: "#050508",
            fontFamily: "sans-serif",
          }}
        >
          <p
            style={{
              color: "#ef4444",
              fontSize: 14,
              textAlign: "center",
              maxWidth: 480,
            }}
          >
            Something went wrong loading the interview UI.
          </p>
          <p
            style={{
              color: "#666",
              fontSize: 12,
              textAlign: "center",
              maxWidth: 480,
            }}
          >
            {this.state.message}
          </p>
          <button
            onClick={() => (window.location.href = "/")}
            style={{
              padding: "10px 24px",
              borderRadius: 8,
              border: "1px solid rgba(255,255,255,0.2)",
              background: "rgba(255,255,255,0.07)",
              color: "#f0f0ff",
              fontSize: 13,
              cursor: "pointer",
            }}
          >
            Return Home
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}

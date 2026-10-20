import { Component, type ReactNode } from "react";

/** Keeps one failing panel from blanking the whole dashboard. */
export default class ErrorBoundary extends Component<{ children: ReactNode; resetKey?: string }, { error: Error | null }> {
  state = { error: null as Error | null };
  static getDerivedStateFromError(error: Error) { return { error }; }
  componentDidUpdate(prev: { resetKey?: string }) {
    if (prev.resetKey !== this.props.resetKey && this.state.error) this.setState({ error: null });
  }
  render() {
    if (!this.state.error) return this.props.children;
    return (
      <div className="card text-[14px] text-ink-2">
        <div className="card-title mb-1">This view could not be drawn</div>
        <p className="text-ink-muted">{this.state.error.message}</p>
      </div>
    );
  }
}

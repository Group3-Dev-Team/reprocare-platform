import { Component } from 'react';

/** Last-resort screen if a page crashes, so visitors are never left with a blank page. */
export class ErrorBoundary extends Component {
  constructor(props) {
    super(props);
    this.state = { error: null };
  }

  static getDerivedStateFromError(error) {
    return { error };
  }

  componentDidCatch(error, info) {
    console.error('ReproCare page error', error, info.componentStack);
  }

  render() {
    if (!this.state.error) return this.props.children;
    return (
      <div className="container" style={{ padding: '80px 0' }}>
        <div className="state state-error" role="alert">
          <h1 style={{ fontSize: 'var(--text-xl)' }}>Something went wrong on this page</h1>
          <p>Reload the page to try again. If it keeps happening, tell us through the Contact page.</p>
          <button className="btn btn-primary" onClick={() => window.location.reload()}>
            Reload the page
          </button>
        </div>
      </div>
    );
  }
}

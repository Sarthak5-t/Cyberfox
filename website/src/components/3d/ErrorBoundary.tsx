import React, { Component, type ReactNode } from 'react';

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
  onError?: (error: Error) => void;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

export default class ThreeErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error) {
    this.props.onError?.(error);
  }

  render() {
    if (this.state.hasError) {
      if (this.props.fallback) {
        return this.props.fallback;
      }
      return (
        <div
          style={{
            padding: '2rem',
            textAlign: 'center',
            color: 'rgba(232, 228, 220, 0.5)',
            fontFamily: "'JetBrains Mono', monospace",
            fontSize: '0.85rem',
          }}
          role="alert"
        >
          <p>3D scene failed to load.</p>
        </div>
      );
    }
    return this.props.children;
  }
}

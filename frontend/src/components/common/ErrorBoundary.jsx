import React from 'react'
import { AlertCircle, RefreshCw } from 'lucide-react'

export class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props)
    this.state = { hasError: false, error: null, errorInfo: null }
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error }
  }

  componentDidCatch(error, errorInfo) {
    const correlationId = error?.response?.data?.correlation_id || error?.correlationId
    if (correlationId) {
      console.error(`[Correlation ID: ${correlationId}]`)
    }
    console.error('Global ErrorBoundary caught an error', error, errorInfo)
    this.setState({ errorInfo })
  }

  render() {
    if (this.state.hasError) {
      const isDev = import.meta.env.DEV
      return (
        <div className="min-h-[50vh] flex flex-col items-center justify-center p-6 m-4 bg-[var(--bg_primary)] border border-red-500/30 rounded-xl">
          <div className="max-w-3xl w-full text-center">
            <div className="w-16 h-16 bg-red-500/10 text-red-500 rounded-full flex items-center justify-center mx-auto mb-6 border border-red-500/20">
              <AlertCircle className="h-8 w-8" />
            </div>
            <h1 className="text-2xl font-bold text-[var(--text_primary)] mb-2">
              Something went wrong
            </h1>
            <p className="text-[var(--text_secondary)] mb-8 text-sm">
              {this.state.error?.message || 'An unexpected error occurred.'}
            </p>
            <button
              onClick={() => window.location.reload()}
              className="mx-auto bg-blue-600 hover:bg-blue-700 text-[var(--text_primary)] font-medium px-6 py-3 rounded-lg flex items-center justify-center gap-2 transition-colors shadow-lg mb-8"
            >
              <RefreshCw className="h-5 w-5" /> Reload page
            </button>

            {isDev && this.state.errorInfo && (
              <div className="w-full bg-[var(--bg_primary)] border border-[var(--border)] rounded-lg p-4 overflow-auto text-left">
                <h3 className="text-red-400 font-mono text-sm mb-2 font-bold">
                  Stack Trace (DEV Only):
                </h3>
                <pre className="text-[var(--text_secondary)] font-mono text-xs whitespace-pre-wrap leading-relaxed">
                  {this.state.error && this.state.error.stack}
                  <br />
                  {this.state.errorInfo.componentStack}
                </pre>
              </div>
            )}
          </div>
        </div>
      )
    }
    return this.props.children
  }
}

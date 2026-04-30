import React, { useState } from 'react'
import { CheckCircle, XCircle, Clock, AlertCircle, Terminal, Bug } from 'lucide-react'

export default function ExecutionOutput({ result, loading }) {
  const [activeTab, setActiveTab] = useState('output')

  if (!result) return null

  const getStatusColor = (status) => {
    switch (status) {
      case 'passed': return 'text-green-600'
      case 'failed': return 'text-red-600'
      case 'timeout': return 'text-orange-600'
      case 'runtime_error': return 'text-red-700'
      default: return 'text-gray-600'
    }
  }

  const getStatusIcon = (status) => {
    switch (status) {
      case 'passed':
        return <CheckCircle className="w-5 h-5 text-green-600" />
      case 'failed':
        return <XCircle className="w-5 h-5 text-red-600" />
      case 'timeout':
        return <Clock className="w-5 h-5 text-orange-600" />
      default:
        return <AlertCircle className="w-5 h-5 text-red-700" />
    }
  }

  const { status, output, error, test_results, execution_time } = result
  const passed = test_results?.filter(t => t.passed).length || 0
  const total = test_results?.length || 0

  const tabs = [
    { id: 'output', label: 'Output', icon: Terminal },
    { id: 'tests', label: 'Tests', icon: CheckCircle },
    ...(error ? [{ id: 'errors', label: 'Errors', icon: AlertCircle }] : []),
    { id: 'debug', label: 'Debug Info', icon: Bug },
  ]

  return (
    <div className="bg-gray-900 text-gray-100 rounded-lg border border-gray-700 overflow-hidden">
      {/* Status Header */}
      <div className="bg-gray-800 p-4 border-b border-gray-700">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            {getStatusIcon(status)}
            <div>
              <div className={`font-bold capitalize ${getStatusColor(status)}`}>
                {status === 'passed' ? 'All Tests Passed!' : status.replace(/_/g, ' ')}
              </div>
              {test_results && (
                <div className="text-xs text-gray-400 mt-1">
                  {passed}/{total} tests passed {execution_time && `• ${execution_time.toFixed(2)}s`}
                </div>
              )}
            </div>
          </div>
          <div className="text-right">
            {status === 'passed' && (
              <div className="text-2xl">🎉</div>
            )}
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-0 bg-gray-800 border-b border-gray-700">
        {tabs.map(({ id, label, icon: Icon }) => (
          <button
            key={id}
            onClick={() => setActiveTab(id)}
            className={`flex items-center gap-2 px-4 py-2 text-sm font-medium transition border-b-2 ${
              activeTab === id
                ? 'border-blue-500 text-blue-400 bg-gray-700/50'
                : 'border-transparent text-gray-400 hover:text-gray-300'
            }`}
          >
            <Icon className="w-4 h-4" />
            {label}
          </button>
        ))}
      </div>

      {/* Tab Content */}
      <div className="p-4 max-h-80 overflow-y-auto font-mono text-sm">
        {/* Output Tab */}
        {activeTab === 'output' && (
          <div>
            {output ? (
              <div className="bg-gray-950 p-3 rounded border border-gray-700 whitespace-pre-wrap text-gray-100 break-words text-xs leading-relaxed">
                {output}
              </div>
            ) : (
              <div className="text-gray-500 text-xs">No output</div>
            )}
          </div>
        )}

        {/* Tests Tab */}
        {activeTab === 'tests' && (
          <div className="space-y-3">
            {test_results && test_results.length > 0 ? (
              test_results.map((result, idx) => (
                <div
                  key={idx}
                  className={`p-3 rounded border ${
                    result.passed
                      ? 'border-green-700/50 bg-green-900/20'
                      : 'border-red-700/50 bg-red-900/20'
                  }`}
                >
                  <div className="flex items-center gap-2 mb-2">
                    {result.passed ? (
                      <CheckCircle className="w-4 h-4 text-green-400" />
                    ) : (
                      <XCircle className="w-4 h-4 text-red-400" />
                    )}
                    <span className={result.passed ? 'text-green-400' : 'text-red-400'}>
                      Test {idx + 1} {result.passed ? 'PASSED' : 'FAILED'}
                    </span>
                  </div>

                  {result.input && (
                    <div className="text-xs text-gray-300 ml-6 mb-1">
                      <span className="text-gray-500">Input:</span> {result.input}
                    </div>
                  )}

                  <div className="text-xs text-gray-300 ml-6 mb-1">
                    <span className="text-gray-500">Expected:</span>
                    <div className="text-green-300 mt-1 break-words">
                      {result.expected}
                    </div>
                  </div>

                  {!result.passed && (
                    <div className="text-xs text-gray-300 ml-6">
                      <span className="text-gray-500">Got:</span>
                      <div className="text-red-300 mt-1 break-words">
                        {result.actual}
                      </div>
                    </div>
                  )}
                </div>
              ))
            ) : (
              <div className="text-gray-500 text-xs">No test results</div>
            )}
          </div>
        )}

        {/* Errors Tab */}
        {activeTab === 'errors' && error && (
          <div className="bg-red-950/40 border border-red-700/50 rounded p-3 text-red-300 text-xs whitespace-pre-wrap break-words leading-relaxed">
            {error}
          </div>
        )}

        {/* Debug Info Tab */}
        {activeTab === 'debug' && (
          <div className="space-y-2 text-xs text-gray-300">
            <div className="grid grid-cols-2 gap-2">
              <div className="bg-gray-800/50 p-2 rounded border border-gray-700">
                <div className="text-gray-500 text-xs mb-1">Status</div>
                <div className={getStatusColor(status)}>{status}</div>
              </div>
              <div className="bg-gray-800/50 p-2 rounded border border-gray-700">
                <div className="text-gray-500 text-xs mb-1">Execution Time</div>
                <div>{execution_time?.toFixed(3) || '0.000'}s</div>
              </div>
              <div className="bg-gray-800/50 p-2 rounded border border-gray-700">
                <div className="text-gray-500 text-xs mb-1">Tests Passed</div>
                <div>
                  {passed}/{total}
                </div>
              </div>
              <div className="bg-gray-800/50 p-2 rounded border border-gray-700">
                <div className="text-gray-500 text-xs mb-1">Pass Rate</div>
                <div>{total > 0 ? ((passed / total) * 100).toFixed(0) : 0}%</div>
              </div>
            </div>

            {output && (
              <div className="bg-gray-800/50 p-2 rounded border border-gray-700 mt-3">
                <div className="text-gray-500 text-xs mb-1">Output Length</div>
                <div>{output.length} characters</div>
              </div>
            )}
          </div>
        )}

        {loading && (
          <div className="text-center text-gray-400 py-4">
            <div className="inline-block animate-spin text-lg">⏳</div>
            <div className="mt-2">Executing code...</div>
          </div>
        )}
      </div>
    </div>
  )
}


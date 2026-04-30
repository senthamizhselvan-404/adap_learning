import React, { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { ChevronLeft, Play, RotateCcw, Code2, Eye } from 'lucide-react'
import { practiceAPI } from '../api/client'
import ExecutionOutput from '../components/ExecutionOutput'

const TEMPLATES = {
  python: `# Python
print("Hello, World!")

# Try more:
name = "EALPS"
for i in range(3):
    print(f"Loop {i}: Hello from {name}!")`,

  javascript: `// JavaScript
console.log("Hello, World!");

// Try more:
const name = "EALPS";
[1, 2, 3].forEach(i => console.log(\`Loop \${i}: Hello from \${name}!\`));`,

  html: `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>My Page</title>
  <style>
    body { font-family: Arial, sans-serif; background: #f0f4ff; padding: 2rem; }
    h1   { color: #3b82f6; }
    p    { color: #374151; }
    .card {
      background: white;
      border-radius: 8px;
      padding: 1rem;
      box-shadow: 0 2px 8px rgba(0,0,0,.1);
      margin-top: 1rem;
    }
  </style>
</head>
<body>
  <h1>Hello, World!</h1>
  <p>Edit this HTML and click <strong>Preview</strong> to see it rendered.</p>
  <div class="card">
    <h2>Card Component</h2>
    <p>This is a styled card.</p>
  </div>
</body>
</html>`,

  css: `/* CSS — click Preview to see styles on a sample page */
body {
  font-family: Arial, sans-serif;
  background: #1e293b;
  color: #f1f5f9;
  padding: 2rem;
}

h1 {
  color: #3b82f6;
  font-size: 2rem;
  margin-bottom: 0.5rem;
}

p {
  color: #94a3b8;
  line-height: 1.6;
}

.card {
  background: #334155;
  border-radius: 8px;
  padding: 1rem 1.5rem;
  margin-top: 1rem;
  border-left: 4px solid #3b82f6;
}

button {
  background: #3b82f6;
  color: white;
  border: none;
  padding: 0.5rem 1.2rem;
  border-radius: 6px;
  cursor: pointer;
  margin-top: 1rem;
}`,
}

const CSS_PREVIEW_WRAPPER = (css) => `<!DOCTYPE html>
<html><head><style>${css}</style></head>
<body>
  <h1>Heading</h1>
  <p>Paragraph text here.</p>
  <div class="card">A <code>.card</code> element</div>
  <button>A button</button>
</body></html>`

const TIPS = {
  python:     'Use print() for output',
  javascript: 'Use console.log() for output',
  html:       'Click Preview to render your HTML page',
  css:        'Click Preview to see styles applied to a sample page',
}

export default function IDE() {
  const navigate = useNavigate()

  const [code, setCode] = useState(TEMPLATES.python)
  const [language, setLanguage] = useState('python')
  const [loading, setLoading] = useState(false)
  const [executionResult, setExecutionResult] = useState(null)
  const [error, setError] = useState(null)
  const [previewKey, setPreviewKey] = useState(0)

  const isMarkup = language === 'html' || language === 'css'

  const handleExecute = async (codeToRun, lang) => {
    try {
      setLoading(true)
      setError(null)
      const { data } = await practiceAPI.executeCode(codeToRun, lang)
      setExecutionResult(data)
      setPreviewKey(k => k + 1)
    } catch (err) {
      setError(err.response?.data?.error || 'Execution failed: ' + err.message)
    } finally {
      setLoading(false)
    }
  }

  const handleReset = () => {
    setCode(TEMPLATES[language] || '')
    setExecutionResult(null)
    setError(null)
  }

  const handleLanguageChange = (e) => {
    const lang = e.target.value
    setLanguage(lang)
    setCode(TEMPLATES[lang] || '')
    setExecutionResult(null)
    setError(null)
  }

  return (
    <div className="min-h-screen bg-gray-950 text-white">
      {/* Header */}
      <div className="bg-gray-900 border-b border-gray-800 p-4 sticky top-0 z-10">
        <div className="max-w-7xl mx-auto">
          <div className="flex items-center justify-between mb-3">
            <button
              onClick={() => navigate('/dashboard')}
              className="flex items-center gap-2 text-blue-400 hover:text-blue-300"
            >
              <ChevronLeft className="w-5 h-5" />
              Back to Dashboard
            </button>
          </div>
          <div className="flex items-center gap-3">
            <Code2 className="w-8 h-8 text-blue-400" />
            <div>
              <h1 className="text-3xl font-bold">Code IDE</h1>
              <p className="text-gray-400 text-sm">Execute code and see output in real-time</p>
            </div>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto p-4">
        {error && (
          <div className="mb-4 p-4 bg-red-900/20 border border-red-700 rounded text-red-300 text-sm">
            {error}
          </div>
        )}

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
          {/* ── Editor Panel ── */}
          <div className="lg:col-span-2 space-y-3">
            {/* Controls */}
            <div className="bg-gray-800 rounded-lg border border-gray-700 p-4">
              <div className="flex items-center justify-between gap-4">
                <div className="flex items-center gap-3">
                  <label className="text-sm text-gray-300 font-medium">Language:</label>
                  <select
                    value={language}
                    onChange={handleLanguageChange}
                    className="px-4 py-2 bg-gray-700 text-white text-sm rounded-lg border border-gray-600 focus:outline-none focus:border-blue-500 font-medium"
                  >
                    <option value="python">Python</option>
                    <option value="javascript">JavaScript</option>
                    <option value="html">HTML</option>
                    <option value="css">CSS</option>
                  </select>
                </div>

                <div className="flex items-center gap-2">
                  <button
                    onClick={handleReset}
                    disabled={loading}
                    className="flex items-center gap-2 px-4 py-2 bg-gray-700 hover:bg-gray-600 text-white text-sm rounded-lg disabled:opacity-50 transition font-medium"
                  >
                    <RotateCcw className="w-4 h-4" />
                    Reset
                  </button>

                  <button
                    onClick={() => handleExecute(code, language)}
                    disabled={loading}
                    className="flex items-center gap-2 px-4 py-2 bg-green-600 hover:bg-green-700 text-white text-sm rounded-lg disabled:opacity-50 transition font-medium"
                  >
                    {loading
                      ? <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                      : <Play className="w-4 h-4" />
                    }
                    {loading ? 'Running...' : isMarkup ? 'Preview' : 'Execute'}
                  </button>
                </div>
              </div>
            </div>

            {/* Code textarea */}
            <div className="bg-gray-900 rounded-lg border border-gray-700 overflow-hidden">
              <textarea
                value={code}
                onChange={(e) => setCode(e.target.value)}
                placeholder="Write your code here..."
                className="w-full h-96 bg-gray-950 text-white p-4 font-mono text-sm focus:outline-none border-none resize-none"
                spellCheck="false"
              />
            </div>

            {/* Info cards */}
            <div className="grid grid-cols-3 gap-3">
              <div className="bg-blue-900/20 border border-blue-700/50 rounded-lg p-3">
                <div className="text-xs text-blue-400 font-bold mb-1">REAL-TIME</div>
                <div className="text-xs text-blue-300">Execute & see output instantly</div>
              </div>
              <div className="bg-green-900/20 border border-green-700/50 rounded-lg p-3">
                <div className="text-xs text-green-400 font-bold mb-1">4 LANGUAGES</div>
                <div className="text-xs text-green-300">Python · JavaScript · HTML · CSS</div>
              </div>
              <div className="bg-purple-900/20 border border-purple-700/50 rounded-lg p-3">
                <div className="text-xs text-purple-400 font-bold mb-1">LIVE PREVIEW</div>
                <div className="text-xs text-purple-300">HTML & CSS render in the browser</div>
              </div>
            </div>
          </div>

          {/* ── Output Panel ── */}
          <div className="lg:col-span-1">
            <div className="sticky top-24 space-y-3">

              {/* HTML preview */}
              {language === 'html' && (
                <div className="bg-gray-800 rounded-lg border border-gray-700 p-3">
                  <div className="flex items-center gap-2 mb-2">
                    <Eye className="w-4 h-4 text-blue-400" />
                    <h2 className="font-bold text-sm">HTML Preview</h2>
                  </div>
                  {executionResult ? (
                    <iframe
                      key={previewKey}
                      srcDoc={executionResult.output}
                      className="w-full rounded border border-gray-600 bg-white"
                      style={{ height: 300 }}
                      title="HTML Preview"
                      sandbox="allow-scripts allow-same-origin"
                    />
                  ) : (
                    <div className="flex items-center justify-center border border-dashed border-gray-600 rounded text-gray-500 text-sm" style={{ height: 300 }}>
                      {loading ? 'Rendering…' : 'Click Preview to render'}
                    </div>
                  )}
                </div>
              )}

              {/* CSS preview */}
              {language === 'css' && (
                <div className="bg-gray-800 rounded-lg border border-gray-700 p-3">
                  <div className="flex items-center gap-2 mb-2">
                    <Eye className="w-4 h-4 text-pink-400" />
                    <h2 className="font-bold text-sm">CSS Preview</h2>
                  </div>
                  {executionResult ? (
                    <iframe
                      key={previewKey}
                      srcDoc={CSS_PREVIEW_WRAPPER(executionResult.output)}
                      className="w-full rounded border border-gray-600 bg-white"
                      style={{ height: 260 }}
                      title="CSS Preview"
                      sandbox="allow-same-origin"
                    />
                  ) : (
                    <div className="flex items-center justify-center border border-dashed border-gray-600 rounded text-gray-500 text-sm" style={{ height: 260 }}>
                      {loading ? 'Rendering…' : 'Click Preview to see styles'}
                    </div>
                  )}
                </div>
              )}

              {/* Output (non-markup languages) */}
              {!isMarkup && (
                <div className="bg-gray-800 rounded-lg border border-gray-700 p-3">
                  <h2 className="font-bold text-lg mb-2">Output</h2>
                  <ExecutionOutput result={executionResult} loading={loading} />
                </div>
              )}

              {/* Quick tip */}
              <div className="bg-gray-800 rounded-lg border border-gray-700 p-4">
                <h3 className="font-bold text-sm mb-2">Quick Tip</h3>
                <p className="text-xs text-gray-400">{TIPS[language]}</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

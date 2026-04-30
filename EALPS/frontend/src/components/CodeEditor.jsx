import React, { useEffect, useState } from 'react'
import { Play, Save, RotateCcw } from 'lucide-react'

export default function CodeEditor({
  code,
  setCode,
  language,
  onExecute,
  onSubmit,
  loading,
  problem,
}) {
  const [editorReady, setEditorReady] = useState(false)
  const monacoEditorLoading = typeof window !== 'undefined' && !window.monaco

  // Simple code editor (Monaco will be loaded as a library)
  useEffect(() => {
    if (typeof window !== 'undefined') {
      const script = document.createElement('script')
      script.src =
        'https://cdnjs.cloudflare.com/ajax/libs/monaco-editor/0.50.0/min/vs/loader.min.js'
      script.async = true
      script.onload = () => {
        window.require.config({
          paths: {
            vs: 'https://cdnjs.cloudflare.com/ajax/libs/monaco-editor/0.50.0/min/vs',
          },
        })
        window.require(['vs/editor/editor.main'], () => {
          setEditorReady(true)
        })
      }
      document.head.appendChild(script)
    }
  }, [])

  // Create Monaco editor instance
  useEffect(() => {
    if (editorReady && window.monaco && !window._editorInstance) {
      const editor = window.monaco.editor.create(
        document.getElementById('monaco-editor'),
        {
          value: code,
          language: language === 'javascript' ? 'javascript' : language,
          theme: 'vs-dark',
          automaticLayout: true,
          minimap: { enabled: false },
          fontSize: 14,
          tabSize: 2,
          lineNumbers: 'on',
        }
      )

      editor.onDidChangeModelContent(() => {
        setCode(editor.getValue())
      })

      window._editorInstance = editor
    }

    return () => {
      if (window._editorInstance) {
        window._editorInstance.dispose()
        window._editorInstance = null
      }
    }
  }, [editorReady, language])

  const handleLanguageChange = (e) => {
    const newLang = e.target.value
    if (window._editorInstance && window.monaco) {
      window.monaco.editor.setModelLanguage(
        window._editorInstance.getModel(),
        newLang === 'javascript' ? 'javascript' : newLang
      )
    }
  }

  const handleReset = () => {
    if (window._editorInstance) {
      window._editorInstance.setValue('')
      setCode('')
    }
  }

  return (
    <div className="flex flex-col gap-3">
      {/* Toolbar */}
      <div className="flex items-center justify-between bg-gray-800 p-3 rounded-lg border border-gray-700">
        <div className="flex items-center gap-3">
          <label className="text-sm text-gray-300">Language:</label>
          <select
            value={language}
            onChange={handleLanguageChange}
            className="px-3 py-1 bg-gray-700 text-white text-sm rounded border border-gray-600 focus:outline-none focus:border-blue-500"
          >
            {problem?.languages_supported?.map((lang) => (
              <option key={lang} value={lang}>
                {lang.charAt(0).toUpperCase() + lang.slice(1)}
              </option>
            ))}
          </select>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={handleReset}
            disabled={loading}
            className="flex items-center gap-2 px-3 py-1 bg-gray-700 hover:bg-gray-600 text-white text-sm rounded disabled:opacity-50 transition"
            title="Reset code"
          >
            <RotateCcw className="w-4 h-4" />
            Reset
          </button>

          <button
            onClick={() => onExecute(code, language)}
            disabled={loading}
            className="flex items-center gap-2 px-3 py-1 bg-blue-600 hover:bg-blue-700 text-white text-sm rounded disabled:opacity-50 transition"
            title="Run code (won't save)"
          >
            <Play className="w-4 h-4" />
            {loading ? 'Running...' : 'Run'}
          </button>

          <button
            onClick={() => onSubmit(code, language)}
            disabled={loading}
            className="flex items-center gap-2 px-3 py-1 bg-green-600 hover:bg-green-700 text-white text-sm rounded disabled:opacity-50 transition"
            title="Submit solution"
          >
            <Save className="w-4 h-4" />
            {loading ? 'Submitting...' : 'Submit'}
          </button>
        </div>
      </div>

      {/* Editor Container */}
      <div
        id="monaco-editor"
        className="w-full h-96 border border-gray-700 rounded-lg bg-gray-900"
      />

      {!editorReady && (
        <div className="h-96 flex items-center justify-center bg-gray-900 rounded-lg border border-gray-700 text-gray-400">
          Loading editor...
        </div>
      )}
    </div>
  )
}

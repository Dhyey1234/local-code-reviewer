
import { useState } from 'react';

type Language = 'python' | 'javascript' | 'typescript' | 'java' | 'cpp' | 'csharp';
type Finding = { issue: string; line?: number; message: string };
type Result = {
  review_id: string;
  language?: Language;
  findings: Finding[];
  style_findings?: Finding[];
  ai_review: string;
  warnings: string[];
};

const languages: { id: Language; name: string; ext: string; example: string }[] = [
  {
    id: 'python',
    name: 'Python',
    ext: 'py',
    example: 'def first_item(items):\n    return items[0]\n',
  },
  {
    id: 'javascript',
    name: 'JavaScript',
    ext: 'js',
    example: 'function divide(a, b) {\n  return a / b;\n}\n',
  },
  {
    id: 'typescript',
    name: 'TypeScript',
    ext: 'ts',
    example: 'function divide(a: number, b: number): number {\n  return a / b;\n}\n',
  },
  {
    id: 'java',
    name: 'Java',
    ext: 'java',
    example: 'class Main {\n  static int divide(int a, int b) {\n    return a / b;\n  }\n}\n',
  },
  {
    id: 'cpp',
    name: 'C++',
    ext: 'cpp',
    example: 'int divide(int a, int b) {\n  return a / b;\n}\n',
  },
  {
    id: 'csharp',
    name: 'C#',
    ext: 'cs',
    example: 'class Program {\n  static int Divide(int a, int b) {\n    return a / b;\n  }\n}\n',
  },
];

// Conservative local detection. Ambiguous snippets keep the current selection.
function detectLanguage(source: string): Language | null {
  const rules: [Language, RegExp[]][] = [
    ['python', [/^\s*(?:def|async def)\s+\w+\s*\(/m, /^\s*(?:from\s+\w+\s+import|import\s+\w+)/m, /^\s*class\s+\w+\s*:/m]],
    ['typescript', [/\b(?:interface|type)\s+\w+\s*[={]/, /\b(?:const|let)\s+\w+\s*:\s*(?:number|string|boolean)/, /\)\s*:\s*(?:number|string|boolean)\s*\{/]],
    ['java', [/\bpublic\s+(?:static\s+)?class\s+\w+/, /\bSystem\.out\./, /\bpublic\s+static\s+void\s+main\s*\(/]],
    ['cpp', [/#include\s*[<"]/, /\bstd::/, /\busing\s+namespace\s+std\b/, /\bvector\s*</]],
    ['csharp', [/\busing\s+System\s*;/, /\bConsole\.Write(?:Line)?\s*\(/, /\bstatic\s+void\s+Main\s*\(/]],
    ['javascript', [/\b(?:const|let|var)\s+\w+\s*=/, /\bconsole\.log\s*\(/, /\bfunction\s+\w+\s*\(/]],
  ];
  if (/\b(?:const|let)\s+\w+\s*:\s*(?:number|string|boolean)/.test(source)) return 'typescript';
  const scores = rules.map(([id, patterns]) => ({ id, score: patterns.filter(pattern => pattern.test(source)).length }));
  const highest = Math.max(...scores.map(item => item.score));
  const winners = scores.filter(item => item.score === highest);
  if (!highest || winners.length !== 1) return null;
  return winners[0].id;
}

export default function App() {
  const [language, setLanguage] = useState<Language>('python');
  const [autoDetect, setAutoDetect] = useState(true);
  const [code, setCode] = useState(languages[0].example);
  const [useAi, setUseAi] = useState(true);
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<Result | null>(null);
  const [error, setError] = useState('');
  const [correction, setCorrection] = useState('');
  const [feedbackStatus, setFeedbackStatus] = useState('');
  const [feedbackBusy, setFeedbackBusy] = useState(false);
  const [feedbackSent, setFeedbackSent] = useState(false);

  const selectedLanguage = languages.find(item => item.id === language)!;

  function changeLanguage(value: Language) {
    setAutoDetect(false);
    setLanguage(value);
    setCode(languages.find(item => item.id === value)!.example);
    setResult(null);
    setError('');
    setCorrection('');
    setFeedbackStatus('');
    setFeedbackSent(false);
  }

  async function review() {
    setBusy(true);
    setError('');
    setResult(null);
    setCorrection('');
    setFeedbackStatus('');
    setFeedbackSent(false);

    try {
      const response = await fetch('/api/review/jobs', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ code, language, use_ai: useAi }),
      });
      if (!response.ok) {
        throw new Error(`Review could not start (HTTP ${response.status})`);
      }
      const { job_id } = await response.json() as { job_id: string };
      let completed = false;
      for (let attempt = 0; attempt < 600; attempt++) {
        await new Promise(resolve => setTimeout(resolve, 1000));
        const statusResponse = await fetch(`/api/review/jobs/${encodeURIComponent(job_id)}`);
        if (!statusResponse.ok) {
          throw new Error(`Could not retrieve review status (HTTP ${statusResponse.status})`);
        }
        const job = await statusResponse.json() as {
          status: 'queued' | 'running' | 'completed' | 'failed';
          result: Result | null;
          error: string | null;
        };
        if (job.status === 'failed') throw new Error(job.error || 'Review failed');
        if (job.status === 'completed') {
          if (!job.result) throw new Error('Review completed without results');
          setResult(job.result);
          completed = true;
          break;
        }
      }
      if (!completed) throw new Error('Review is taking too long. Please try again.');
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Review failed');
    } finally {
      setBusy(false);
    }
  }

  async function feedback(verdict: 'correct' | 'incorrect') {
    if (!result || feedbackBusy || feedbackSent) return;

    setFeedbackBusy(true);
    setFeedbackStatus('Saving feedback…');

    try {
      const response = await fetch('/api/feedback', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          review_id: result.review_id,
          verdict,
          correction,
        }),
      });

      if (!response.ok) throw new Error(`HTTP ${response.status}`);

      setFeedbackSent(true);
      setFeedbackStatus(
        'Feedback saved locally. It is not used for training automatically.'
      );
    } catch (e) {
      setFeedbackStatus(`Could not save feedback: ${String(e)}`);
    } finally {
      setFeedbackBusy(false);
    }
  }

  return (
    <div className="app-shell">
      <header className="topbar">
        <a className="wordmark" href="/" aria-label="CodeLens home">
          code<span>lens</span><span className="wordmark-mark">/</span>
        </a>
        <div className="topbar-right">
          <span className="topbar-label">CODE REVIEW WORKSPACE</span>
          <span className="topbar-separator" />
          <span className="local-status">
            <span className="status-square" />
            LOCAL PROCESSING
          </span>
        </div>
      </header>

      <main className="main-content">
        <section className="intro" aria-labelledby="page-title">
          <div className="intro-index">01 / REVIEW</div>
          <div className="intro-main">
            <h1 id="page-title">Find the issue.<br />Understand the fix.</h1>
            <p>
              Review code using local analysis and a model running on your machine.
              No hosted AI service required.
            </p>
          </div>
          <div className="intro-meta">
            <span>LANGUAGE</span>
            <strong>{selectedLanguage.name}</strong>
            <span>ENGINE</span>
            <strong>{language === 'python' ? 'AST + Local Qwen' : 'Static checks + Local Qwen'}</strong>
          </div>
        </section>

        <section className="workspace" aria-label="Code review workspace">
          <div className="editor-column">
            <div className="section-bar">
              <div>
                <span className="section-number">01</span>
                <h2>Source code</h2>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <label style={{ fontSize: 12, whiteSpace: 'nowrap' }}>
                <input type="checkbox" checked={autoDetect} onChange={e => {
                  setAutoDetect(e.target.checked);
                  if (e.target.checked) {
                    const detected = detectLanguage(code);
                    if (detected) setLanguage(detected);
                  }
                }} /> Auto-detect
              </label>
              <select
                className="language-select"
                aria-label="Programming language"
                value={language}
                onChange={e => changeLanguage(e.target.value as Language)}
                disabled={busy}
                style={{
                  background: '#faf9f6',
                  color: '#111',
                  border: '1px solid #e5e5e5',
                  borderRadius: 0,
                  padding: '8px 12px',
                  font: 'inherit',
                  cursor: 'pointer',
                }}
              >
                {languages.map(item => (
                  <option key={item.id} value={item.id}>
                    {item.name}
                  </option>
                ))}
              </select>
              </div>
            </div>

            <div className="editor-frame">
              <div className="editor-toolbar">
                <span className="file-tab">
                  <span className="file-square" />
                  untitled.{selectedLanguage.ext}
                </span>
                <span className="editor-detail">
                  UTF-8 <span className="editor-detail-divider">/</span>
                  {' '}{selectedLanguage.ext.toUpperCase()}
                </span>
              </div>

              <div className="code-editor-wrap">
                <div className="line-numbers" aria-hidden="true">
                  {code.split('\n').map((_, index) => (
                    <span key={index}>{index + 1}</span>
                  ))}
                </div>
                <textarea
                  aria-label={`${selectedLanguage.name} code`}
                  spellCheck={false}
                  autoCapitalize="off"
                  autoCorrect="off"
                  value={code}
                  onChange={e => {
                    const next = e.target.value;
                    setCode(next);
                    if (autoDetect) {
                      const detected = detectLanguage(next);
                      if (detected) setLanguage(detected);
                    }
                    setResult(null);
                  }}
                />
              </div>

              <div className="editor-footer">
                <label className="ai-toggle">
                  <input
                    type="checkbox"
                    checked={useAi}
                    onChange={e => setUseAi(e.target.checked)}
                  />
                  <span>Include local AI review</span>
                </label>
                <span className="line-count">
                  {code.split('\n').length} LINES
                </span>
              </div>
            </div>

            <div className="editor-actions">
              <p>Code stays on your machine.</p>
              <button
                className="primary-button"
                onClick={review}
                disabled={busy || !code.trim()}
              >
                {busy ? 'Reviewing code…' : 'Run review'}
                <span aria-hidden="true">↗</span>
              </button>
            </div>
          </div>

          <div className="results-column" aria-live="polite">
            <div className="section-bar">
              <div>
                <span className="section-number">02</span>
                <h2>Analysis</h2>
              </div>
              <span className="section-note">REVIEW / OUTPUT</span>
            </div>

            <div className="results-content">
              {busy && (
                <div className="state-panel">
                  <span className="state-index">PROCESSING / 01</span>
                  <h3>Review in progress</h3>
                  <p>Checking your code and preparing the review.</p>
                  <div className="progress-rule" />
                </div>
              )}

              {!busy && !result && !error && (
                <div className="state-panel">
                  <span className="state-index">READY / 00</span>
                  <h3>Your review starts here.</h3>
                  <p>
                    Select a programming language, enter your code,
                    and run the review.
                  </p>
                  <button
                    className="text-action"
                    onClick={review}
                    disabled={!code.trim()}
                  >
                    Review the example <span aria-hidden="true">↗</span>
                  </button>
                  <div className="state-steps">
                    <span>01 &nbsp; Select language</span>
                    <span>02 &nbsp; Run review</span>
                    <span>03 &nbsp; Inspect findings</span>
                  </div>
                </div>
              )}

              {!busy && error && (
                <div className="state-panel error-state" role="alert">
                  <span className="state-index">REQUEST / FAILED</span>
                  <h3>Review couldn't finish.</h3>
                  <p>{error}. Check that FastAPI is running.</p>
                  <button className="outline-button" onClick={review}>
                    Try again
                  </button>
                </div>
              )}

              {!busy && result && (
                <>
                  <div className="result-overview">
                    <div>
                      <span className="overline">REVIEW STATUS</span>
                      <h3>Analysis complete</h3>
                    </div>
                    <div className="result-counts">
                      <div>
                        <strong>{String(result.findings.length).padStart(2, '0')}</strong>
                        <span>FINDINGS</span>
                      </div>
                      <div>
                        <strong>{String(result.warnings.length).padStart(2, '0')}</strong>
                        <span>WARNINGS</span>
                      </div>
                    </div>
                  </div>

                  <div className="result-section">
                    <div className="result-heading">
                      <h4>Static findings</h4>
                      <span>{String(result.findings.length).padStart(2, '0')}</span>
                    </div>

                    {result.findings.length === 0 ? (
                      <div className="clean-state">
                        <strong>
                          No patterns flagged
                        </strong>
                        <p>
                          No issue matched the available static checks. This does not guarantee bug-free code.
                        </p>
                        <button
                          className="text-action"
                          onClick={() => setResult(null)}
                        >
                          Review another snippet <span aria-hidden="true">↗</span>
                        </button>
                      </div>
                    ) : (
                      <div className="findings-list">
                        {result.findings.map((finding, i) => (
                          <article className="finding-row" key={i}>
                            <div className="finding-top">
                              <strong>{finding.issue}</strong>
                              {finding.line != null && (
                                <span>LINE {finding.line}</span>
                              )}
                            </div>
                            <p>{finding.message}</p>
                          </article>
                        ))}
                      </div>
                    )}
                  </div>

                  {result.language === 'python' && (
                    <div className="result-section">
                      <div className="result-heading">
                        <h4>PEP 8 style checks</h4>
                        <span>{String(result.style_findings?.length ?? 0).padStart(2, '0')}</span>
                      </div>
                      {(result.style_findings?.length ?? 0) === 0 ? (
                        <div className="clean-state">
                          <strong>No style violations reported</strong>
                          <p>Only the enabled pycodestyle rules are checked. See warnings if the checker is unavailable.</p>
                        </div>
                      ) : (
                        <div className="findings-list">
                          {result.style_findings!.map((finding, i) => (
                            <article className="finding-row" key={i}>
                              <div className="finding-top"><strong>{finding.issue}</strong>
                                {finding.line != null && <span>LINE {finding.line}</span>}
                              </div>
                              <p>{finding.message}</p>
                            </article>
                          ))}
                        </div>
                      )}
                    </div>
                  )}

                  <div className="result-section">
                    <div className="result-heading">
                      <h4>Local AI review</h4>
                      <span>{result.ai_review ? 'REVIEW' : 'OFF'}</span>
                    </div>
                    <pre className="ai-output">{result.ai_review}</pre>
                  </div>

                  {result.warnings.length > 0 && (
                    <div className="result-section">
                      <div className="result-heading">
                        <h4>Validation warnings</h4>
                        <span>{result.warnings.length}</span>
                      </div>
                      {result.warnings.map((warning, i) => (
                        <p className="validation-warning" key={i}>
                          {warning}
                        </p>
                      ))}
                    </div>
                  )}

                  <div className="feedback-section">
                    <div className="result-heading">
                      <h4>Review feedback</h4>
                      <span>OPTIONAL</span>
                    </div>
                    <p>
                      Was this review useful? Feedback is saved locally
                      for later evaluation.
                    </p>
                    <label htmlFor="feedback-note" className="input-label">
                      Correction or context
                    </label>
                    <textarea
                      id="feedback-note"
                      className="feedback-input"
                      placeholder="What should the review have said?"
                      value={correction}
                      onChange={e => setCorrection(e.target.value)}
                      disabled={feedbackSent}
                    />
                    <div className="feedback-actions">
                      <button
                        className="outline-button"
                        onClick={() => feedback('correct')}
                        disabled={feedbackBusy || feedbackSent}
                      >
                        Accurate
                      </button>
                      <button
                        className="outline-button"
                        onClick={() => feedback('incorrect')}
                        disabled={feedbackBusy || feedbackSent}
                      >
                        Needs work
                      </button>
                    </div>
                    {feedbackStatus && (
                      <p className="feedback-message" role="status">
                        {feedbackStatus}
                      </p>
                    )}
                  </div>
                </>
              )}
            </div>
          </div>
        </section>
      </main>

      <footer className="footer">
        <span>CODELENS / LOCAL CODE REVIEW</span>
        <span>PYTHON AST · QWEN VIA MLX · LOCAL FEEDBACK</span>
      </footer>
    </div>
  );
}

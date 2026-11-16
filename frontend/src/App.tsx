import { useState } from 'react';

type Finding = { issue: string; line?: number; message: string };
type Result = { review_id: string; findings: Finding[]; ai_review: string; warnings: string[] };
const initial = `def first_item(items):\n    return items[0]\n`;

export default function App() {
  const [code, setCode] = useState(initial);
  const [useAi, setUseAi] = useState(true);
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<Result | null>(null);
  const [error, setError] = useState('');
  const [correction, setCorrection] = useState('');
  const [feedbackStatus, setFeedbackStatus] = useState('');
  const [feedbackBusy, setFeedbackBusy] = useState(false);
  const [feedbackSent, setFeedbackSent] = useState(false);

  async function review() {
    setBusy(true);
    setError('');
    setResult(null);
    setCorrection('');
    setFeedbackStatus('');
    setFeedbackSent(false);
    try {
      const response = await fetch('/api/review', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ code, use_ai: useAi }),
      });
      if (!response.ok) throw new Error(`Review failed (HTTP ${response.status})`);
      setResult(await response.json() as Result);
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
        body: JSON.stringify({ review_id: result.review_id, verdict, correction }),
      });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      setFeedbackSent(true);
      setFeedbackStatus('Feedback saved on this device. It is not used for training automatically.');
    } catch (e) {
      setFeedbackStatus(`Could not save feedback: ${String(e)}`);
    } finally {
      setFeedbackBusy(false);
    }
  }

  return (
    <div className="app-shell">
      <header className="topbar">
        <a className="wordmark" href="/" aria-label="CodeLens home">code<span>lens</span><span className="wordmark-mark">/</span></a>
        <div className="topbar-right"><span className="topbar-label">CODE REVIEW WORKSPACE</span><span className="topbar-separator" /><span className="local-status"><span className="status-square" />LOCAL PROCESSING</span></div>
      </header>

      <main className="main-content">
        <section className="intro" aria-labelledby="page-title">
          <div className="intro-index">01 / REVIEW</div>
          <div className="intro-main"><h1 id="page-title">Find the issue.<br />Understand the fix.</h1><p>Review Python code with static analysis and a model running on your machine. Nothing is sent to a hosted AI service.</p></div>
          <div className="intro-meta"><span>LANGUAGE</span><strong>Python 3</strong><span>ENGINE</span><strong>AST + Local Qwen</strong></div>
        </section>

        <section className="workspace" aria-label="Code review workspace">
          <div className="editor-column">
            <div className="section-bar"><div><span className="section-number">01</span><h2>Source code</h2></div><span className="section-note">PYTHON / EDITOR</span></div>
            <div className="editor-frame">
              <div className="editor-toolbar"><span className="file-tab"><span className="file-square" />untitled.py</span><span className="editor-detail">UTF-8 <span className="editor-detail-divider">/</span> PY</span></div>
              <div className="code-editor-wrap"><div className="line-numbers" aria-hidden="true">{code.split('\n').map((_, index) => <span key={index}>{index + 1}</span>)}</div><textarea aria-label="Python code" spellCheck={false} autoCapitalize="off" autoCorrect="off" value={code} onChange={e => setCode(e.target.value)} /></div>
              <div className="editor-footer"><label className="ai-toggle"><input type="checkbox" checked={useAi} onChange={e => setUseAi(e.target.checked)} /><span>Include local AI review</span></label><span className="line-count">{code.split('\n').length} LINES</span></div>
            </div>
            <div className="editor-actions"><p>Code stays on your machine.</p><button className="primary-button" onClick={review} disabled={busy || !code.trim()}>{busy ? 'Reviewing code…' : 'Run review'}<span aria-hidden="true">↗</span></button></div>
          </div>

          <div className="results-column" aria-live="polite">
            <div className="section-bar"><div><span className="section-number">02</span><h2>Analysis</h2></div><span className="section-note">REVIEW / OUTPUT</span></div>
            <div className="results-content">
              {busy && <div className="state-panel"><span className="state-index">PROCESSING / 01</span><h3>Review in progress</h3><p>Checking the code and preparing your review. Local model analysis can take a moment.</p><div className="progress-rule" /></div>}
              {!busy && !result && !error && <div className="state-panel"><span className="state-index">READY / 00</span><h3>Your review starts here.</h3><p>Edit the Python code, choose whether to include local AI analysis, then run the review.</p><button className="text-action" onClick={review} disabled={!code.trim()}>Review the example <span aria-hidden="true">↗</span></button><div className="state-steps"><span>01 &nbsp; Write code</span><span>02 &nbsp; Run review</span><span>03 &nbsp; Inspect findings</span></div></div>}
              {!busy && error && <div className="state-panel error-state" role="alert"><span className="state-index">REQUEST / FAILED</span><h3>Review couldn't finish.</h3><p>{error}. Check that FastAPI is running at 127.0.0.1:8000, then try again.</p><button className="outline-button" onClick={review}>Try again</button></div>}
              {!busy && result && <>
                <div className="result-overview"><div><span className="overline">REVIEW STATUS</span><h3>Analysis complete</h3></div><div className="result-counts"><div><strong>{result.findings.length.toString().padStart(2, '0')}</strong><span>FINDINGS</span></div><div><strong>{result.warnings.length.toString().padStart(2, '0')}</strong><span>WARNINGS</span></div></div></div>
                <div className="result-section"><div className="result-heading"><h4>Static findings</h4><span>{result.findings.length.toString().padStart(2, '0')}</span></div>{result.findings.length === 0 ? <div className="clean-state"><strong>No patterns flagged</strong><p>The static analyzer didn't identify a matching issue. This doesn't guarantee the code is bug-free.</p><button className="text-action" onClick={() => { setResult(null); setError(''); }}>Review another snippet <span aria-hidden="true">↗</span></button></div> : <div className="findings-list">{result.findings.map((finding, i) => <article className="finding-row" key={`${finding.issue}-${finding.line ?? 0}-${i}`}><div className="finding-top"><strong>{finding.issue}</strong>{finding.line != null && <span>LINE {finding.line}</span>}</div><p>{finding.message}</p></article>)}</div>}</div>
                <div className="result-section"><div className="result-heading"><h4>Local AI review</h4><span>{useAi ? 'MODEL' : 'OFF'}</span></div>{result.ai_review ? <pre className="ai-output">{result.ai_review}</pre> : <div className="clean-state"><strong>AI review not included</strong><p>Turn on “Include local AI review” and run another review to get an explanation and suggested fix.</p></div>}</div>
                {result.warnings.length > 0 && <div className="result-section"><div className="result-heading"><h4>Validation warnings</h4><span>{result.warnings.length.toString().padStart(2, '0')}</span></div>{result.warnings.map((warning, i) => <p className="validation-warning" key={i}>{warning}</p>)}</div>}
                <div className="feedback-section"><div className="result-heading"><h4>Review feedback</h4><span>OPTIONAL</span></div><p>Was this review useful? Your feedback is saved locally for later evaluation.</p><label htmlFor="feedback-note" className="input-label">Correction or context</label><textarea id="feedback-note" className="feedback-input" placeholder="What should the review have said?" value={correction} onChange={e => setCorrection(e.target.value)} disabled={feedbackSent} /><div className="feedback-actions"><button className="outline-button" onClick={() => feedback('correct')} disabled={feedbackBusy || feedbackSent}>Accurate</button><button className="outline-button" onClick={() => feedback('incorrect')} disabled={feedbackBusy || feedbackSent}>Needs work</button></div>{feedbackStatus && <p className="feedback-message" role="status">{feedbackStatus}</p>}</div>
              </>}
            </div>
          </div>
        </section>
      </main>
      <footer className="footer"><span>CODELENS / LOCAL CODE REVIEW</span><span>PYTHON AST · QWEN VIA MLX · LOCAL FEEDBACK</span></footer>
    </div>
  );
}

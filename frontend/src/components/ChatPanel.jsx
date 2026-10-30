import { useEffect, useRef, useState } from 'react';
import Icon from './Icon';
import Markdown from './Markdown';

const TOOL_LABELS = {
  get_dataset_schema: 'Inspect schema',
  get_descriptive_stats: 'Descriptive stats',
  plot_numerical_distribution: 'Numeric distribution',
  plot_categorical_distribution: 'Category counts',
  plot_bivariate_relationship: 'Relationship plot',
  plot_correlation_heatmap: 'Correlation heatmap',
  perform_statistical_test: 'Statistical test',
  train_baseline_model: 'Train baseline model',
};

const toolLabel = (name) => TOOL_LABELS[name] ?? name;

function TraceStep({ step }) {
  if (step.type === 'thought') {
    return (
      <div className="trace-step">
        <div className="trace-label thought">
          <Icon name="brain" size={13} /> Reasoning
        </div>
        <div className="trace-text">{step.content}</div>
      </div>
    );
  }
  if (step.type === 'tool_call') {
    return (
      <div className="trace-step">
        <div className="trace-label tool">
          <Icon name="tool" size={13} /> {toolLabel(step.name)}
        </div>
        <pre className="trace-code">{JSON.stringify(step.arguments, null, 2)}</pre>
      </div>
    );
  }
  if (step.type === 'tool_output') {
    const failed = step.result && step.result.error;
    return (
      <div className="trace-step">
        <div className={`trace-label ${failed ? 'error' : 'output'}`}>
          <Icon name={failed ? 'alert' : 'check'} size={13} /> {failed ? 'Failed' : 'Result'}: {toolLabel(step.name)}
        </div>
        <pre className="trace-code">{JSON.stringify(step.result, null, 2)}</pre>
      </div>
    );
  }
  return (
    <div className="trace-step">
      <div className="trace-label error">
        <Icon name="alert" size={13} /> Error
      </div>
      <div className="trace-text">{step.content}</div>
    </div>
  );
}

function Trace({ steps }) {
  const [open, setOpen] = useState(false);
  const tools = steps.filter((s) => s.type === 'tool_call');
  if (steps.length === 0) return null;

  return (
    <div className="trace">
      <button type="button" className="trace-toggle" onClick={() => setOpen((o) => !o)} aria-expanded={open}>
        <Icon name="tool" size={13} />
        <span>
          {tools.length > 0
            ? `Used ${tools.length} tool${tools.length > 1 ? 's' : ''}`
            : 'Agent reasoning'}
        </span>
        <Icon name="chevron" size={13} className={open ? 'rot' : ''} />
      </button>
      {!open && tools.length > 0 && (
        <div className="chip-row">
          {tools.map((t, i) => (
            <span key={i} className="chip">
              {toolLabel(t.name)}
            </span>
          ))}
        </div>
      )}
      {open && (
        <div className="trace-steps">
          {steps.map((s, i) => (
            <TraceStep key={i} step={s} />
          ))}
        </div>
      )}
    </div>
  );
}

function Message({ message, onImageClick }) {
  const [copied, setCopied] = useState(false);

  if (message.role === 'notice') {
    return <div className="notice">{message.text}</div>;
  }

  if (message.role === 'user') {
    return (
      <div className="msg user">
        <div className="bubble user-bubble">{message.text}</div>
      </div>
    );
  }

  const streaming = message.status === 'streaming';
  const copy = async () => {
    try {
      await navigator.clipboard.writeText(message.text);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch {
      /* clipboard unavailable */
    }
  };

  return (
    <div className="msg agent">
      <div className="avatar">A</div>
      <div className="agent-body">
        {message.text ? (
          <div className={`bubble agent-bubble ${message.status === 'error' ? 'is-error' : ''}`}>
            <Markdown text={message.text} onImageClick={onImageClick} />
          </div>
        ) : (
          streaming && (
            <div className="bubble agent-bubble typing">
              <span className="dots">
                <i />
                <i />
                <i />
              </span>
              <span className="muted small">{message.activity || 'Thinking…'}</span>
            </div>
          )
        )}

        {streaming && message.text && message.activity && (
          <div className="activity muted small">
            <span className="spinner" /> {message.activity}
          </div>
        )}

        <Trace steps={message.steps} />

        {message.text && !streaming && (
          <div className="msg-actions">
            <button type="button" className="btn btn-ghost tiny" onClick={copy}>
              <Icon name={copied ? 'check' : 'copy'} size={13} /> {copied ? 'Copied' : 'Copy'}
            </button>
          </div>
        )}
      </div>
    </div>
  );
}

function Composer({ disabled, disabledHint, loading, onSend, onStop }) {
  const [value, setValue] = useState('');
  const ref = useRef(null);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    el.style.height = 'auto';
    el.style.height = `${Math.min(el.scrollHeight, 160)}px`;
  }, [value]);

  const submit = () => {
    const text = value.trim();
    if (!text || disabled || loading) return;
    onSend(text);
    setValue('');
  };

  return (
    <div className="composer">
      <textarea
        ref={ref}
        rows={1}
        value={value}
        disabled={disabled}
        placeholder={disabled ? disabledHint : 'Ask about your data…'}
        onChange={(e) => setValue(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === 'Enter' && !e.shiftKey && !e.nativeEvent.isComposing) {
            e.preventDefault();
            submit();
          }
        }}
        aria-label="Message"
      />
      {loading ? (
        <button type="button" className="send-btn stop" onClick={onStop} aria-label="Stop generating">
          <Icon name="stop" size={16} />
        </button>
      ) : (
        <button
          type="button"
          className="send-btn"
          onClick={submit}
          disabled={disabled || !value.trim()}
          aria-label="Send message"
        >
          <Icon name="send" size={16} />
        </button>
      )}
    </div>
  );
}

export default function ChatPanel({
  messages,
  loading,
  dataset,
  suggestions,
  onSend,
  onStop,
  onPickFile,
  onImageClick,
}) {
  const endRef = useRef(null);
  const hasMessages = messages.length > 0;

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' });
  }, [messages]);

  return (
    <div className="chat">
      <div className="chat-scroll">
        {!hasMessages ? (
          <div className="hero">
            <div className="hero-mark">
              <Icon name="sparkles" size={26} />
            </div>
            <h1>{dataset ? `Ask anything about ${dataset.filename}` : 'Analyze your data in plain English'}</h1>
            <p className="muted">
              {dataset
                ? 'AIDA explores the schema, runs statistical tests, draws charts and trains baseline models. Your raw data never leaves the backend.'
                : 'Upload a CSV and AIDA will explore it, test hypotheses, draw charts and train baseline models — no code needed.'}
            </p>
            {!dataset && (
              <button type="button" className="btn btn-primary" onClick={onPickFile}>
                <Icon name="upload" size={15} /> Upload a CSV
              </button>
            )}
            {dataset && (
              <div className="suggestions">
                {suggestions.map((s) => (
                  <button type="button" key={s} className="suggestion" onClick={() => onSend(s)} disabled={loading}>
                    <Icon name="sparkles" size={14} />
                    <span>{s}</span>
                  </button>
                ))}
              </div>
            )}
          </div>
        ) : (
          <div className="messages">
            {messages.map((m) => (
              <Message key={m.id} message={m} onImageClick={onImageClick} />
            ))}
            <div ref={endRef} />
          </div>
        )}
      </div>

      <div className="composer-wrap">
        {hasMessages && dataset && !loading && (
          <div className="quick-row">
            {suggestions.slice(0, 3).map((s) => (
              <button type="button" key={s} className="chip action" onClick={() => onSend(s)}>
                {s}
              </button>
            ))}
          </div>
        )}
        <Composer
          disabled={!dataset}
          disabledHint="Upload a CSV file to begin…"
          loading={loading}
          onSend={onSend}
          onStop={onStop}
        />
        <div className="composer-hint muted small">Enter to send · Shift+Enter for a new line</div>
      </div>
    </div>
  );
}

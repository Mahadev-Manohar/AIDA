import Icon from './Icon';

const STATUS = {
  checking: { label: 'Connecting…', tone: 'muted' },
  offline: { label: 'Backend offline', tone: 'error' },
  nokey: { label: 'API key missing', tone: 'warn' },
  ready: { label: 'Connected', tone: 'ok' },
};

export default function Header({ status, model, theme, onToggleTheme, onRetry, onNewChat, canReset }) {
  const s = STATUS[status];

  return (
    <header className="header">
      <div className="brand">
        <div className="brand-mark">A</div>
        <div className="brand-text">
          <span className="brand-name">AIDA</span>
          <span className="brand-sub">Automated Intelligent Data Agent</span>
        </div>
      </div>

      <div className="header-actions">
        <button
          type="button"
          className={`status-pill ${s.tone}`}
          onClick={status === 'offline' ? onRetry : undefined}
          title={status === 'offline' ? 'Click to retry' : model || ''}
        >
          <span className="status-dot" />
          {s.label}
          {status === 'ready' && model && <span className="status-model">{model}</span>}
          {status === 'offline' && <Icon name="refresh" size={13} />}
        </button>

        <button type="button" className="btn btn-ghost" onClick={onNewChat} disabled={!canReset}>
          <Icon name="refresh" size={15} />
          <span className="hide-sm">New chat</span>
        </button>

        <button
          type="button"
          className="icon-btn"
          onClick={onToggleTheme}
          aria-label={`Switch to ${theme === 'dark' ? 'light' : 'dark'} theme`}
          title="Toggle theme"
        >
          <Icon name={theme === 'dark' ? 'sun' : 'moon'} size={17} />
        </button>
      </div>
    </header>
  );
}

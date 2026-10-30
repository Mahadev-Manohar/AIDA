import { useEffect } from 'react';
import Icon from './Icon';

export default function PlotModal({ plots, index, onClose, onNavigate }) {
  const plot = plots[index];

  useEffect(() => {
    const onKey = (e) => {
      if (e.key === 'Escape') onClose();
      else if (e.key === 'ArrowLeft' && index > 0) onNavigate(index - 1);
      else if (e.key === 'ArrowRight' && index < plots.length - 1) onNavigate(index + 1);
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [index, plots.length, onClose, onNavigate]);

  if (!plot) return null;

  return (
    <div className="modal-overlay" onClick={onClose} role="dialog" aria-modal="true" aria-label={plot.summary}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal-head">
          <div className="modal-title">{plot.summary}</div>
          <div className="modal-actions">
            <span className="muted small">
              {index + 1} / {plots.length}
            </span>
            <a className="icon-btn" href={plot.url} download={plot.plot_path.split('/').pop()} aria-label="Download chart">
              <Icon name="download" size={16} />
            </a>
            <button type="button" className="icon-btn" onClick={onClose} aria-label="Close">
              <Icon name="x" size={16} />
            </button>
          </div>
        </div>
        <div className="modal-stage">
          <button
            type="button"
            className="nav-btn"
            disabled={index === 0}
            onClick={() => onNavigate(index - 1)}
            aria-label="Previous chart"
          >
            <Icon name="left" size={20} />
          </button>
          <img src={plot.url} alt={plot.summary} />
          <button
            type="button"
            className="nav-btn"
            disabled={index === plots.length - 1}
            onClick={() => onNavigate(index + 1)}
            aria-label="Next chart"
          >
            <Icon name="right" size={20} />
          </button>
        </div>
      </div>
    </div>
  );
}

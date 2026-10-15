import { useCallback, useEffect, useRef, useState } from 'react';

import { STATUS_BY_KEY, initials } from '../format.js';

export function StatusBadge({ status }) {
  const meta = STATUS_BY_KEY[status];
  return (
    <span className="badge">
      <span className="swatch" style={{ background: meta.color }} aria-hidden="true" />
      {meta.label}
    </span>
  );
}

export function Avatar({ name, tone = 'neutral' }) {
  return (
    <span className={`avatar avatar-${tone}`} aria-hidden="true">
      {initials(name)}
    </span>
  );
}

export function EmptyState({ title, children }) {
  return (
    <div className="empty">
      <strong>{title}</strong>
      {children && <p>{children}</p>}
    </div>
  );
}

export function Field({ label, hint, children, wide }) {
  return (
    <label className={`field${wide ? ' field-wide' : ''}`}>
      <span className="field-label">{label}</span>
      {children}
      {hint && <span className="field-hint">{hint}</span>}
    </label>
  );
}

/** A native <dialog>, so focus trapping and Esc-to-close come from the browser. */
export function Modal({ title, open, onClose, children }) {
  const ref = useRef(null);

  useEffect(() => {
    const dialog = ref.current;
    if (open && !dialog.open) dialog.showModal();
    if (!open && dialog.open) dialog.close();
  }, [open]);

  return (
    <dialog
      ref={ref}
      className="modal"
      onClose={onClose}
      onClick={(event) => event.target === ref.current && onClose()}
      aria-labelledby="modal-title"
    >
      {open && (
        <div className="modal-body">
          <header className="modal-head">
            <h2 id="modal-title">{title}</h2>
            <button type="button" className="icon-button" onClick={onClose} aria-label="Close">
              ×
            </button>
          </header>
          {children}
        </div>
      )}
    </dialog>
  );
}

export function useToasts() {
  const [toasts, setToasts] = useState([]);
  const notify = useCallback((message, tone = 'good') => {
    const id = crypto.randomUUID();
    setToasts((current) => [...current, { id, message, tone }]);
    setTimeout(() => setToasts((current) => current.filter((t) => t.id !== id)), 4500);
  }, []);
  return { toasts, notify };
}

export function Toasts({ toasts }) {
  return (
    <div className="toasts" role="status" aria-live="polite">
      {toasts.map((toast) => (
        <div key={toast.id} className={`toast toast-${toast.tone}`}>
          <span className="toast-icon" aria-hidden="true">
            {toast.tone === 'good' ? '✓' : '!'}
          </span>
          {toast.message}
        </div>
      ))}
    </div>
  );
}

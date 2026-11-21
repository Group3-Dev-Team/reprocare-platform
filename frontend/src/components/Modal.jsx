import { useId, useRef } from 'react';
import { X } from 'lucide-react';
import { useDialogFocus } from '../hooks/useDialogFocus';

/** Accessible dialog: focus moves inside, Escape and the backdrop close it, focus returns afterwards. */
export function Modal({ title, description, onClose, children, footer, width }) {
  const ref = useRef(null);
  const titleId = useId();
  const descriptionId = useId();
  useDialogFocus(ref, true, onClose, { initialFocus: 'input, select, textarea, a[href], button:not([data-close])' });
  return (
    <div className="modal-backdrop" onMouseDown={(e) => e.target === e.currentTarget && onClose()}>
      <div className="modal" role="dialog" aria-modal="true" aria-labelledby={titleId} aria-describedby={description ? descriptionId : undefined} ref={ref} tabIndex={-1} style={width ? { width: `min(100%, ${width}px)` } : undefined}>
        <div className="modal-head">
          <div>
            <h2 id={titleId}>{title}</h2>
            {description && <p id={descriptionId}>{description}</p>}
          </div>
          <button className="icon-btn" data-close onClick={onClose} aria-label="Close">
            <X size={18} />
          </button>
        </div>
        <div className="modal-body">{children}</div>
        {footer && <div className="modal-foot">{footer}</div>}
      </div>
    </div>
  );
}

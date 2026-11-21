import { useEffect, useRef } from 'react';

const tabTargets = 'a[href], button, input, select, textarea, summary, [tabindex], [contenteditable="true"]';

function tabStops(dialog) {
  return [...dialog.querySelectorAll(tabTargets)].filter((element) => (
    element.tabIndex >= 0 && !element.matches(':disabled') && element.getClientRects().length > 0
    && window.getComputedStyle(element).visibility === 'visible'
  ));
}

/** Keep focus and keyboard interaction inside an active modal, then restore the trigger. */
export function useDialogFocus(ref, isOpen, onClose, {
  initialFocus, returnFocus, allowOutside, lockScroll = true,
} = {}) {
  const dismiss = useRef(onClose);
  dismiss.current = onClose;

  useEffect(() => {
    const dialog = ref.current;
    if (!isOpen || !dialog) return undefined;
    const previous = returnFocus?.current || document.activeElement;
    const previousOverflow = document.body.style.overflow;
    const background = [];
    for (let element = dialog; element.parentElement && element !== document.body; element = element.parentElement) {
      for (const sibling of element.parentElement.children) {
        if (sibling !== element && sibling !== allowOutside?.current && !sibling.hasAttribute('inert')) {
          sibling.setAttribute('inert', '');
          background.push(sibling);
        }
      }
    }
    if (lockScroll) document.body.style.overflow = 'hidden';

    const preferred = () => {
      const stops = tabStops(dialog);
      return (initialFocus && stops.find((element) => element.matches(initialFocus))) || stops[0] || dialog;
    };
    preferred().focus({ preventScroll: true });

    const onKey = (event) => {
      if (event.defaultPrevented || event.isComposing) return;
      if (event.key === 'Escape') {
        event.preventDefault();
        dismiss.current();
      }
      if (event.key !== 'Tab') return;
      const stops = tabStops(dialog);
      const index = stops.indexOf(document.activeElement);
      if (!stops.length || index === -1 || (event.shiftKey ? index === 0 : index === stops.length - 1)) {
        event.preventDefault();
        (stops[event.shiftKey ? stops.length - 1 : 0] || dialog).focus();
      }
    };
    const keepFocus = (event) => {
      if (!dialog.contains(event.target)) preferred().focus({ preventScroll: true });
    };
    document.addEventListener('keydown', onKey);
    document.addEventListener('focusin', keepFocus);
    return () => {
      document.removeEventListener('keydown', onKey);
      document.removeEventListener('focusin', keepFocus);
      if (lockScroll) document.body.style.overflow = previousOverflow;
      background.forEach((element) => element.removeAttribute('inert'));
      if (previous?.isConnected && (dialog.contains(document.activeElement) || document.activeElement === document.body)) {
        previous.focus({ preventScroll: true });
      }
    };
  }, [ref, isOpen, initialFocus, returnFocus, allowOutside, lockScroll]);
}

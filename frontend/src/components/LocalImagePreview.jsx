import { useEffect, useId, useState } from 'react';
import { Image as ImageIcon, X } from 'lucide-react';
import { Field, TextInput } from './Forms';
import { Alert } from './Feedback';
import '../styles/patient-tools.css';

const allowedTypes = new Set(['image/jpeg', 'image/png', 'image/webp']);
const maxBytes = 5 * 1024 * 1024;

export function LocalImagePreview() {
  const inputId = useId();
  const [preview, setPreview] = useState(null);
  const [alt, setAlt] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const url = preview?.url;

  useEffect(() => {
    if (url) return () => URL.revokeObjectURL(url);
  }, [url]);

  function clear() {
    setPreview(null);
    setAlt('');
    setLoading(false);
    setError('');
  }

  function selectImage(event) {
    const [file] = event.target.files;
    event.target.value = '';
    if (!file) return;
    clear();
    if (!allowedTypes.has(file.type)) {
      setError('Choose a JPEG, PNG or WebP image.');
      return;
    }
    if (file.size > maxBytes) {
      setError('Choose an image no larger than 5 MB.');
      return;
    }
    setLoading(true);
    setPreview({ url: URL.createObjectURL(file), name: file.name });
  }

  return (
    <section className="panel local-image-preview stack" aria-labelledby={inputId + '-heading'}>
      <h2 id={inputId + '-heading'}>Facility photo preview</h2>
      <p className="small muted">Preview a public-facing photo before publishing becomes available. Your file stays in this tab and is separate from the listing form.</p>
      <Field label="Select an image" hint="JPEG, PNG or WebP, up to 5 MB. Choose a photo free of patient details." error={error}>
        {(a11y) => <input className="input" {...a11y} type="file" accept={[...allowedTypes].join(',')} onChange={selectImage} />}
      </Field>
      {error && <Alert tone="danger">{error}</Alert>}
      {loading && <progress aria-label="Loading image preview" />}
      {!preview ? (
        <div className="local-image-placeholder small muted">
          <ImageIcon size={24} aria-hidden="true" /> Select an image to see a preview.
        </div>
      ) : (
        <>
          <figure className="local-image-frame">
            <img
              key={url}
              src={url}
              alt={alt.trim() || 'Selected facility photo'}
              onLoad={() => setLoading(false)}
              onError={() => {
                clear();
                setError('The browser could not open this image. Choose a different file.');
              }}
            />
            <figcaption className="small muted">{preview.name}</figcaption>
          </figure>
          <TextInput label="Alternative text" hint="Describe what a patient needs to know about the photo." value={alt} onChange={(event) => setAlt(event.target.value)} maxLength={180} />
          <button type="button" className="btn btn-secondary btn-sm local-image-clear" onClick={clear}><X size={16} aria-hidden="true" /> Remove preview</button>
        </>
      )}
    </section>
  );
}

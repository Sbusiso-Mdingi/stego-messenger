import { useEffect, useState } from "react";

type Sample = { id: string; label: string; width: number; height: number; url: string };
type Detection = { rs_rate: number; rs_reliable: boolean; chi_square: number; hcf_ratio: number };
type Result = {
  method: "sequential" | "keyed";
  message_bytes: number;
  payload_bytes: number;
  capacity_bytes: number;
  capacity_utilization: number;
  psnr_db: number;
  ssim: number;
  detection: Detection;
  hcf_shift: number;
  rs_flagged: boolean;
  image: string;
  changes: string;
};
type Hidden = {
  cover: { width: number; height: number; detection: Detection };
  rs_threshold: number;
  results: { sequential: Result; keyed: Result };
};

const FILLS = [
  { value: 0, label: "Message only" },
  { value: 0.1, label: "10%" },
  { value: 0.25, label: "25%" },
  { value: 0.5, label: "50%" },
  { value: 0.9, label: "90%" },
];

const METHOD_TEXT = {
  sequential: {
    tag: "Baseline",
    title: "Sequential replacement",
    body: "Overwrites the lowest bit of each colour value, starting at the top-left corner.",
  },
  keyed: {
    tag: "Default",
    title: "Keyed LSB matching",
    body: "Nudges values by one up or down, at positions only the password can reproduce.",
  },
} as const;

async function post<T>(path: string, form: FormData): Promise<T> {
  const r = await fetch(path, { method: "POST", body: form });
  const body = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(body.detail ?? "Something went wrong. Try again.");
  return body as T;
}

function blobFromDataUri(uri: string): Blob {
  const bytes = atob(uri.split(",")[1] ?? "");
  const out = new Uint8Array(bytes.length);
  for (let i = 0; i < bytes.length; i++) out[i] = bytes.charCodeAt(i);
  return new Blob([out], { type: "image/png" });
}

const fixed = (v: number, d = 3) => v.toFixed(d);

export function App({ embedded }: { embedded: boolean }) {
  const [tab, setTab] = useState<"hide" | "reveal">("hide");
  const [handoff, setHandoff] = useState<{ file: File; password: string } | null>(null);

  return (
    <div className="preview">
      {!embedded && (
        <header className="intro">
          <p className="kicker">Stego Messenger · Live preview</p>
          <h1>Hide a message, then try to catch it</h1>
          <p>
            Encrypt a message, hide it in a photo with two different methods, and run the
            steganalysis detectors from the toolkit on both results.
          </p>
        </header>
      )}
      <div className="tabs" role="tablist">
        <button role="tab" aria-selected={tab === "hide"} onClick={() => setTab("hide")}>
          Hide and test
        </button>
        <button role="tab" aria-selected={tab === "reveal"} onClick={() => setTab("reveal")}>
          Read a message
        </button>
      </div>
      <div hidden={tab !== "hide"}>
        <HideTab
          onReadBack={(file, password) => {
            setHandoff({ file, password });
            setTab("reveal");
          }}
        />
      </div>
      <div hidden={tab !== "reveal"}>
        <RevealTab handoff={handoff} />
      </div>
      <p className="footnote">
        Nothing is stored: images and messages are processed in memory and discarded. Research
        software, not a secure messenger.
        {embedded ? "" : " Source: github.com/Sbusiso-Mdingi/stego-messenger."}
      </p>
    </div>
  );
}

function HideTab({ onReadBack }: { onReadBack: (file: File, password: string) => void }) {
  const [samples, setSamples] = useState<Sample[]>([]);
  const [sample, setSample] = useState("coffee");
  const [upload, setUpload] = useState<{ file: File; url: string } | null>(null);
  const [message, setMessage] = useState("Meet at Park Station, 7pm. Bring the blue folder.");
  const [password, setPassword] = useState("jozi-2026");
  const [fill, setFill] = useState(0.25);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [hidden, setHidden] = useState<Hidden | null>(null);
  const [coverUrl, setCoverUrl] = useState<string | null>(null);

  useEffect(() => {
    fetch("/api/samples")
      .then((r) => r.json() as Promise<Sample[]>)
      .then(setSamples)
      .catch(() => setError("The preview service is waking up. Refresh in a few seconds."));
  }, []);

  const run = async () => {
    setBusy(true);
    setError(null);
    const form = new FormData();
    form.set("message", message);
    form.set("password", password);
    form.set("fill", String(fill));
    if (upload) form.set("image", upload.file);
    else form.set("sample", sample);
    try {
      setHidden(await post<Hidden>("/api/hide", form));
      setCoverUrl(upload ? upload.url : `/api/samples/${sample}.png`);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <>
      <section className="step">
        <h3>
          <span>1</span> Choose a cover image
        </h3>
        <div className="covers">
          {samples.map((s) => (
            <button
              key={s.id}
              className="cover"
              aria-pressed={!upload && sample === s.id}
              onClick={() => {
                setUpload(null);
                setSample(s.id);
              }}
            >
              <img src={s.url} alt="" width={s.width} height={s.height} />
              <span>{s.label}</span>
            </button>
          ))}
          <label className="cover upload" data-active={!!upload}>
            {upload ? <img src={upload.url} alt="" /> : <b>+</b>}
            <span>{upload ? "Your image" : "Upload your own"}</span>
            <input
              type="file"
              accept="image/png,image/jpeg,image/webp"
              onChange={(e) => {
                const file = e.target.files?.[0];
                if (file) setUpload({ file, url: URL.createObjectURL(file) });
              }}
            />
          </label>
        </div>
        <p className="hint">Uploads are scaled to at most 640 pixels on the longest side.</p>
      </section>

      <section className="step">
        <h3>
          <span>2</span> Write the message
        </h3>
        <div className="fields">
          <label>
            Message
            <textarea value={message} maxLength={4000} rows={3} onChange={(e) => setMessage(e.target.value)} />
          </label>
          <label>
            Password
            <input value={password} maxLength={200} onChange={(e) => setPassword(e.target.value)} />
            <small>Shown in plain text so you can use it again in “Read a message”.</small>
          </label>
        </div>
      </section>

      <section className="step">
        <h3>
          <span>3</span> Choose the payload size
        </h3>
        <div className="segmented" role="group" aria-label="Payload size">
          {FILLS.map((f) => (
            <button key={f.value} aria-pressed={fill === f.value} onClick={() => setFill(f.value)}>
              {f.label}
            </button>
          ))}
        </div>
        <p className="hint">
          The encrypted message is padded with random bytes to this share of the image’s capacity.
          A short message alone is too small for any detector to find, so padding shows how
          detection grows with payload.
        </p>
      </section>

      <div className="actions">
        <button className="button" disabled={busy || !message.trim() || !password} onClick={run}>
          {busy ? "Hiding and testing…" : "Hide and test"}
        </button>
        {error && <p className="error">{error}</p>}
      </div>

      {hidden && coverUrl && <Results hidden={hidden} coverUrl={coverUrl} password={password} onReadBack={onReadBack} />}
    </>
  );
}

function Results({
  hidden,
  coverUrl,
  password,
  onReadBack,
}: {
  hidden: Hidden;
  coverUrl: string;
  password: string;
  onReadBack: (file: File, password: string) => void;
}) {
  const { cover, results, rs_threshold } = hidden;
  return (
    <section className="results" aria-live="polite">
      <div className="compare">
        <figure>
          <img src={coverUrl} alt="The original cover image" />
          <figcaption>Original</figcaption>
        </figure>
        <figure>
          <img src={results.keyed.image} alt="The same image with the message hidden in it" />
          <figcaption>With the hidden message ({fixed(results.keyed.psnr_db, 1)} dB PSNR)</figcaption>
        </figure>
      </div>
      <p className="hint center">
        Invisible to the eye. The question is whether a detector can tell.
      </p>

      <div className="methods">
        {(["sequential", "keyed"] as const).map((m) => {
          const r = results[m];
          const text = METHOD_TEXT[m];
          return (
            <article key={m} className="method">
              <p className="tag">{text.tag}</p>
              <h3>{text.title}</h3>
              <p className="muted">{text.body}</p>
              <figure className="changes">
                <img src={r.changes} alt={`Map of the pixels changed by ${text.title.toLowerCase()}`} />
                <figcaption>Pixels changed, in gold</figcaption>
              </figure>
              <p className={r.rs_flagged ? "verdict flagged" : "verdict clear"}>
                {r.rs_flagged ? "Flagged by RS analysis" : "Not flagged by RS analysis"}
              </p>
              <dl className="readings">
                <Reading
                  label="RS analysis, estimated embedding rate"
                  value={r.detection.rs_rate}
                  clean={cover.detection.rs_rate}
                  threshold={rs_threshold}
                />
                <Reading
                  label="Chi-square attack, embedding probability"
                  value={r.detection.chi_square}
                  clean={cover.detection.chi_square}
                />
                <div className="reading">
                  <dt>HCF-COM shift from the original</dt>
                  <dd className="mono">{(r.hcf_shift >= 0 ? "+" : "−") + fixed(Math.abs(r.hcf_shift))}</dd>
                </div>
              </dl>
              <dl className="quality">
                <div>
                  <dt>PSNR</dt>
                  <dd>{fixed(r.psnr_db, 1)} dB</dd>
                </div>
                <div>
                  <dt>SSIM</dt>
                  <dd>{fixed(r.ssim, 4)}</dd>
                </div>
                <div>
                  <dt>Payload</dt>
                  <dd>{r.payload_bytes.toLocaleString()} B</dd>
                </div>
              </dl>
              <div className="method-actions">
                <a className="button button-outline" href={r.image} download={`stego-${m}.png`}>
                  Download PNG
                </a>
                <button
                  className="text-link"
                  onClick={() => onReadBack(new File([blobFromDataUri(r.image)], `stego-${m}.png`, { type: "image/png" }), password)}
                >
                  Read it back
                </button>
              </div>
            </article>
          );
        })}
      </div>
      <p className="caveat">
        Keyed matching gets past the two detectors built for replacement, but it is not
        undetectable. The HCF-COM detector targets matching, and in the benchmark it moves
        further for keyed embedding as the payload grows. Learned detectors are stronger still.
        Encryption hides what the message says; nothing here hides for certain that a message
        is there.
      </p>
    </section>
  );
}

function Reading({
  label,
  value,
  clean,
  threshold,
}: {
  label: string;
  value: number;
  clean: number;
  threshold?: number;
}) {
  const pct = (v: number) => `${Math.min(100, Math.max(0, v * 100))}%`;
  return (
    <div className="reading">
      <dt>{label}</dt>
      <dd className="mono">{fixed(value)}</dd>
      <div className="bar" aria-hidden="true">
        <i className="fill" style={{ width: pct(value) }} />
        <i className="mark clean" style={{ left: pct(clean) }} title="Original image" />
        {threshold !== undefined && <i className="mark threshold" style={{ left: pct(threshold) }} />}
      </div>
      <small>
        Original image {fixed(clean)}
        {threshold !== undefined ? ` · flag above ${threshold}` : ""}
      </small>
    </div>
  );
}

function RevealTab({ handoff }: { handoff: { file: File; password: string } | null }) {
  const [file, setFile] = useState<File | null>(null);
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [found, setFound] = useState<{ message: string; method: string } | null>(null);

  useEffect(() => {
    if (!handoff) return;
    setFile(handoff.file);
    setPassword(handoff.password);
    setFound(null);
    setError(null);
  }, [handoff]);

  const run = async () => {
    if (!file) return;
    setBusy(true);
    setError(null);
    setFound(null);
    const form = new FormData();
    form.set("image", file);
    form.set("password", password);
    try {
      setFound(await post("/api/reveal", form));
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <>
      <section className="step">
        <h3>
          <span>1</span> Choose the PNG
        </h3>
        <label className="file">
          <input
            type="file"
            accept="image/png"
            onChange={(e) => {
              setFile(e.target.files?.[0] ?? null);
              setFound(null);
            }}
          />
          <span className="button button-outline">Choose file</span>
          <span className="muted">{file ? file.name : "No file chosen"}</span>
        </label>
        <p className="hint">
          The image and the password are all it needs. The salt and key settings travel inside
          the image.
        </p>
      </section>
      <section className="step">
        <h3>
          <span>2</span> Enter the password
        </h3>
        <div className="fields single">
          <label>
            Password
            <input value={password} maxLength={200} onChange={(e) => setPassword(e.target.value)} />
          </label>
        </div>
      </section>
      <div className="actions">
        <button className="button" disabled={busy || !file || !password} onClick={run}>
          {busy ? "Reading…" : "Read message"}
        </button>
        {error && <p className="error">{error}</p>}
      </div>
      {found && (
        <section className="found" aria-live="polite">
          <p className="tag">Recovered and authenticated</p>
          <blockquote>{found.message}</blockquote>
          <p className="muted">
            Found with {found.method === "keyed" ? "keyed LSB matching" : "sequential replacement"}.
            AES-256-GCM confirmed it was not altered.
          </p>
        </section>
      )}
    </>
  );
}

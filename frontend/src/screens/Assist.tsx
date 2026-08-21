import { FormEvent, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { useChat } from "../hooks/useChat";
import { useEngine } from "../hooks/useEngine";

export function Assist() {
  const [params] = useSearchParams();
  const docId = params.get("doc") ?? undefined;
  const navigate = useNavigate();
  const { engine } = useEngine();
  const assistantOn = !engine || engine.ollama.ok === true || engine.chat?.ok === true;
  const { messages, send, busy, error } = useChat(docId, assistantOn);
  const [text, setText] = useState("");
  const thread = messages.length > 0;

  function onSubmit(e: FormEvent) {
    e.preventDefault();
    const next = text;
    setText("");
    void send(next);
  }

  return (
    <div className={`assist${thread ? " has-thread" : ""}`}>
      <button
        type="button"
        className="assist__back"
        onClick={() => navigate(docId ? `/doc/${docId}` : "/")}
      >
        revisión
      </button>

      <div className="assist__stage">
        {!thread ? (
          <h1 className="assist__mark">
            <span className="assist__glyph" aria-hidden="true">
              <i />
              <i />
              <i />
              <i />
              <i />
              <i />
              <i />
              <i />
              <i />
            </span>
            Cuadre IQ
          </h1>
        ) : null}

        {thread ? (
          <ul className="assist__log">
            {messages.map((m, i) => (
              <li key={i} className={m.role === "user" ? "is-user" : "is-bot"}>
                {m.text}
              </li>
            ))}
            {busy ? (
              <li className="is-bot is-pending" aria-live="polite">
                …
              </li>
            ) : null}
          </ul>
        ) : null}

        <form className="composer" onSubmit={onSubmit}>
          {!assistantOn ? (
            <p className="composer__off">asistente apagado</p>
          ) : (
            <textarea
              value={text}
              onChange={(e) => setText(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  onSubmit(e);
                }
              }}
              placeholder="¿Qué necesitas de la cola?"
              disabled={busy}
              rows={thread ? 2 : 4}
              spellCheck={false}
            />
          )}
          <div className="composer__bar">
            <span className="composer__hint">
              {docId ? "este documento · local" : "manual · Ollama local"}
            </span>
            <button type="submit" disabled={!assistantOn || busy || !text.trim()}>
              enviar
            </button>
          </div>
        </form>
        {error ? <p className="composer__off">{error}</p> : null}
      </div>
    </div>
  );
}

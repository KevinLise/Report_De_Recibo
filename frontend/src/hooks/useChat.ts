import { useCallback, useState } from "react";
import { sendChat, sendChatEmail } from "../api/client";
import { pulseField } from "../field/bus";

export type ChatMsg = { role: "user" | "assistant"; text: string };

export function useChat(documentId: string | undefined, assistantOn: boolean) {
  const [messages, setMessages] = useState<ChatMsg[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const send = useCallback(
    async (text: string) => {
      const trimmed = text.trim();
      if (!trimmed || !assistantOn || busy) return;
      setBusy(true);
      setError(null);
      const prior = messages.slice(-8);
      setMessages((m) => [...m, { role: "user", text: trimmed }]);
      try {
        const res = await sendChat(trimmed, documentId, prior);
        setMessages((m) => [...m, { role: "assistant", text: res.text }]);
        pulseField("chat");
        if (
          res.action === "email" &&
          res.to &&
          !res.sent &&
          (res.document_id || documentId)
        ) {
          await sendChatEmail(res.document_id ?? documentId ?? "", res.to);
          pulseField("email");
        } else if (res.sent) {
          pulseField("email");
        }
      } catch (e) {
        setError(e instanceof Error ? e.message : "chat");
      } finally {
        setBusy(false);
      }
    },
    [assistantOn, busy, documentId, messages],
  );

  return { messages, send, busy, error };
}

import { useNavigate } from "react-router-dom";

type Props = {
  documentId?: string;
};

export function ChatDock({ documentId }: Props) {
  const navigate = useNavigate();
  return (
    <button
      type="button"
      className="chat"
      onClick={() =>
        navigate(documentId ? `/asistente?doc=${encodeURIComponent(documentId)}` : "/asistente")
      }
    >
      asistente
    </button>
  );
}

type Props = {
  disabled?: boolean;
  onApprove: () => void;
  onReject: () => void;
  onOpen?: () => void;
};

export function Actions({ disabled, onApprove, onReject, onOpen }: Props) {
  return (
    <div className="actions">
      {onOpen ? (
        <button type="button" className="empty__open" onClick={onOpen}>
          abrir PDF o foto
        </button>
      ) : null}
      <button type="button" className="act act--fault" disabled={disabled} onClick={onReject}>
        rechazar
        <kbd>⇧R</kbd>
      </button>
      <button type="button" className="act act--pass" disabled={disabled} onClick={onApprove}>
        aprobar
        <kbd>R</kbd>
      </button>
    </div>
  );
}

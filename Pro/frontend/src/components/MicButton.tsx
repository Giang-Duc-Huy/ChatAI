interface Props {
  supported: boolean;
  listening: boolean;
  disabled?: boolean;
  onToggle: () => void;
}

export function MicButton({ supported, listening, disabled, onToggle }: Props) {
  if (!supported) {
    return <p className="mic-unsupported">Trình duyệt không hỗ trợ nhập giọng nói (cần Chrome/Edge).</p>;
  }
  return (
    <button
      type="button"
      className={`mic-btn${listening ? " mic-on" : ""}`}
      onClick={onToggle}
      disabled={disabled}
      aria-pressed={listening}
      title={listening ? "Dừng ghi" : "Nói để hỏi"}
    >
      {listening ? "Đang nghe…" : "Nói"}
    </button>
  );
}

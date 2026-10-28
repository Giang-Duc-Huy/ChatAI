type Props = {
  listening: boolean;
  disabled?: boolean;
  onClick: () => void;
};

export function MicButton({ listening, disabled = false, onClick }: Props) {
  return (
    <button id="mic" className={listening ? "rec" : ""} disabled={disabled} onClick={onClick}>
      {listening ? "⏹ Đang nghe (bấm để dừng)" : "🎤 Ghi âm"}
    </button>
  );
}

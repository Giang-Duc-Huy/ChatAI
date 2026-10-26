type Props = {
  listening: boolean;
  onClick: () => void;
};

export function MicButton({ listening, onClick }: Props) {
  return (
    <button id="mic" className={listening ? "rec" : ""} onClick={onClick}>
      {listening ? "⏹ Đang nghe (bấm để dừng)" : "🎤 Ghi âm"}
    </button>
  );
}

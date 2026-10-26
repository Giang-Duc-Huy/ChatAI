type Props = {
  topK: number;
  minScore: number;
  rate: number;
  onTopK: (n: number) => void;
  onMinScore: (n: number) => void;
  onRate: (n: number) => void;
};

export function SettingsBar({ topK, minScore, rate, onTopK, onMinScore, onRate }: Props) {
  return (
    <details>
      <summary>Cài đặt</summary>
      <div className="row mu" style={{ alignItems: "center" }}>
        TOP_K{" "}
        <input
          type="number"
          value={topK}
          min={1}
          max={10}
          style={{ width: 56 }}
          onChange={(e) => onTopK(Math.min(10, Math.max(1, Number(e.target.value) || 5)))}
        />
        MIN_SCORE{" "}
        <input
          type="number"
          value={minScore}
          min={0}
          max={1}
          step={0.05}
          style={{ width: 64 }}
          onChange={(e) => onMinScore(Number(e.target.value))}
        />
        Tốc độ đọc{" "}
        <input
          type="number"
          value={rate}
          step={0.1}
          min={0.6}
          max={1.5}
          style={{ width: 60 }}
          onChange={(e) => onRate(Number(e.target.value) || 1)}
        />
      </div>
      <div className="mu" style={{ marginTop: 6 }}>
        Ghi âm: dùng nhận dạng giọng nói của trình duyệt (vi-VN). Việc xử lý âm thanh phụ thuộc trình duyệt và nhà cung cấp nhận dạng.
      </div>
    </details>
  );
}

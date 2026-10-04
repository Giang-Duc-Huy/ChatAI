interface Props {
  voiceEnabled: boolean;
  avatarEnabled: boolean;
  ttsPlaying: boolean;
  onVoiceChange: (v: boolean) => void;
  onAvatarChange: (v: boolean) => void;
  onStopAudio: () => void;
}

export function SettingsBar({
  voiceEnabled,
  avatarEnabled,
  ttsPlaying,
  onVoiceChange,
  onAvatarChange,
  onStopAudio,
}: Props) {
  return (
    <div className="settings-bar">
      <label className="toggle">
        <input
          type="checkbox"
          checked={voiceEnabled}
          onChange={(e) => onVoiceChange(e.target.checked)}
        />
        Đọc câu trả lời
      </label>
      <label className="toggle">
        <input
          type="checkbox"
          checked={avatarEnabled}
          onChange={(e) => onAvatarChange(e.target.checked)}
        />
        Nhân vật 3D
      </label>
      {ttsPlaying && (
        <button type="button" className="stop-audio" onClick={onStopAudio}>
          Dừng nghe
        </button>
      )}
    </div>
  );
}

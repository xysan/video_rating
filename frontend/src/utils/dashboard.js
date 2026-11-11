export function scoreOf(video) {
  const value = video.score ?? video.total_score;
  if (value === null || value === undefined || value === "") return null;
  return Number.isFinite(Number(value)) ? Number(value) : null;
}
export function isHighScore(video) {
  return (
    video.is_high_score === true ||
    (scoreOf(video) !== null && scoreOf(video) >= 85)
  );
}
export function formatCount(value) {
  if (
    value === null ||
    value === undefined ||
    value === "" ||
    !Number.isFinite(Number(value))
  )
    return "—";
  const number = Number(value);
  if (number >= 1e8) return `${(number / 1e8).toFixed(1)}亿`;
  if (number >= 1e4) return `${(number / 1e4).toFixed(1)}万`;
  return new Intl.NumberFormat("zh-CN").format(number);
}
export function titleOf(video) {
  return video.title || video.video_title || "暂无标题";
}
export function nextScroll(left, width, viewport, direction) {
  const max = Math.max(0, width - viewport);
  if (max === 0) return 0;
  if (direction > 0 && left >= max - 2) return 0;
  if (direction < 0 && left <= 2) return max;
  return Math.max(
    0,
    Math.min(max, left + direction * Math.max(296, viewport * 0.8)),
  );
}

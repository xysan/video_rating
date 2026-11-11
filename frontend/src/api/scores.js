import { api } from "./client";
export const publicScoreFields = [
  "difficulty",
  "efficiency",
  "traffic_ratio",
  "tags",
  "id",
  "video_title",
  "title",
  "up_name",
  "director",
  "publish_date",
  "total_score",
  "play_count",
  "snapshot_play_count",
  "interact_rate",
  "jump_3s",
  "convert_rate",
  "progress",
];
export function projectScore(row, admin = false) {
  const publicRow = Object.fromEntries(
    publicScoreFields.map((key) => [key, row[key]]),
  );
  return admin
    ? {
        ...publicRow,
        score_detail: row.score_detail,
        raw_payload: row.raw_payload,
      }
    : publicRow;
}
export async function fetchScores(admin, params, signal) {
  const { data } = await api.get(
    admin ? "/api/admin/scores" : "/api/member/scores",
    { params, signal, paramsSerializer: { indexes: null } },
  );
  return { ...data, items: data.items.map((row) => projectScore(row, admin)) };
}
export function percent(value) {
  return value == null || value === ""
    ? "—"
    : `${(Number(value) * 100).toFixed(2)}%`;
}

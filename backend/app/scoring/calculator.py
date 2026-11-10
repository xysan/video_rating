import math

CORE_METRICS = ("play", "interact", "jump_3s", "progress", "convert")
WEIGHT_METRICS = CORE_METRICS + ("difficulty", "efficiency")


class ConfigurationError(ValueError):
    pass


def parse_metric_value(value_str, metric_type=None):
    if value_str is None or isinstance(value_str, str) and not value_str.strip():
        return None
    if isinstance(value_str, bool):
        raise ValueError("指标不能是布尔值")
    if isinstance(value_str, (int, float)):
        result = value_str
    elif isinstance(value_str, str):
        value = value_str.strip()
        if "%" in value:
            result = float(value.replace("%", "").strip()) / 100.0
        elif "万" in value:
            result = float(value.replace("万", "").strip()) * 10000.0
        else:
            result = float(value)
    else:
        raise ValueError("指标必须是数值或字符串")
    if not math.isfinite(result):
        raise ValueError("指标必须是有限数值")
    return result


def linear_interpolate(x, left, right, low_score, high_score):
    return low_score + (high_score - low_score) * (x - left) / (right - left)


def calc_positive_score(x, p10, p25, p50, p75, p95, score_points):
    standards = (p10, p25, p50, p75, p95)
    # 保留原伪代码中相邻基线相等时的优先返回规则。
    for index in range(4):
        if standards[index] == standards[index + 1]:
            return score_points[index] if x <= standards[index] else score_points[index + 1]
    if x <= p10:
        return score_points[0]
    for index in range(4):
        if x <= standards[index + 1]:
            return linear_interpolate(x, standards[index], standards[index + 1], score_points[index], score_points[index + 1])
    return score_points[-1]


def calc_reverse_score(x, p10, p25, p50, p75, p95, score_points):
    standards = (p95, p75, p50, p25, p10)
    for index in range(4):
        if standards[index] == standards[index + 1]:
            return score_points[index] if x >= standards[index] else score_points[index + 1]
    if x >= p95:
        return score_points[0]
    for index in range(4):
        if x >= standards[index + 1]:
            return linear_interpolate(x, standards[index], standards[index + 1], score_points[index], score_points[index + 1])
    return score_points[-1]


def numeric(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def validate_standards(standards):
    if not isinstance(standards, dict) or set(standards) != set(CORE_METRICS):
        raise ConfigurationError("基线必须包含五个核心维度")
    for metric in CORE_METRICS:
        values = standards[metric]
        if not isinstance(values, list) or len(values) != 5 or not all(numeric(v) for v in values) or values != sorted(values):
            raise ConfigurationError(f"{metric} 基线必须是五个升序有限数值")


REQUIRED_KEYS = tuple("weight_" + m for m in WEIGHT_METRICS) + ("score_diff_S", "score_diff_A", "score_diff_B", "efficiency_scores", "ranking_bonuses", "traffic_penalty_thresholds", "neutral_score", "interpolation_scores", "metric_fields", "calculation_age_days")


def validate_rules(config):
    missing = [key for key in REQUIRED_KEYS if key not in config]
    if missing:
        raise ConfigurationError("缺少算法配置：" + ", ".join(missing))
    for key in ["weight_" + m for m in WEIGHT_METRICS] + ["score_diff_S", "score_diff_A", "score_diff_B", "neutral_score"]:
        if not numeric(config[key]) or config[key] < 0:
            raise ConfigurationError(f"{key} 必须是非负有限数值")
    points = config["interpolation_scores"]
    if not isinstance(points, list) or len(points) != 5 or not all(numeric(v) for v in points) or points != sorted(points):
        raise ConfigurationError("interpolation_scores 必须是五个升序有限数值")
    efficiency = config["efficiency_scores"]
    if not isinstance(efficiency, dict) or set(efficiency) != {"按时", "推迟1-2天", "推迟2-3天", "推迟3-5天", "推迟5天以上"} or not all(numeric(v) for v in efficiency.values()):
        raise ConfigurationError("效率配置必须包含全部五种状态及有限分值")
    ranking = config["ranking_bonuses"]
    if not isinstance(ranking, list) or len(ranking) != 3 or any(not isinstance(item, dict) or set(item) != {"tag", "score"} or not numeric(item["score"]) for item in ranking):
        raise ConfigurationError("榜单配置必须包含三个 tag/score 对象")
    if [item["tag"] for item in ranking] != ["每周必看", "全站", "热门"]:
        raise ConfigurationError("榜单优先级必须为每周必看、全站、热门")
    traffic = config["traffic_penalty_thresholds"]
    if not isinstance(traffic, dict) or set(traffic) != {"lower", "upper", "middle_penalty", "high_penalty"} or not all(numeric(v) and v >= 0 for v in traffic.values()) or traffic["lower"] > traffic["upper"]:
        raise ConfigurationError("投流阈值或扣分配置无效")
    fields = config["metric_fields"]
    if not isinstance(fields, dict) or set(fields) != set(WEIGHT_METRICS + ("tags", "traffic_ratio")):
        raise ConfigurationError("metric_fields 必须包含全部指标映射")
    if any(v is not None and (not isinstance(v, str) or not v.strip()) for v in fields.values()):
        raise ConfigurationError("字段映射必须为非空字符串或 null")
    if any(not fields[m] for m in CORE_METRICS):
        raise ConfigurationError("核心指标必须配置字段映射")
    if not isinstance(config["calculation_age_days"], int) or isinstance(config["calculation_age_days"], bool) or config["calculation_age_days"] < 0:
        raise ConfigurationError("计算天数必须为非负整数")


def calculate_video_score(video_data, up_standards, config):
    validate_rules(config)
    validate_standards(up_standards)
    metrics = {m: parse_metric_value(video_data.get(m)) for m in CORE_METRICS}
    for metric in CORE_METRICS:
        if metrics[metric] is None:
            return {"status": "error", "message": "核心指标数据缺失，无法计算得分", "missing_fields": [metric], "final_score": None}
    points = config["interpolation_scores"]
    scores = {m: (calc_reverse_score if m == "jump_3s" else calc_positive_score)(metrics[m], *up_standards[m], score_points=points) for m in CORE_METRICS}
    missing_fields = []
    zero = config["neutral_score"]
    difficulty = video_data.get("difficulty")
    efficiency = video_data.get("efficiency")
    if difficulty is None:
        missing_fields.append("difficulty")
    if efficiency is None:
        missing_fields.append("efficiency")
    scores["difficulty"] = {level: config["score_diff_" + level] for level in ("S", "A", "B")}.get(difficulty, zero)
    scores["efficiency"] = config["efficiency_scores"].get(efficiency, zero)
    base_score = sum(scores[m] * config["weight_" + m] for m in WEIGHT_METRICS)
    tags = video_data.get("tags")
    ranking_bonus = zero
    if tags is None:
        missing_fields.append("tags")
    else:
        for item in config["ranking_bonuses"]:
            if item["tag"] in tags:
                ranking_bonus = item["score"]
                break
    ratio = parse_metric_value(video_data.get("traffic_ratio"))
    traffic_penalty = zero
    if ratio is None:
        missing_fields.append("traffic_ratio")
    else:
        traffic = config["traffic_penalty_thresholds"]
        if ratio > traffic["upper"]:
            traffic_penalty = traffic["high_penalty"]
        elif traffic["lower"] <= ratio <= traffic["upper"]:
            traffic_penalty = traffic["middle_penalty"]
    return {
        "status": "success" if not missing_fields else "partial_success",
        "final_score": round(base_score + ranking_bonus - traffic_penalty, 2),
        "base_score": round(base_score, 2),
        "score_details": {"play_score": round(scores["play"], 2), "interact_score": round(scores["interact"], 2), "jump_score": round(scores["jump_3s"], 2), "progress_score": round(scores["progress"], 2), "convert_score": round(scores["convert"], 2), "difficulty_score": scores["difficulty"], "efficiency_score": scores["efficiency"]},
        "bonus_and_penalty": {"ranking_bonus": ranking_bonus, "traffic_penalty": -traffic_penalty},
        "missing_fields": missing_fields,
        "message": "计算成功" if not missing_fields else f"计算成功，但缺少以下数据项：{missing_fields}，请补充后重算",
    }

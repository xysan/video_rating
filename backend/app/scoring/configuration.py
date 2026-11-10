import json

from sqlalchemy import select

from app.models import AlgorithmConfig
from app.scoring.calculator import ConfigurationError, REQUIRED_KEYS, validate_rules, validate_standards


def load_configs(session):
    result = {}
    for key, value in session.execute(select(AlgorithmConfig.config_key, AlgorithmConfig.config_value)):
        try:
            result[key] = json.loads(value)
        except (ValueError, TypeError):
            raise ConfigurationError(f"配置 {key} 不是合法 JSON") from None
    return result


def validate_config_update(key, value, existing):
    # 每次只校验本次字段，允许首次配置按键逐项录入。
    if key.startswith("up_standards_"):
        if not key.removeprefix("up_standards_").strip():
            raise ConfigurationError("UP 主名称不能为空")
        validate_standards(value)
    elif key in REQUIRED_KEYS:
        # 校验器对缺少配置有明确报错；现有完整规则可直接整体校验。
        combined = {**existing, key: value}
        if all(k in combined for k in REQUIRED_KEYS):
            validate_rules(combined)
        else:
            from app.scoring.initialize_configs import read_initial_rules
            validate_rules({**read_initial_rules(), **{k: v for k, v in combined.items() if k in REQUIRED_KEYS}})

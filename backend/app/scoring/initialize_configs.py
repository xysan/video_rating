import json
from pathlib import Path

from sqlalchemy import select

from app.database import SessionLocal
from app.models import AlgorithmConfig
from app.scoring.calculator import validate_rules


def read_initial_rules():
    # 此文件仅用于显式初始化或输入校验，运行时计算绝不读取它兜底。
    return json.loads(Path(__file__).with_name("initial_rules.json").read_text(encoding="utf-8"))


def initialize_configs(session):
    rules = read_initial_rules()
    validate_rules(rules)
    added = 0
    for key, value in rules.items():
        if session.scalar(select(AlgorithmConfig.id).where(AlgorithmConfig.config_key == key)) is None:
            session.add(AlgorithmConfig(config_key=key, config_value=json.dumps(value, ensure_ascii=False, allow_nan=False), description="PR-05 用户确认的计分规则", updated_by=None))
            added += 1
    session.commit()
    return added


if __name__ == "__main__":
    with SessionLocal() as session:
        print(f"已初始化 {initialize_configs(session)} 项规则；未覆盖现有值，未创建 UP 主基线")

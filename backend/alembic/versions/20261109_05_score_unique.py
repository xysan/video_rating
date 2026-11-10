"""同一视频与算法版本只能存在一条评分。"""
from alembic import op

revision = "20261109_05"
down_revision = "92bc01ba8d6d"
branch_labels = None
depends_on = None


def upgrade():
    # 发现历史重复记录时迁移失败，不擅自删除评分。
    with op.batch_alter_table("scores") as batch:
        batch.create_unique_constraint("uq_scores_snapshot_version", ["video_snapshot_id", "algorithm_version"])


def downgrade():
    with op.batch_alter_table("scores") as batch:
        batch.drop_constraint("uq_scores_snapshot_version", type_="unique")

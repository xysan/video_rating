"""创建四张业务表。"""
from alembic import op
import sqlalchemy as sa


revision = '92bc01ba8d6d'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # 创建或回滚本次迁移的业务表。
    op.create_table('algorithm_configs',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('config_key', sa.String(length=191), nullable=False),
    sa.Column('config_value', sa.Text(), nullable=False),
    sa.Column('description', sa.Text(), nullable=True),
    sa.Column('updated_by', sa.Integer(), nullable=True),
    sa.Column('updated_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('config_key'),
    mysql_charset='utf8mb4',
    mysql_collate='utf8mb4_unicode_ci',
    mysql_engine='InnoDB'
    )
    op.create_table('users',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('username', sa.String(length=191), nullable=False),
    sa.Column('password_hash', sa.String(length=255), nullable=False),
    sa.Column('display_name', sa.String(length=255), nullable=False),
    sa.Column('role', sa.Enum('admin', 'member', name='user_role', create_constraint=True), nullable=False),
    sa.Column('is_active', sa.Boolean(), server_default='1', nullable=False),
    sa.Column('created_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('username'),
    mysql_charset='utf8mb4',
    mysql_collate='utf8mb4_unicode_ci',
    mysql_engine='InnoDB'
    )
    op.create_table('video_snapshots',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('feishu_record_id', sa.String(length=191), nullable=False),
    sa.Column('up_name', sa.String(length=255), nullable=False),
    sa.Column('video_title', sa.Text(), nullable=False),
    sa.Column('publish_date', sa.Date(), nullable=False),
    sa.Column('raw_payload', sa.JSON(), nullable=False),
    sa.Column('last_modified_at', sa.DateTime(), nullable=False),
    sa.Column('synced_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('feishu_record_id'),
    mysql_charset='utf8mb4',
    mysql_collate='utf8mb4_unicode_ci',
    mysql_engine='InnoDB'
    )
    op.create_table('scores',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('video_snapshot_id', sa.Integer(), nullable=False),
    sa.Column('score', sa.Numeric(precision=18, scale=6), nullable=False),
    sa.Column('score_detail', sa.JSON(), nullable=False),
    sa.Column('calculated_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.Column('algorithm_version', sa.String(length=191), nullable=False),
    sa.ForeignKeyConstraint(['video_snapshot_id'], ['video_snapshots.id'], name='fk_scores_video_snapshot_id'),
    sa.PrimaryKeyConstraint('id'),
    mysql_charset='utf8mb4',
    mysql_collate='utf8mb4_unicode_ci',
    mysql_engine='InnoDB'
    )


def downgrade():
    # 创建或回滚本次迁移的业务表。
    op.drop_table('scores')
    op.drop_table('video_snapshots')
    op.drop_table('users')
    op.drop_table('algorithm_configs')

"""Initial migration

Revision ID: 9374fc8a26df
Revises:
Create Date: 2026-03-18 17:27:24.477960

"""
from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector

# revision identifiers, used by Alembic.
revision = '9374fc8a26df'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # 创建 pgvector 扩展
    op.execute('CREATE EXTENSION IF NOT EXISTS vector')

    # 创建数据源表
    op.create_table(
        'datasources',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('type', sa.String(length=50), nullable=False),
        sa.Column('host', sa.String(length=255), nullable=False),
        sa.Column('port', sa.Integer(), nullable=False),
        sa.Column('database', sa.String(length=100), nullable=True),
        sa.Column('username', sa.String(length=100), nullable=True),
        sa.Column('password_encrypted', sa.String(), nullable=True),
        sa.Column('extra_config', sa.JSON(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_datasources_id'), 'datasources', ['id'], unique=False)
    op.create_index(op.f('ix_datasources_name'), 'datasources', ['name'], unique=True)

    # 创建保存的 SQL 表，包含 embedding 列
    op.create_table(
        'saved_sqls',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('datasource_id', sa.Integer(), nullable=True),
        sa.Column('name', sa.String(length=200), nullable=False),
        sa.Column('sql_text', sa.Text(), nullable=False),
        sa.Column('comment', sa.Text(), nullable=True),
        sa.Column('tags', sa.ARRAY(sa.String()), nullable=True),
        sa.Column('embedding', Vector(1536), nullable=True),
        sa.Column('run_count', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('last_run_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['datasource_id'], ['datasources.id']),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_saved_sqls_id'), 'saved_sqls', ['id'], unique=False)
    # 创建向量索引
    op.execute('CREATE INDEX ix_saved_sqls_embedding ON saved_sqls USING ivfflat (embedding vector_cosine_ops)')

    # 创建导出任务表
    op.create_table(
        'export_tasks',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('datasource_id', sa.Integer(), nullable=True),
        sa.Column('saved_sql_id', sa.Integer(), nullable=True),
        sa.Column('sql_text', sa.Text(), nullable=False),
        sa.Column('export_format', sa.String(length=20), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=True, server_default='pending'),
        sa.Column('file_path', sa.Text(), nullable=True),
        sa.Column('row_count', sa.Integer(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['datasource_id'], ['datasources.id']),
        sa.ForeignKeyConstraint(['saved_sql_id'], ['saved_sqls.id']),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_export_tasks_id'), 'export_tasks', ['id'], unique=False)

    # 创建 AI 配置表
    op.create_table(
        'ai_configs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('provider', sa.String(length=50), nullable=False),
        sa.Column('api_key_encrypted', sa.Text(), nullable=True),
        sa.Column('base_url', sa.String(length=255), nullable=True),
        sa.Column('model_name', sa.String(length=100), nullable=True),
        sa.Column('extra_params', sa.JSON(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_ai_configs_id'), 'ai_configs', ['id'], unique=False)


def downgrade():
    op.drop_index(op.f('ix_ai_configs_id'), table_name='ai_configs')
    op.drop_table('ai_configs')
    op.drop_index(op.f('ix_export_tasks_id'), table_name='export_tasks')
    op.drop_table('export_tasks')
    op.execute('DROP INDEX IF EXISTS ix_saved_sqls_embedding')
    op.drop_index(op.f('ix_saved_sqls_id'), table_name='saved_sqls')
    op.drop_table('saved_sqls')
    op.drop_index(op.f('ix_datasources_name'), table_name='datasources')
    op.drop_index(op.f('ix_datasources_id'), table_name='datasources')
    op.drop_table('datasources')
    op.execute('DROP EXTENSION IF EXISTS vector')
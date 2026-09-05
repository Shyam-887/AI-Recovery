from alembic import op
import sqlalchemy as sa

revision = "0004_payment_method"
down_revision = "0003_webhook_events"
branch_labels = None
depends_on = None

def upgrade():
    op.add_column("payments", sa.Column("payment_method", sa.String(80), nullable=True))
    op.execute("UPDATE payments SET payment_method = 'card' WHERE payment_method IS NULL")
    op.alter_column("payments", "payment_method", nullable=False, server_default="card")

def downgrade():
    op.drop_column("payments", "payment_method")

from alembic import op
import sqlalchemy as sa

revision = "0005_payment_receipt"
down_revision = "0004_payment_method"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("payments", sa.Column("receipt_filename", sa.String(255), nullable=True))
    op.add_column("payments", sa.Column("receipt_path", sa.String(255), nullable=True))


def downgrade():
    op.drop_column("payments", "receipt_path")
    op.drop_column("payments", "receipt_filename")
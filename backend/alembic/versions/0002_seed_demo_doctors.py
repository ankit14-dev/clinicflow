"""seed demo doctors so a fresh install has someone to book with

Revision ID: 0002
"""

import sqlalchemy as sa

from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None

DOCTORS = [
    {
        "full_name": "Dr. Ananya Rao",
        "specialty": "General Medicine",
        "room": "101",
        "email": "ananya.rao@clinicflow.dev",
    },
    {"full_name": "Dr. Vikram Mehta", "specialty": "Cardiology", "room": "204", "email": "vikram.mehta@clinicflow.dev"},
    {"full_name": "Dr. Sara Khan", "specialty": "Pediatrics", "room": "110", "email": "sara.khan@clinicflow.dev"},
    {"full_name": "Dr. Rohan Iyer", "specialty": "Dermatology", "room": "305", "email": "rohan.iyer@clinicflow.dev"},
    {"full_name": "Dr. Meera Nair", "specialty": "Orthopedics", "room": "212", "email": "meera.nair@clinicflow.dev"},
]


def upgrade():
    doctors = sa.table(
        "doctors",
        sa.column("full_name", sa.String),
        sa.column("specialty", sa.String),
        sa.column("room", sa.String),
        sa.column("email", sa.String),
    )
    op.bulk_insert(doctors, DOCTORS)


def downgrade():
    emails = ", ".join(f"'{d['email']}'" for d in DOCTORS)
    op.execute(f"DELETE FROM doctors WHERE email IN ({emails})")

"""Add Phase 2 Live GPS Tracking, Tiered Seats, Operators, and Journey Shares.

Revision ID: f2a8c3d901b2
Revises: e5192c73d81b
Create Date: 2026-11-14 01:25:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "f2a8c3d901b2"
down_revision = "e5192c73d81b"
branch_labels = None
depends_on = None


def upgrade():
    # -------------------------------------------------------------
    # 1. Operators Table
    # -------------------------------------------------------------
    op.create_table(
        "operators",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("code", sa.String(length=40), nullable=False),
        sa.Column("contact_email", sa.String(length=160), nullable=True),
        sa.Column("contact_phone", sa.String(length=20), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name", name="uq_operators_name"),
        sa.UniqueConstraint("code", name="uq_operators_code"),
    )
    op.create_index("ix_operators_name", "operators", ["name"])
    op.create_index("ix_operators_is_active", "operators", ["is_active"])

    # Seed verified 12 fleet operators
    op.execute("""
        INSERT INTO operators (name, code, is_active) VALUES
        ('Bihar State Volvo Express', 'BSVE', true),
        ('Chotanagpur Royal Coach', 'CNRC', true),
        ('Kaveri Airavat Club', 'KVAC', true),
        ('Aravalli Prime Sleeper', 'AVPS', true),
        ('Awadh Shatabdi Volvo', 'AWSV', true),
        ('Rajputana GoldLine', 'RPGL', true),
        ('Bodh Gaya AC Cruiser', 'BGAC', true),
        ('Gomti Night Cruiser', 'GMNC', true),
        ('Sahyadri Shivneri AC', 'SHSN', true),
        ('Nandi Express Shuttle', 'NDES', true),
        ('Magadh Deluxe Travels', 'MGDT', true),
        ('Deccan Queen Coach', 'DCQC', true)
        ON CONFLICT (name) DO NOTHING;
    """)

    # -------------------------------------------------------------
    # 2. Update users Table (Role constraint & operator_id)
    # -------------------------------------------------------------
    op.add_column("users", sa.Column("operator_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_users_operator_id",
        "users",
        "operators",
        ["operator_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_users_operator_id", "users", ["operator_id"])

    # Expand check constraint to allow DRIVER and OPERATOR
    op.drop_constraint("ck_users_valid_role", "users", type_="check")
    op.create_check_constraint(
        "ck_users_valid_role",
        "users",
        "role IN ('USER', 'ADMIN', 'DRIVER', 'OPERATOR')",
    )

    # -------------------------------------------------------------
    # 3. Update buses & trips Tables with operator_id
    # -------------------------------------------------------------
    op.add_column("buses", sa.Column("operator_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_buses_operator_id",
        "buses",
        "operators",
        ["operator_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_buses_operator_id", "buses", ["operator_id"])

    op.add_column("trips", sa.Column("operator_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_trips_operator_id",
        "trips",
        "operators",
        ["operator_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_trips_operator_id", "trips", ["operator_id"])

    # Backfill operator_id on buses and trips from matching operator_name
    op.execute("""
        UPDATE buses b
        SET operator_id = o.id
        FROM operators o
        WHERE b.operator_name = o.name;

        UPDATE trips t
        SET operator_id = o.id
        FROM operators o
        WHERE t.operator_name = o.name;
    """)

    # -------------------------------------------------------------
    # 4. Update trip_seats Table (Tiers, Fares, Amenities, Positions)
    # -------------------------------------------------------------
    op.add_column("trip_seats", sa.Column("seat_tier", sa.String(length=30), nullable=False, server_default="STANDARD"))
    op.add_column("trip_seats", sa.Column("seat_fare", sa.Numeric(precision=10, scale=2), nullable=True))
    op.add_column("trip_seats", sa.Column("amenities", sa.String(length=255), nullable=True))
    op.add_column("trip_seats", sa.Column("position_type", sa.String(length=30), nullable=False, server_default="MIDDLE"))
    
    op.create_check_constraint(
        "ck_trip_seats_valid_tier",
        "trip_seats",
        "seat_tier IN ('STANDARD', 'PREMIUM', 'SLEEPER')",
    )
    op.create_index("ix_trip_seats_seat_tier", "trip_seats", ["seat_tier"])

    # Backfill Seat Tiers and Amenities
    op.execute("""
        -- Front rows (1 and 2) are Premium seats
        UPDATE trip_seats
        SET seat_tier = 'PREMIUM',
            position_type = 'FRONT',
            amenities = 'Extra Legroom, Personal USB Charger, Front View'
        WHERE seat_number LIKE '1%' OR seat_number LIKE '2%';

        -- Sleeper berths
        UPDATE trip_seats
        SET seat_tier = 'SLEEPER',
            amenities = 'Flat Berth, Pillow, Reading Light'
        WHERE seat_type IN ('SLEEPER_LOWER', 'SLEEPER_UPPER');

        -- Standard seats
        UPDATE trip_seats
        SET seat_tier = 'STANDARD',
            amenities = 'Pushback Seat, AC'
        WHERE seat_tier = 'STANDARD' AND amenities IS NULL;
    """)

    # -------------------------------------------------------------
    # 5. Update cities & route_stops with GPS Coordinates
    # -------------------------------------------------------------
    op.add_column("cities", sa.Column("latitude", sa.Float(), nullable=True))
    op.add_column("cities", sa.Column("longitude", sa.Float(), nullable=True))

    op.add_column("route_stops", sa.Column("latitude", sa.Float(), nullable=True))
    op.add_column("route_stops", sa.Column("longitude", sa.Float(), nullable=True))

    # Populate coordinates for all 42 transit hub cities
    op.execute("""
        UPDATE cities SET latitude = 25.5941, longitude = 85.1376 WHERE name = 'Patna';
        UPDATE cities SET latitude = 23.3441, longitude = 85.3096 WHERE name = 'Ranchi';
        UPDATE cities SET latitude = 24.7955, longitude = 85.0002 WHERE name = 'Gaya';
        UPDATE cities SET latitude = 25.3176, longitude = 82.9739 WHERE name = 'Varanasi';
        UPDATE cities SET latitude = 22.5726, longitude = 88.3639 WHERE name = 'Kolkata';
        UPDATE cities SET latitude = 28.6139, longitude = 77.2090 WHERE name = 'Delhi';
        UPDATE cities SET latitude = 26.1209, longitude = 85.3647 WHERE name = 'Muzaffarpur';
        UPDATE cities SET latitude = 25.2425, longitude = 86.9842 WHERE name = 'Bhagalpur';
        UPDATE cities SET latitude = 23.7957, longitude = 86.4304 WHERE name = 'Dhanbad';
        UPDATE cities SET latitude = 22.8046, longitude = 86.2029 WHERE name = 'Jamshedpur';
        UPDATE cities SET latitude = 23.6693, longitude = 86.1511 WHERE name = 'Bokaro';
        UPDATE cities SET latitude = 26.1542, longitude = 85.8918 WHERE name = 'Darbhanga';
        UPDATE cities SET latitude = 26.8467, longitude = 80.9462 WHERE name = 'Lucknow';
        UPDATE cities SET latitude = 26.4499, longitude = 80.3319 WHERE name = 'Kanpur';
        UPDATE cities SET latitude = 25.4358, longitude = 81.8463 WHERE name = 'Prayagraj';
        UPDATE cities SET latitude = 26.7606, longitude = 83.3732 WHERE name = 'Gorakhpur';
        UPDATE cities SET latitude = 26.7271, longitude = 88.3953 WHERE name = 'Siliguri';
        UPDATE cities SET latitude = 23.6739, longitude = 86.9524 WHERE name = 'Asansol';
        UPDATE cities SET latitude = 23.5204, longitude = 87.3119 WHERE name = 'Durgapur';
        UPDATE cities SET latitude = 26.9124, longitude = 75.7873 WHERE name = 'Jaipur';
        UPDATE cities SET latitude = 27.1767, longitude = 78.0081 WHERE name = 'Agra';
        UPDATE cities SET latitude = 12.9716, longitude = 77.5946 WHERE name = 'Bengaluru';
        UPDATE cities SET latitude = 17.3850, longitude = 78.4867 WHERE name = 'Hyderabad';
        UPDATE cities SET latitude = 13.0827, longitude = 80.2707 WHERE name = 'Chennai';
        UPDATE cities SET latitude = 18.5204, longitude = 73.8567 WHERE name = 'Pune';
        UPDATE cities SET latitude = 19.0760, longitude = 72.8777 WHERE name = 'Mumbai';
        UPDATE cities SET latitude = 23.0225, longitude = 72.5714 WHERE name = 'Ahmedabad';
        UPDATE cities SET latitude = 23.2599, longitude = 77.4126 WHERE name = 'Bhopal';
        UPDATE cities SET latitude = 22.7196, longitude = 75.8577 WHERE name = 'Indore';
        UPDATE cities SET latitude = 21.2514, longitude = 81.6296 WHERE name = 'Raipur';
        UPDATE cities SET latitude = 20.2961, longitude = 85.8245 WHERE name = 'Bhubaneswar';
        UPDATE cities SET latitude = 20.4625, longitude = 85.8828 WHERE name = 'Cuttack';
        UPDATE cities SET latitude = 19.8135, longitude = 85.8312 WHERE name = 'Puri';
        UPDATE cities SET latitude = 24.4826, longitude = 86.7001 WHERE name = 'Deoghar';
        UPDATE cities SET latitude = 23.9925, longitude = 85.3637 WHERE name = 'Hazaribagh';
        UPDATE cities SET latitude = 24.1860, longitude = 86.3090 WHERE name = 'Giridih';
        UPDATE cities SET latitude = 25.7771, longitude = 87.4753 WHERE name = 'Purnia';
        UPDATE cities SET latitude = 25.5647, longitude = 84.6669 WHERE name = 'Arrah';
        UPDATE cities SET latitude = 24.9528, longitude = 84.0287 WHERE name = 'Sasaram';
        UPDATE cities SET latitude = 25.5644, longitude = 83.9777 WHERE name = 'Buxar';
        UPDATE cities SET latitude = 25.7796, longitude = 84.7499 WHERE name = 'Chhapra';
        UPDATE cities SET latitude = 26.6469, longitude = 84.9186 WHERE name = 'Motihari';

        -- Update route_stops coordinates matching city_name
        UPDATE route_stops rs
        SET latitude = c.latitude, longitude = c.longitude
        FROM cities c
        WHERE rs.city_name = c.name;
    """)

    # -------------------------------------------------------------
    # 6. Create Table trip_live_locations (With UNIQUE trip_id)
    # -------------------------------------------------------------
    op.create_table(
        "trip_live_locations",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("trip_id", sa.Integer(), nullable=False),
        sa.Column("bus_id", sa.Integer(), nullable=True),
        sa.Column("driver_sequence_number", sa.BigInteger(), nullable=True),
        sa.Column("operator_sequence_number", sa.BigInteger(), nullable=True),
        sa.Column("driver_server_received_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("operator_server_received_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("driver_client_timestamp", sa.DateTime(timezone=True), nullable=True),
        sa.Column("operator_client_timestamp", sa.DateTime(timezone=True), nullable=True),
        sa.Column("driver_latitude", sa.Float(), nullable=True),
        sa.Column("driver_longitude", sa.Float(), nullable=True),
        sa.Column("driver_speed", sa.Float(), nullable=True),
        sa.Column("driver_heading", sa.Float(), nullable=True),
        sa.Column("driver_accuracy", sa.Float(), nullable=True),
        sa.Column("operator_latitude", sa.Float(), nullable=True),
        sa.Column("operator_longitude", sa.Float(), nullable=True),
        sa.Column("operator_speed", sa.Float(), nullable=True),
        sa.Column("operator_heading", sa.Float(), nullable=True),
        sa.Column("operator_accuracy", sa.Float(), nullable=True),
        sa.Column("operator_user_id", sa.Integer(), nullable=True),
        sa.Column("latitude", sa.Float(), nullable=True),
        sa.Column("longitude", sa.Float(), nullable=True),
        sa.Column("speed", sa.Float(), nullable=True),
        sa.Column("heading", sa.Float(), nullable=True),
        sa.Column("accuracy", sa.Float(), nullable=True),
        sa.Column("active_source", sa.String(length=20), nullable=False, server_default="DRIVER"),
        sa.Column("server_received_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["bus_id"], ["buses.id"], name="fk_trip_live_locations_bus_id", ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["operator_user_id"], ["users.id"], name="fk_trip_live_locations_operator_user_id", ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["trip_id"], ["trips.id"], name="fk_trip_live_locations_trip_id", ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("trip_id", name="uq_trip_live_location_trip_id"),
    )
    op.create_index("ix_trip_live_locations_trip_id", "trip_live_locations", ["trip_id"])
    op.create_index("ix_trip_live_locations_is_active", "trip_live_locations", ["is_active"])

    # -------------------------------------------------------------
    # 7. Create Table trip_location_history (Breadcrumbs)
    # -------------------------------------------------------------
    op.create_table(
        "trip_location_history",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("trip_id", sa.Integer(), nullable=False),
        sa.Column("latitude", sa.Float(), nullable=False),
        sa.Column("longitude", sa.Float(), nullable=False),
        sa.Column("speed", sa.Float(), nullable=True),
        sa.Column("heading", sa.Float(), nullable=True),
        sa.Column("source", sa.String(length=20), nullable=False, server_default="DRIVER"),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["trip_id"], ["trips.id"], name="fk_trip_location_history_trip_id", ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_trip_location_history_trip_id", "trip_location_history", ["trip_id"])
    op.create_index("ix_trip_location_history_recorded_at", "trip_location_history", ["recorded_at"])

    # -------------------------------------------------------------
    # 8. Create Table trip_driver_assignments
    # -------------------------------------------------------------
    op.create_table(
        "trip_driver_assignments",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("trip_id", sa.Integer(), nullable=False),
        sa.Column("driver_id", sa.Integer(), nullable=True),
        sa.Column("operator_id", sa.Integer(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("assigned_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["driver_id"], ["users.id"], name="fk_trip_driver_assignments_driver_id", ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["operator_id"], ["operators.id"], name="fk_trip_driver_assignments_operator_id", ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["trip_id"], ["trips.id"], name="fk_trip_driver_assignments_trip_id", ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_trip_driver_assignments_trip_id", "trip_driver_assignments", ["trip_id"])
    op.create_index("ix_trip_driver_assignments_driver_id", "trip_driver_assignments", ["driver_id"])
    op.create_index("ix_trip_driver_assignments_operator_id", "trip_driver_assignments", ["operator_id"])

    # -------------------------------------------------------------
    # 9. Create Table journey_shares (With SHA-256 Hashed Token)
    # -------------------------------------------------------------
    op.create_table(
        "journey_shares",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("booking_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["booking_id"], ["bookings.id"], name="fk_journey_shares_booking_id", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name="fk_journey_shares_user_id", ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token_hash", name="uq_journey_shares_token_hash"),
    )
    op.create_index("ix_journey_shares_booking_id", "journey_shares", ["booking_id"])
    op.create_index("ix_journey_shares_token_hash", "journey_shares", ["token_hash"])
    op.create_index("ix_journey_shares_expires_at", "journey_shares", ["expires_at"])


def downgrade():
    """Forward-only migration policy:
    
    CRITICAL: Downgrade is explicitly disabled in live environments to prevent
    catastrophic deletion of active GPS tracking records, journey shares, and
    weakening of relational constraints.
    
    Use a forward-fix migration or point-in-time backup restore for recovery.
    """
    raise NotImplementedError(
        "Phase 2 migration is forward-only to prevent catastrophic data loss and constraint weakening. "
        "For defect remediation, apply a tested forward-fix migration. "
        "For disaster recovery, execute the verified point-in-time backup restoration procedure."
    )

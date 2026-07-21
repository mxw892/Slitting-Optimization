from decimal import Decimal

from .models import (
    CustomerOrder,
    ParentRollMetadata,
    UsableInterval,
)


# ---------------------------------------------------------------------------
# Parent roll
# ---------------------------------------------------------------------------
# LDF parent rolls are typically 670 mm wide.
#
# Coordinate convention for all transverse positions:
#   DS = 0 mm
#   Coordinates increase from Drive Side toward Control Side.
# ---------------------------------------------------------------------------

parent_roll = ParentRollMetadata(
    roll_id="ROLL-DEMO-001",
    base_width_mm=Decimal("670"),
    available_length_m=Decimal("5000"),
    material="PET",
    film_type="LDF",
    nominal_thickness_um=Decimal("25.5"),
)


# ---------------------------------------------------------------------------
# Usable transverse intervals
# ---------------------------------------------------------------------------
# These represent regions SDI has already declared usable.
#
# region_001:
#   20 mm to 300 mm from DS
#   capacity = 280 mm
#
# region_002:
#   340 mm to 650 mm from DS
#   capacity = 310 mm
#
# Total usable transverse width per run:
#   280 + 310 = 590 mm
#
# The gaps from 0–20 mm, 300–340 mm, and 650–670 mm are unusable.
# ---------------------------------------------------------------------------

usable_intervals = (
    UsableInterval(
        roll_id="ROLL-DEMO-001",
        region_id="region_001",
        start_mm_from_ds=Decimal("20"),
        end_mm_from_ds=Decimal("300"),
    ),
    UsableInterval(
        roll_id="ROLL-DEMO-001",
        region_id="region_002",
        start_mm_from_ds=Decimal("340"),
        end_mm_from_ds=Decimal("650"),
    ),
)


# ---------------------------------------------------------------------------
# Customer orders
# ---------------------------------------------------------------------------
# ORDER-001 and ORDER-002 are compatible:
#   - same material
#   - same film type
#   - same thickness
#   - same requested length
#
# ORDER-003 has a different requested length, so it must be processed in a
# separate compatibility batch.
# ---------------------------------------------------------------------------

orders = (
    CustomerOrder(
        order_id="ORDER-001",
        width_mm=Decimal("140"),
        quantity=14,
        requested_length_m=Decimal("750"),
        material="PET",
        film_type="LDF",
        nominal_thickness_um=Decimal("25.5"),
    ),
    CustomerOrder(
        order_id="ORDER-002",
        width_mm=Decimal("120"),
        quantity=13,
        requested_length_m=Decimal("750"),
        material="PET",
        film_type="LDF",
        nominal_thickness_um=Decimal("25.5"),
    ),
    CustomerOrder(
        order_id="ORDER-003",
        width_mm=Decimal("50"),
        quantity=23,
        requested_length_m=Decimal("500"),
        material="PET",
        film_type="LDF",
        nominal_thickness_um=Decimal("25.5"),
    ),
)


if __name__ == "__main__":
    print("Parent roll")
    print(f"  Roll ID: {parent_roll.roll_id}")
    print(f"  Film type: {parent_roll.film_type}")
    print(f"  Width: {parent_roll.base_width_mm} mm")
    print(f"  Available length: {parent_roll.available_length_m} m")

    print("\nUsable intervals")
    for interval in usable_intervals:
        print(
            f"  {interval.region_id}: "
            f"{interval.start_mm_from_ds}–{interval.end_mm_from_ds} mm from DS "
            f"(capacity: {interval.capacity_mm} mm)"
        )

    print("\nCustomer orders")
    for order in orders:
        print(
            f"  {order.order_id}: "
            f"{order.width_mm} mm × {order.quantity}, "
            f"requested length {order.requested_length_m} m"
        )
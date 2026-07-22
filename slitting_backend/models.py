"""
Author: Matthew Wang

Core domain models for the film slitting optimization backend

All inputs must be translated into these models before batching, allocation, validation, and layour calculations
"""

from dataclasses import dataclass
from decimal import Decimal


SUPPORTED_FILM_TYPES = frozenset({"LDF", "HDC"})


# ---------------------------------------------------------------------------
# validation helper methods
# ---------------------------------------------------------------------------


def _require_non_blank_string(value: str, field_name: str) -> None:

    if not isinstance(value, str):
        raise TypeError(f"{field_name} must be a string")

    if not value.strip():
        raise ValueError(f"{field_name} must not be blank")


def _require_finite_decimal(value: Decimal, field_name: str) -> None:

    if not isinstance(value, Decimal):
        raise TypeError(f"{field_name} must be a Decimal")

    if not value.is_finite():
        raise ValueError(f"{field_name} must be finite")


def _require_positive_decimal(value: Decimal, field_name: str) -> None:

    _require_finite_decimal(value, field_name)

    if value <= 0:
        raise ValueError(f"{field_name} must be greater than zero")


def _require_nonnegative_decimal(value: Decimal, field_name: str) -> None:

    _require_finite_decimal(value, field_name)

    if value < 0:
        raise ValueError(f"{field_name} must be zero or greater")


def _require_supported_film_type(value: str, field_name: str = "film_type") -> None:

    _require_non_blank_string(value, field_name)

    if value not in SUPPORTED_FILM_TYPES:
        allowed = ", ".join(sorted(SUPPORTED_FILM_TYPES))
        raise ValueError(f"{field_name} must be one of: {allowed}")


# ---------------------------------------------------------------------------
# input models
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class ParentRollMetadata:

    roll_id: str
    base_width_mm: Decimal
    available_length_m: Decimal
    material: str
    film_type: str
    nominal_thickness_um: Decimal

    def __post_init__(self) -> None:
        _require_non_blank_string(self.roll_id, "roll_id")
        _require_positive_decimal(self.base_width_mm, "base_width_mm")
        _require_positive_decimal(self.available_length_m, "available_length_m")
        _require_non_blank_string(self.material, "material")
        _require_supported_film_type(self.film_type)
        _require_positive_decimal(self.nominal_thickness_um, "nominal_thickness_um")

# mm from drive side, translated sdi output
# validates interval, validation against parent roll is done in SlittingProblem
@dataclass(frozen=True, slots=True)
class UsableInterval:

    roll_id: str
    region_id: str
    start_mm_from_ds: Decimal
    end_mm_from_ds: Decimal

    def __post_init__(self) -> None:
        _require_non_blank_string(self.roll_id, "roll_id")
        _require_non_blank_string(self.region_id, "region_id")
        _require_nonnegative_decimal(
            self.start_mm_from_ds,
            "start_mm_from_ds",
        )
        _require_positive_decimal(
            self.end_mm_from_ds,
            "end_mm_from_ds",
        )

        if self.start_mm_from_ds >= self.end_mm_from_ds:
            raise ValueError(
                "start_mm_from_ds must be less than end_mm_from_ds"
            )

    @property
    def capacity_mm(self) -> Decimal:
        """Return the exact transverse width available in this interval."""

        return self.end_mm_from_ds - self.start_mm_from_ds

# normalized customer order
@dataclass(frozen=True, slots=True)
class CustomerOrder:

    order_id: str
    width_mm: Decimal
    quantity: int
    requested_length_m: Decimal
    material: str
    film_type: str
    nominal_thickness_um: Decimal

    def __post_init__(self) -> None:
        _require_non_blank_string(self.order_id, "order_id")
        _require_positive_decimal(self.width_mm, "width_mm")

        if not isinstance(self.quantity, int) or isinstance(self.quantity, bool):
            raise TypeError("quantity must be an integer")

        if self.quantity <= 0:
            raise ValueError("quantity must be greater than zero")

        _require_positive_decimal(
            self.requested_length_m,
            "requested_length_m",
        )
        _require_non_blank_string(self.material, "material")
        _require_supported_film_type(self.film_type)
        _require_positive_decimal(self.nominal_thickness_um, "nominal_thickness_um")


# ---------------------------------------------------------------------------
# Compatibility and batching models
# ---------------------------------------------------------------------------

# values that must match for a grouped order
# nominal thickness and film type will be checked in SlittingProblem
# length must be equal since cuts affect all lanes in the same run
@dataclass(frozen=True, slots=True)
class CompatibilityKey:
    requested_length_m: Decimal

    def __post_init__(self) -> None:
        _require_positive_decimal(
            self.requested_length_m,
            "requested_length_m",
        )

    @classmethod
    def from_order(cls, order: CustomerOrder) -> "CompatibilityKey":
        """Construct the run-compatibility key for one customer order."""

        if not isinstance(order, CustomerOrder):
            raise TypeError("order must be a CustomerOrder")

        return cls(
            requested_length_m=order.requested_length_m,
        )

# grouped batch that is further validated by the batch compatability key
@dataclass(frozen=True, slots=True)
class CompatibleBatch:

    batch_id: str
    key: CompatibilityKey
    orders: tuple[CustomerOrder, ...]

    def __post_init__(self) -> None:
        _require_non_blank_string(self.batch_id, "batch_id")

        if not isinstance(self.key, CompatibilityKey):
            raise TypeError("key must be a CompatibilityKey")

        if not isinstance(self.orders, tuple):
            raise TypeError("orders must be a tuple")

        if not self.orders:
            raise ValueError("orders must not be empty")

        seen_order_ids: set[str] = set()

        for order in self.orders:
            if not isinstance(order, CustomerOrder):
                raise TypeError(
                    "orders must contain only CustomerOrder objects"
                )

            if order.order_id in seen_order_ids:
                raise ValueError(
                    f"duplicate order_id in batch: {order.order_id!r}"
                )

            if CompatibilityKey.from_order(order) != self.key:
                raise ValueError(
                    "every order must match the batch compatibility key"
                )

            seen_order_ids.add(order.order_id)


# ---------------------------------------------------------------------------
# Lane-demand model
# ---------------------------------------------------------------------------

# each lane is one order, each LaneDemand will be assigned to a single interval in a single run
@dataclass(frozen=True, slots=True)
class LaneDemand:

    lane_demand_id: str
    source_order_id: str
    width_mm: Decimal
    compatibility_key: CompatibilityKey

    def __post_init__(self) -> None:
        _require_non_blank_string(
            self.lane_demand_id,
            "lane_demand_id",
        )
        _require_non_blank_string(
            self.source_order_id,
            "source_order_id",
        )
        _require_positive_decimal(self.width_mm, "width_mm")

        if not isinstance(self.compatibility_key, CompatibilityKey):
            raise TypeError(
                "compatibility_key must be a CompatibilityKey"
            )

# ---------------------------------------------------------------------------
# Allocation-result models
# ---------------------------------------------------------------------------

# the region the order is assigned to
@dataclass(frozen=True, slots=True)
class LanePlacement:

    lane_demand: LaneDemand
    region_id: str

    def __post_init__(self) -> None:
        if not isinstance(self.lane_demand, LaneDemand):
            raise TypeError(
                "lane_demand must be a LaneDemand"
            )

        _require_non_blank_string(
            self.region_id,
            "region_id",
        )

# the interval within the region in a run
@dataclass(frozen=True, slots=True)
class IntervalAllocation:

    usable_interval: UsableInterval
    placements: tuple[LanePlacement, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.usable_interval, UsableInterval):
            raise TypeError(
                "usable_interval must be a UsableInterval"
            )

        if not isinstance(self.placements, tuple):
            raise TypeError(
                "placements must be a tuple"
            )

        seen_lane_demand_ids: set[str] = set()
        for placement in self.placements:
            if not isinstance(placement, LanePlacement):
                raise TypeError(
                    "placements must contain only LanePlacement objects"
                )

            if (placement.region_id != self.usable_interval.region_id):
                raise ValueError(f"Lane placement region {placement.region_id!r} is not equal to interval region {self.usable_interval.region_id!r}")

            lane_demand_id = (
                placement.lane_demand.lane_demand_id
            )

            if lane_demand_id in seen_lane_demand_ids:
                raise ValueError(
                    f"duplicate lane_demand_id in interval: "
                    f"{lane_demand_id!r}"
                )

            seen_lane_demand_ids.add(lane_demand_id)

        if self.used_width_mm > self.usable_interval.capacity_mm:
            raise ValueError(
                f"Interval {self.usable_interval.region_id!r} exceeds capacity."
            )

    # adds all lane widths within the interval
    @property
    def used_width_mm(self) -> Decimal:
        return sum(
            (
                placement.lane_demand.width_mm
                for placement in self.placements
            ),
            start=Decimal("0"),
        )

    # left over scrap
    @property
    def remaining_width(self) -> Decimal:
        return (
            self.usable_interval.capacity_mm - self.used_width_mm
        )

@dataclass(frozen=True, slots=True)
class ProductionRun:

    run_number: int
    compatibility_key: CompatibilityKey
    interval_allocations: tuple[IntervalAllocation, ...]

    def __post_init__(self) -> None:

        # general checks
        if (
            not isinstance(self.run_number, int)
            or isinstance(self.run_number, bool)
        ):
            raise TypeError("run_number must be an integer")

        if self.run_number <= 0:
            raise ValueError("run_number must be greater than zero")
        if not isinstance(
            self.compatibility_key,
            CompatibilityKey,
        ):
            raise TypeError(
                "compatibility_key must be a CompatibilityKey"
            )
        if not isinstance(self.interval_allocations, tuple):
            raise TypeError(
                "interval_allocationss must be a tuple"
            )
        if not self.interval_allocations:
            raise ValueError(
                "interval_allocationss must not be empty"
            )

        # duplicate tracking
        seen_region_ids: set[str] = set()
        seen_lane_demand_ids: set[str] = set()
        run_roll_id: str | None = None
        total_placement_count = 0

        for allocation in self.interval_allocations:
            if not isinstance(allocation, IntervalAllocation):
                raise TypeError(
                    "interval_allocationss must contain only IntervalAllocation objects"
                )
            region_id = allocation.usable_interval.region_id
            if region_id in seen_region_ids:
                raise ValueError(
                    f"duplicate region_id in run: {region_id!r}"
                )
            seen_region_ids.add(region_id)

            allocation_roll_id = (
                allocation.usable_interval.roll_id
            )

            if run_roll_id is None:
                run_roll_id = allocation_roll_id
            elif allocation_roll_id != run_roll_id:
                raise ValueError(
                    "all interval allocations in a run must belong to the same parent roll"
                )

            for placement in allocation.placements:
                lane = placement.lane_demand
                lane_demand_id = lane.lane_demand_id

                if lane_demand_id in seen_lane_demand_ids:
                    raise ValueError(
                        f"duplicate lane_demand_id in run: {lane_demand_id!r}"
                    )
                seen_lane_demand_ids.add(lane_demand_id)

                if (
                    lane.compatibility_key
                    != self.compatibility_key
                ):
                    raise ValueError(
                        f"lane demand {lane_demand_id!r} "
                        f"does not match the run compatibility key"
                    )
                total_placement_count += 1

        if total_placement_count == 0:
            raise ValueError(
                "production run must contain at least one placement"
            )
            
# ---------------------------------------------------------------------------
# Complete optimization-problem model
# ---------------------------------------------------------------------------

# validated optimization model input
@dataclass(frozen=True, slots=True)
class SlittingProblem:

    parent_roll: ParentRollMetadata
    usable_intervals: tuple[UsableInterval, ...]
    orders: tuple[CustomerOrder, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.parent_roll, ParentRollMetadata):
            raise TypeError(
                "parent_roll must be a ParentRollMetadata"
            )

        if not isinstance(self.usable_intervals, tuple):
            raise TypeError("usable_intervals must be a tuple")

        if not self.usable_intervals:
            raise ValueError("usable_intervals must not be empty")

        if not isinstance(self.orders, tuple):
            raise TypeError("orders must be a tuple")

        if not self.orders:
            raise ValueError("orders must not be empty")

        self._validate_intervals()
        self._validate_orders()

    # validate interval types, roll ownership, IDs, bounds, and overlap
    def _validate_intervals(self) -> None:
        seen_region_ids: set[str] = set()

        for interval in self.usable_intervals:
            if not isinstance(interval, UsableInterval):
                raise TypeError(
                    "usable_intervals must contain only UsableInterval objects"
                )

            if interval.roll_id != self.parent_roll.roll_id:
                raise ValueError(
                    f"interval {interval.region_id!r} belongs to roll "
                    f"{interval.roll_id!r}, expected "
                    f"{self.parent_roll.roll_id!r}"
                )

            if interval.region_id in seen_region_ids:
                raise ValueError(
                    f"duplicate region_id: {interval.region_id!r}"
                )

            if interval.end_mm_from_ds > self.parent_roll.base_width_mm:
                raise ValueError(
                    f"interval {interval.region_id!r} ends at "
                    f"{interval.end_mm_from_ds} mm, which exceeds parent-roll "
                    f"width {self.parent_roll.base_width_mm} mm"
                )

            seen_region_ids.add(interval.region_id)

        ordered_intervals = sorted(
            self.usable_intervals,
            key=lambda interval: (
                interval.start_mm_from_ds,
                interval.end_mm_from_ds,
                interval.region_id,
            ),
        )

        for previous, current in zip(
            ordered_intervals,
            ordered_intervals[1:],
        ):
            if current.start_mm_from_ds < previous.end_mm_from_ds:
                raise ValueError(
                    f"usable intervals {previous.region_id!r} and "
                    f"{current.region_id!r} overlap"
                )

    # ensures orders are compatible with the parent roll
    def _validate_orders(self) -> None:
        
        seen_order_ids: set[str] = set()

        for order in self.orders:
            if not isinstance(order, CustomerOrder):
                raise TypeError(
                    "orders must contain only CustomerOrder objects"
                )

            if order.order_id in seen_order_ids:
                raise ValueError(
                    f"duplicate order_id: {order.order_id!r}"
                )

            if order.material != self.parent_roll.material:
                raise ValueError(
                    f"order {order.order_id!r} material "
                    f"{order.material!r} does not match parent-roll material "
                    f"{self.parent_roll.material!r}"
                )

            if order.film_type != self.parent_roll.film_type:
                raise ValueError(
                    f"order {order.order_id!r} film type "
                    f"{order.film_type!r} does not match parent-roll film type "
                    f"{self.parent_roll.film_type!r}"
                )

            if order.nominal_thickness_um != self.parent_roll.nominal_thickness_um:
                raise ValueError(
                    f"order {order.order_id!r} thickness "
                    f"{order.nominal_thickness_um} µm does not match parent-roll "
                    f"thickness {self.parent_roll.nominal_thickness_um} µm"
                )

            if order.requested_length_m > self.parent_roll.available_length_m:
                raise ValueError(
                    f"order {order.order_id!r} requests "
                    f"{order.requested_length_m} m, which exceeds the "
                    f"available parent-roll length "
                    f"{self.parent_roll.available_length_m} m"
                )

            if not any(
                order.width_mm <= interval.capacity_mm
                for interval in self.usable_intervals
            ):
                raise ValueError(
                    f"order {order.order_id!r} width "
                    f"{order.width_mm} mm does not fit in any usable interval"
                )

            seen_order_ids.add(order.order_id)

    # total available width for a run based on capacity
    @property
    def total_usable_width_mm(self) -> Decimal:

        return sum(
            (
                interval.capacity_mm
                for interval in self.usable_intervals
            ),
            start=Decimal("0"),
        )
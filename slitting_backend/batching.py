"""
Author: Matthew Wang

Takes validated CustomerOrder objects and groups them into batches that can share a run.
"""

from .models import (
    CompatibleBatch,
    CompatibilityKey,
    CustomerOrder,
)

# compatible orders need to have the same length
def group_compatible_orders(
        orders: tuple[CustomerOrder, ...]
) -> tuple[CompatibleBatch, ...]:
    
    if not isinstance(orders, tuple):
        raise TypeError("orders must be a tuple")
    if not orders:
        return ()
    
    grouped_orders: dict[
        CompatibilityKey,
        list[CustomerOrder],
    ] = {}

    seen_order_ids: set[str] = set()

    for order in orders:
        if not isinstance(order, CustomerOrder):
            raise TypeError(
                "Order must contain only CustomerOrder objects"
            )
        if order.order_id in seen_order_ids:  # check for duplicate orders
            raise ValueError(
                f"duplicate order_id: {order.order_id!r}" 
            )
        seen_order_ids.add(order.order_id)

        key = CompatibilityKey.from_order(order)  # create key
        if key not in grouped_orders:
            grouped_orders[key] = []    # add to dictionary if nonexistent

        grouped_orders[key].append(order)   # append order based on key
    ordered_groups = sorted(    # sort by length, ascending
        grouped_orders.items(),
        key=lambda item: item[0].requested_length_m
    )

    batches: list[CompatibleBatch] = []
    for batch_number, (key, batch_orders) in enumerate(
        ordered_groups,
        start=1,
    ):
        batch_id = f"BATCH-{batch_number:03d}"
        batch = CompatibleBatch(
            batch_id=batch_id,
            key=key,
            orders=tuple(batch_orders),
        )
        batches.append(batch)

    return tuple(batches)
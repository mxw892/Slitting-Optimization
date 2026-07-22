'''
Author: Matthew Wang

Take customer order batches and convert into lane demands.
'''

from .models import (
    CompatibleBatch,
    LaneDemand,
)

def lane_demand_conversion(
    batch: CompatibleBatch
) -> tuple[LaneDemand, ...]:
    if not isinstance(batch, CompatibleBatch):
        raise TypeError("batch must be a CompatibleBatch")
    
    lane_demands: list[LaneDemand] = []

    # for each order in the batch, create a LaneDemand object for each requested quantity
    for order in batch.orders:
        for lane_number in range(1, order.quantity+1):
            lane_demand_id = (
                f"{order.order_id}-LANE-{lane_number:04d}"
            )
            lane_demand = LaneDemand(
                lane_demand_id=lane_demand_id,
                source_order_id=order.order_id,  #customer order
                width_mm=order.width_mm,
                compatibility_key=batch.key,
            )
            lane_demands.append(lane_demand)

    return tuple(lane_demands)
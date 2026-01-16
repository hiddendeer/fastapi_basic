from fastapi import APIRouter, HTTPException  


router = APIRouter()
@router.get("/{order_id}")
def get_order_info(order_id: str):
    return {"order_id": order_id}
    
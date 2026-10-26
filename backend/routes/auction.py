from fastapi import APIRouter

from models.schemas import Bid, BidCreate
from services.auction_service import create_bid, list_bids

router = APIRouter()


@router.get("/bids", response_model=list[Bid])
def bids():
    return list_bids()


@router.post("/bids", response_model=Bid)
def submit_bid(payload: BidCreate):
    return create_bid(payload)


@router.post("/bids/{bid_id}/accept")
def accept_bid(bid_id: str):
    from services.auction_service import on_bid_accepted
    res = on_bid_accepted(bid_id)
    if not res.get("success"):
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail=res.get("error", "Failed to accept bid"))
    return res


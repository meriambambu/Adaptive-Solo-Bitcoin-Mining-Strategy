from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


SAT = 100_000_000  # satoshis per BTC


# ── Shared ────────────────────────────────────────────────────────────────────

class UpstreamSpec(BaseModel):
    url: str
    identity: str


# ── Bid (order) ───────────────────────────────────────────────────────────────

class BidCounters(BaseModel):
    model_config = ConfigDict(extra='allow')

    shares_purchased_m: float = 0
    shares_accepted_m: float = 0
    shares_rejected_m: float = 0
    fee_paid_sat: float = 0
    amount_consumed_sat: float = 0


class BidState(BaseModel):
    avg_speed_ph: float = 0        # PH/s
    progress_pct: float = 0        # 0..100
    amount_remaining_sat: float = 0


class SpotBid(BaseModel):
    id: str
    price_sat: float               # satoshi / EH / day
    status: str                    # BID_STATUS_ACTIVE | BID_STATUS_CANCELED | …
    is_current: bool = False
    amount_sat: float = 0          # total budget in satoshi
    speed_limit_ph: float = 0      # PH/s, 0 = unlimited
    dest_upstream: Optional[UpstreamSpec] = None
    memo: str = ""
    created: Optional[str] = None
    fee_rate_pct: float = 0


class BidItem(BaseModel):
    """One price level in the order book. Live API sends camelCase for hashrate/speed fields."""
    model_config = ConfigDict(populate_by_name=True)
    price_sat: float
    amount_sat: float = 0
    hr_matched_ph: float = Field(default=0, alias="hashRateMatched")
    speed_limit_ph: float = Field(default=0, alias="speedLimit")


class AskItem(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    price_sat: float
    hr_matched_ph: float = Field(default=0, alias="hashRateMatched")
    hr_available_ph: float = Field(default=0, alias="hashRateAvailable")


class OrderBook(BaseModel):
    bids: list[BidItem] = []
    asks: list[AskItem] = []


class BidResponseItem(BaseModel):
    bid: SpotBid
    counters_estimate: BidCounters = BidCounters()
    counters_committed: BidCounters = BidCounters()
    state_estimate: BidState = BidState()


class BidsResponse(BaseModel):
    items: list[BidResponseItem] = []


# ── Account ───────────────────────────────────────────────────────────────────

class AccountBalance(BaseModel):
    subaccount: str = ""
    currency: str = "BTC"
    total_balance_sat: int = 0
    available_balance_sat: int = 0
    blocked_balance_sat: int = 0


class BalancesResponse(BaseModel):
    accounts: list[AccountBalance] = []


# ── Requests ──────────────────────────────────────────────────────────────────

class PlaceBidRequest(BaseModel):
    """Frontend sends prices in BTC; client converts to satoshi before calling API."""
    price_btc: float               # BTC / EH / day
    amount_btc: float              # budget in BTC
    speed_limit_ph: float = 0      # PH/s, 0 = unlimited
    pool_url: str
    pool_identity: str             # username / worker
    memo: str = ""


class EditBidRequest(BaseModel):
    bid_id: str
    new_price_btc: Optional[float] = None
    new_amount_btc: Optional[float] = None   # must be >= current amount
    new_speed_limit_ph: Optional[float] = None

"""Pydantic request/response models for API bodies."""
from pydantic import BaseModel


class SetExecutorEnabledBody(BaseModel):
    enabled: bool


class SetDefaultHotkeyBody(BaseModel):
    """SS58 hotkey to use as execute()'s default hotkey."""
    hotkey: str


class StakeBody(BaseModel):
    hotkey: str
    netuid: int
    amount_tao: float


class StakeLimitBody(BaseModel):
    hotkey: str
    netuid: int
    amount_tao: float
    rate_tolerance: float = 0.5
    use_min_tolerance: bool = False
    allow_partial: bool = False


class RemoveStakeBody(BaseModel):
    hotkey: str
    netuid: int
    amount: float | None = None


class RemoveStakeLimitBody(BaseModel):
    hotkey: str
    netuid: int
    amount: float | None = None
    rate_tolerance: float = 0.5
    use_min_tolerance: bool = False
    allow_partial: bool = False


class TransferStakeBody(BaseModel):
    """amount_tao null or omitted = full stake (alpha rao) on origin_netuid for this hotkey."""

    hotkey: str
    origin_netuid: int
    destination_netuid: int
    amount_tao: float | None = None


class MoveStakeBody(BaseModel):
    origin_hotkey: str
    destination_hotkey: str
    origin_netuid: int
    destination_netuid: int
    amount_tao: float | None = None


class WithdrawBody(BaseModel):
    """amount_tao null or omitted = withdraw full native balance on the contract."""
    amount_tao: float | None = None


class FastStakeBody(BaseModel):
    netuid: int
    amount_tao: float


class FastStakeLimitBody(BaseModel):
    netuid: int
    amount_tao: float
    rate_tolerance: float = 0.5
    use_min_tolerance: bool = False


class FastUnstakeBody(BaseModel):
    netuid: int


class FastStakeAndUnstakeBody(BaseModel):
    netuid: int
    amount_tao: float
    limit_price: int | None = None


class CalcToleranceBody(BaseModel):
    tao_amount: float
    netuid: int
    operation: str = "stake"


class ToleranceOffsetBody(BaseModel):
    """Body for PUT /api/tolerance-offset."""
    tolerance_offset: float | str



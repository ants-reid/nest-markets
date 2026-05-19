from enum import Enum


class AssetClass(str, Enum):
    FX = "fx"
    EQUITY = "equity"
    ETF = "etf"
    INDEX_PROXY = "index_proxy"
    COMMODITY_PROXY = "commodity_proxy"
    CRYPTO = "crypto"


class SignalStatus(str, Enum):
    CANDIDATE = "candidate"
    RISK_APPROVED = "risk_approved"
    RISK_BLOCKED = "risk_blocked"
    PENDING_USER_APPROVAL = "pending_user_approval"
    USER_APPROVED = "user_approved"
    USER_REJECTED = "user_rejected"
    PAPER_SUBMITTED = "paper_submitted"
    PAPER_FILLED = "paper_filled"
    LIVE_SUBMITTED = "live_submitted"
    LIVE_FILLED = "live_filled"
    CLOSED = "closed"
    EXPIRED = "expired"


class TradeDirection(str, Enum):
    LONG = "long"
    SHORT = "short"
    FLAT = "flat"


class SetupType(str, Enum):
    TREND_PULLBACK = "trend_pullback"
    BREAKOUT_CONFIRMATION = "breakout_confirmation"
    NEWS_CONTINUATION = "news_continuation"
    NONE = "none"


class RegimeType(str, Enum):
    TREND = "trend"
    RANGE = "range"
    BREAKOUT = "breakout"
    HIGH_VOLATILITY = "high_volatility"
    LOW_VOLATILITY = "low_volatility"
    RISK_ON = "risk_on"
    RISK_OFF = "risk_off"


class HorizonLabel(str, Enum):
    INTRADAY = "intraday"
    ONE_TO_THREE_DAYS = "1_3_days"
    THREE_TO_TEN_DAYS = "3_10_days"


class CatalystType(str, Enum):
    NONE = "none"
    MACRO = "macro"
    EARNINGS = "earnings"
    SECTOR_NEWS = "sector_news"
    COMMODITY_MOVE = "commodity_move"
    CENTRAL_BANK = "central_bank"
    GEOPOLITICS = "geopolitics"


class PromptRole(str, Enum):
    SIGNAL_ENGINE = "signal_engine"
    CATALYST_CLASSIFIER = "catalyst_classifier"
    TRADE_REVIEWER = "trade_reviewer"


class OrderStatus(str, Enum):
    PENDING = "pending"
    NEW = "new"
    ACCEPTED = "accepted"
    FILLED = "filled"
    CANCELED = "canceled"
    REJECTED = "rejected"
    CLOSED = "closed"


class PositionStatus(str, Enum):
    OPEN = "open"
    CLOSED = "closed"


class ApprovalStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"


class ExecutionModeName(str, Enum):
    PAPER = "paper"
    AUTO_PAPER = "auto_paper"
    AUTO_LIVE = "auto_live"
    CONFIRM_LIVE = "confirm_live"
    PENDING_APPROVAL = "pending_approval"


class ModelRegistryStatus(str, Enum):
    CANDIDATE = "candidate"
    ACTIVE = "active"
    ARCHIVED = "archived"
    FAILED = "failed"


class PromotionType(str, Enum):
    CANDIDATE_TO_ACTIVE = "candidate_to_active"
    ACTIVE_TO_ACTIVE = "active_to_active"


class RollbackTrigger(str, Enum):
    AUTOMATIC = "automatic"
    MANUAL = "manual"
    PERFORMANCE_DEGRADATION = "performance_degradation"


class MarketRegimeType(str, Enum):
    RISK_ON = "risk_on"
    RISK_OFF = "risk_off"
    HIGH_VOL = "high_vol"
    LOW_VOL = "low_vol"
    CHOP = "chop"
    TREND = "trend"


class ExecutionOutcomeStatus(str, Enum):
    EXECUTED = "executed"
    BLOCKED = "blocked"
    MISSED = "missed"
    SKIPPED = "skipped"


class FilingEventType(str, Enum):
    EARNINGS = "earnings"
    TEN_K = "10-k"
    TEN_Q = "10-q"
    EIGHT_K = "8-k"
    PROXY = "proxy"
    OTHER = "other"

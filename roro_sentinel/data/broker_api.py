"""
Broker API abstraction layer
Supports multiple brokers with unified interface
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Dict, Optional
from datetime import datetime
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class OrderType(Enum):
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"
    STOP_LIMIT = "stop_limit"


class OrderSide(Enum):
    BUY = "buy"
    SELL = "sell"


class OrderStatus(Enum):
    PENDING = "pending"
    FILLED = "filled"
    PARTIAL = "partial"
    CANCELLED = "cancelled"
    REJECTED = "rejected"


@dataclass
class Order:
    """Represents a trade order"""
    order_id: str
    symbol: str
    side: OrderSide
    order_type: OrderType
    quantity: float
    price: Optional[float] = None
    stop_price: Optional[float] = None
    status: OrderStatus = OrderStatus.PENDING
    filled_quantity: float = 0.0
    average_fill_price: float = 0.0
    timestamp: datetime = None
    broker_order_id: Optional[str] = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()


@dataclass
class Position:
    """Represents an open position"""
    symbol: str
    quantity: float
    entry_price: float
    current_price: float
    unrealized_pnl: float
    realized_pnl: float = 0.0
    margin_used: float = 0.0
    timestamp: datetime = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()


@dataclass
class AccountSummary:
    """Account information"""
    equity: float
    cash: float
    margin_used: float
    margin_available: float
    maintenance_margin: float
    buying_power: float
    unrealized_pnl: float
    realized_pnl: float
    timestamp: datetime = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()


class BrokerAPI(ABC):
    """Abstract base class for broker integrations"""

    @abstractmethod
    async def place_order(self, order: Order) -> Order:
        """Place an order and return updated order with broker ID"""
        pass

    @abstractmethod
    async def cancel_order(self, order_id: str) -> bool:
        """Cancel an order"""
        pass

    @abstractmethod
    async def get_order_status(self, order_id: str) -> Order:
        """Get current status of an order"""
        pass

    @abstractmethod
    async def get_positions(self) -> List[Position]:
        """Get all open positions"""
        pass

    @abstractmethod
    async def get_account_summary(self) -> AccountSummary:
        """Get account information"""
        pass

    @abstractmethod
    async def close_position(self, symbol: str) -> bool:
        """Close a position"""
        pass


class MockBrokerAPI(BrokerAPI):
    """Mock broker for paper trading"""

    def __init__(self, initial_capital: float = 100000.0):
        self.initial_capital = initial_capital
        self.equity = initial_capital
        self.cash = initial_capital
        self.positions: Dict[str, Position] = {}
        self.orders: Dict[str, Order] = {}
        self.order_counter = 0
        logger.info(f"MockBroker initialized with ${initial_capital:,.2f}")

    async def place_order(self, order: Order) -> Order:
        """Simulate order placement"""
        self.order_counter += 1
        order.broker_order_id = f"MOCK{self.order_counter:06d}"
        order.order_id = order.broker_order_id

        # In mock mode, instantly fill market orders
        if order.order_type == OrderType.MARKET:
            order.status = OrderStatus.FILLED
            order.filled_quantity = order.quantity
            order.average_fill_price = order.price if order.price else 0.0

            # Update positions
            await self._update_position(order)

        self.orders[order.order_id] = order
        logger.info(f"Order placed: {order.symbol} {order.side.value} {order.quantity} @ {order.price}")
        return order

    async def _update_position(self, order: Order):
        """Update positions based on filled order"""
        if order.symbol in self.positions:
            pos = self.positions[order.symbol]
            if order.side == OrderSide.BUY:
                new_quantity = pos.quantity + order.filled_quantity
                pos.entry_price = (pos.entry_price * pos.quantity +
                                 order.average_fill_price * order.filled_quantity) / new_quantity
                pos.quantity = new_quantity
            else:  # SELL
                pos.quantity -= order.filled_quantity
                if pos.quantity <= 0:
                    # Position closed
                    del self.positions[order.symbol]
                    return
        else:
            # New position
            if order.side == OrderSide.BUY:
                self.positions[order.symbol] = Position(
                    symbol=order.symbol,
                    quantity=order.filled_quantity,
                    entry_price=order.average_fill_price,
                    current_price=order.average_fill_price,
                    unrealized_pnl=0.0
                )

    async def cancel_order(self, order_id: str) -> bool:
        """Cancel an order"""
        if order_id in self.orders:
            self.orders[order_id].status = OrderStatus.CANCELLED
            logger.info(f"Order cancelled: {order_id}")
            return True
        return False

    async def get_order_status(self, order_id: str) -> Order:
        """Get order status"""
        return self.orders.get(order_id)

    async def get_positions(self) -> List[Position]:
        """Get all positions"""
        return list(self.positions.values())

    async def get_account_summary(self) -> AccountSummary:
        """Get account summary"""
        unrealized_pnl = sum(pos.unrealized_pnl for pos in self.positions.values())
        margin_used = sum(pos.margin_used for pos in self.positions.values())

        return AccountSummary(
            equity=self.equity + unrealized_pnl,
            cash=self.cash,
            margin_used=margin_used,
            margin_available=self.equity - margin_used,
            maintenance_margin=margin_used * 0.5,  # Simplified
            buying_power=(self.equity - margin_used) * 30,  # 30x leverage
            unrealized_pnl=unrealized_pnl,
            realized_pnl=0.0
        )

    async def close_position(self, symbol: str) -> bool:
        """Close a position"""
        if symbol in self.positions:
            pos = self.positions[symbol]
            close_order = Order(
                order_id="",
                symbol=symbol,
                side=OrderSide.SELL if pos.quantity > 0 else OrderSide.BUY,
                order_type=OrderType.MARKET,
                quantity=abs(pos.quantity),
                price=pos.current_price
            )
            await self.place_order(close_order)
            logger.info(f"Position closed: {symbol}")
            return True
        return False


def create_broker_api(config: Dict) -> BrokerAPI:
    """Factory function to create appropriate broker API"""
    mode = config.get('system', {}).get('mode', 'paper')

    if mode in ['paper', 'backtest']:
        initial_capital = config.get('broker', {}).get('initial_capital', 100000.0)
        return MockBrokerAPI(initial_capital=initial_capital)
    elif mode == 'live':
        # In production, would return IBKRBrokerAPI or similar
        logger.warning("Live mode not implemented, using MockBroker")
        return MockBrokerAPI()
    else:
        raise ValueError(f"Unknown mode: {mode}")

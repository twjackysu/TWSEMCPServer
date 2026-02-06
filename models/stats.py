from typing import Optional
from pydantic import Field, AliasChoices
from .base import TWSEBaseModel

class RealTimeStats(TWSEBaseModel):
    """Real-time 5-second trading statistics (MI_5MINS)."""
    
    time: str = Field(validation_alias=AliasChoices('Time', '時間'))
    
    # Accumulated Bid (委買)
    acc_bid_orders: Optional[str] = Field(None, validation_alias=AliasChoices('AccBidOrders', '累積委託買進筆數'))
    acc_bid_volume: Optional[str] = Field(None, validation_alias=AliasChoices('AccBidVolume', '累積委託買進數量'))
    
    # Accumulated Ask (委賣)
    acc_ask_orders: Optional[str] = Field(None, validation_alias=AliasChoices('AccAskOrders', '累積委託賣出筆數'))
    acc_ask_volume: Optional[str] = Field(None, validation_alias=AliasChoices('AccAskVolume', '累積委託賣出數量'))
    
    # Accumulated Transaction (成交)
    acc_transaction: Optional[str] = Field(None, validation_alias=AliasChoices('AccTransaction', '累積成交筆數'))
    acc_trade_volume: Optional[str] = Field(None, validation_alias=AliasChoices('AccTradeVolume', '累積成交數量'))
    acc_trade_value: Optional[str] = Field(None, validation_alias=AliasChoices('AccTradeValue', '累積成交金額'))

from typing import Optional
from pydantic import Field, AliasChoices
from .base import TWSEBaseModel

class MarketInfo(TWSEBaseModel):
    """General market information."""
    date: str = Field(validation_alias=AliasChoices('Date', '日期'), default="")
    stock_code: Optional[str] = Field(None, validation_alias=AliasChoices('Code', '公司代號', '股票代號'))
    stock_name: Optional[str] = Field(None, validation_alias=AliasChoices('Name', '公司名稱', '股票名稱'))
    
    # Price info
    opening_price: Optional[str] = Field(None, validation_alias=AliasChoices('OpeningPrice', '開盤價'))
    highest_price: Optional[str] = Field(None, validation_alias=AliasChoices('HighestPrice', '最高價'))
    lowest_price: Optional[str] = Field(None, validation_alias=AliasChoices('LowestPrice', '最低價'))
    closing_price: Optional[str] = Field(None, validation_alias=AliasChoices('ClosingPrice', '收盤價'))
    change: Optional[str] = Field(None, validation_alias=AliasChoices('Change', '漲跌價差'))
    
    # Volume info
    trade_volume: Optional[str] = Field(None, validation_alias=AliasChoices('TradeVolume', '成交股數'))
    trade_value: Optional[str] = Field(None, validation_alias=AliasChoices('TradeValue', '成交金額'))
    transaction_count: Optional[str] = Field(None, validation_alias=AliasChoices('Transaction', '成交筆數'))

class BrokerInfo(TWSEBaseModel):
    """Broker information."""
    broker_id: str = Field(validation_alias=AliasChoices('券商代號'))
    broker_name: str = Field(validation_alias=AliasChoices('券商名稱'))
    establishment_date: Optional[str] = Field(None, validation_alias='設立日期')
    address: Optional[str] = Field(None, validation_alias='地址')
    tel: Optional[str] = Field(None, validation_alias='電話')

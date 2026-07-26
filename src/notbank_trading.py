# Archivo: src/notbank_trading.py

from decimal import Decimal
from notbank_python_sdk.notbank_client import NotbankClient
from notbank_python_sdk.constants import Side, OrderType, TimeInForce
from notbank_python_sdk.requests_models.send_order import SendOrderRequest
from notbank_python_sdk.models.send_order import SendOrderResponse

def comprar_btc_por_monto_clp(
    client: NotbankClient,
    account_id: int,
    monto_clp: Decimal,
    precio_btc: Decimal,
    symbol: str = "BTCCLP"
) -> SendOrderResponse:
    """
    Crea una orden de COMPRA calculando los BTC exactos en base al monto en CLP.
    """
    cantidad_btc = monto_clp / precio_btc
    instrument = client.get_instrument_by_symbol(symbol)
    
    request = SendOrderRequest(
        instrument=instrument,
        account_id=account_id,
        time_in_force=TimeInForce.GTC,
        side=Side.BUY,
        order_type=OrderType.LIMIT,
        quantity=cantidad_btc,
        limit_price=precio_btc
    )
    return client.send_order(request)

def vender_btc(
    client: NotbankClient,
    account_id: int,
    quantity: Decimal,
    price: Decimal,
    symbol: str = "BTCCLP"
) -> SendOrderResponse:
    """
    Crea una orden limite de VENTA de Bitcoin a CLP.
    """
    instrument = client.get_instrument_by_symbol(symbol)
    
    request = SendOrderRequest(
        instrument=instrument,
        account_id=account_id,
        time_in_force=TimeInForce.GTC,
        side=Side.SELL,
        order_type=OrderType.LIMIT,
        quantity=quantity,
        limit_price=price
    )
    return client.send_order(request)

# Archivo: src/notbank_trading.py

from decimal import Decimal
from notbank_python_sdk.notbank_client import NotbankClient
from notbank_python_sdk.constants import Side, OrderType, TimeInForce, MakerTaker
from notbank_python_sdk.requests_models import SendOrderRequest, GetOrderFeeRequest
from notbank_python_sdk.models.send_order import SendOrderResponse

def comprar_btc_por_monto_clp(
    client: NotbankClient,
    account_id: int,
    monto_clp: Decimal,
    precio_btc: Decimal,
    symbol: str = "BTCCLP"
) -> SendOrderResponse:
    """
    Crea una orden de COMPRA de Bitcoin calculando la cantidad exacta de BTC 
    en base al monto en CLP que se desea gastar[cite: 2].
    
    :param client: Instancia autenticada de NotbankClient
    :param account_id: ID de la cuenta del usuario
    :param monto_clp: Presupuesto en CLP a gastar (Decimal)
    :param precio_btc: Precio limite en CLP por BTC (Decimal)
    :param symbol: Par de mercado (por defecto 'BTCCLP')
    """
    # 1. Calcular la cantidad de BTC a comprar
    cantidad_btc = monto_clp / precio_btc
    
    # 2. Obtener el instrumento correspondiente al par[cite: 1]
    instrument = client.get_instrument_by_symbol(symbol)
    
    # 3. Construir la solicitud de orden de compra[cite: 1]
    request = SendOrderRequest(
        instrument=instrument,
        account_id=account_id,
        time_in_force=TimeInForce.GTC,
        side=Side.BUY,
        order_type=OrderType.LIMIT,
        quantity=cantidad_btc,
        limit_price=precio_btc
    )
    
    # 4. Enviar la orden[cite: 1]
    return client.send_order(request)


def vender_btc(
    client: NotbankClient,
    account_id: int,
    quantity: Decimal,
    price: Decimal,
    symbol: str = "BTCCLP"
) -> SendOrderResponse:
    """
    Crea una orden limite de VENTA de Bitcoin a CLP[cite: 2].
    
    :param client: Instancia autenticada de NotbankClient
    :param account_id: ID de la cuenta del usuario
    :param quantity: Cantidad de BTC a vender (Decimal)
    :param price: Precio limite en CLP por BTC (Decimal)
    :param symbol: Par de mercado (por defecto 'BTCCLP')
    """
    # 1. Obtener el instrumento correspondiente al par[cite: 1]
    instrument = client.get_instrument_by_symbol(symbol)
    
    # 2. Construir la solicitud de orden de venta[cite: 1]
    request = SendOrderRequest(
        instrument=instrument,
        account_id=account_id,
        time_in_force=TimeInForce.GTC,
        side=Side.SELL,
        order_type=OrderType.LIMIT,
        quantity=quantity,
        limit_price=price
    )
    
    # 3. Enviar la orden[cite: 1]
    return client.send_order(request)


def consultar_costo_orden(
    client: NotbankClient, 
    account_id: int, 
    quantity: Decimal, 
    price: Decimal, 
    instrument_id: int = 1, 
    side: Side = Side.BUY,
    maker_taker: MakerTaker = MakerTaker.MAKER
) -> Decimal:
    """
    Consulta el costo exacto de una orden antes de enviarla[cite: 2].
    
    :param client: Instancia autenticada de NotbankClient
    :param account_id: ID de la cuenta del usuario
    :param quantity: Cantidad estimada de la orden (Decimal)
    :param price: Precio estimado de la orden (Decimal)
    :param instrument_id: ID del instrumento (Por defecto 1)
    :param side: Lado de la orden (Side.BUY o Side.SELL)
    :param maker_taker: Tipo de liquidez a aportar o tomar (MakerTaker.MAKER o MakerTaker.TAKER)
    """
    # 1. Construir la solicitud de consulta de tarifa[cite: 1]
    request = GetOrderFeeRequest(
        account_id=account_id,
        instrument_id=instrument_id,  
        quantity=quantity,     
        price=price,    
        order_type=OrderType.LIMIT,
        maker_taker=maker_taker, 
        side=side
    )
    
    # 2. Obtener la respuesta de la API[cite: 1]
    fee_response = client.get_order_fee(request)
    
    # 3. Retornar el costo operativo[cite: 1]
    return fee_response.order_fee

if __name__ == "__main__":
    pass

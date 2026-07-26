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
    en base al monto en CLP que se desea gastar.
    """
    # 1. Calcular la cantidad de BTC a comprar
    cantidad_btc = monto_clp / precio_btc
    
    # 2. Obtener el instrumento correspondiente al par
    instrument = client.get_instrument_by_symbol(symbol)
    
    # 3. Construir la solicitud de orden de compra
    request = SendOrderRequest(
        instrument=instrument,
        account_id=account_id,
        time_in_force=TimeInForce.GTC,
        side=Side.BUY,
        order_type=OrderType.LIMIT,
        quantity=cantidad_btc,
        limit_price=precio_btc
    )
    
    # 4. Enviar la orden
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
    # 1. Obtener el instrumento correspondiente al par
    instrument = client.get_instrument_by_symbol(symbol)
    
    # 2. Construir la solicitud de orden de venta
    request = SendOrderRequest(
        instrument=instrument,
        account_id=account_id,
        time_in_force=TimeInForce.GTC,
        side=Side.SELL,
        order_type=OrderType.LIMIT,
        quantity=quantity,
        limit_price=price
    )
    
    # 3. Enviar la orden
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
    Consulta el costo exacto de una orden antes de enviarla.
    """
    # 1. Construir la solicitud de consulta de tarifa
    request = GetOrderFeeRequest(
        account_id=account_id,
        instrument_id=instrument_id,  
        quantity=quantity,     
        price=price,    
        order_type=OrderType.LIMIT,
        maker_taker=maker_taker, 
        side=side
    )
    
    # 2. Obtener la respuesta de la API
    fee_response = client.get_order_fee(request)
    
    # 3. Retornar el costo operativo
    return fee_response.order_fee


def colocar_take_profit_y_stop_loss(
    client: NotbankClient,
    account_id: int,
    quantity: Decimal,
    precio_compra: Decimal,
    rentabilidad_esperada: Decimal,
    symbol: str = "BTCCLP"
):
    """
    Envía dos órdenes vinculadas (OCO): un Take Profit y un Stop Loss.
    Si una se ejecuta, la otra se cancela automáticamente en el exchange.
    """
    instrument = client.get_instrument_by_symbol(symbol)
    
    # 1. Definir los niveles de precio
    precio_tp = precio_compra * (Decimal("1") + rentabilidad_esperada)
    precio_sl = precio_compra * (Decimal("1") - (rentabilidad_esperada / Decimal("2")))
    
    print(f" -> Configurando OCO: TP @ {precio_tp:.0f} CLP | SL @ {precio_sl:.0f} CLP")
    
    # 2. Enviar Orden Limit de Venta (Take Profit)
    tp_request = SendOrderRequest(
        instrument=instrument,
        account_id=account_id,
        time_in_force=TimeInForce.GTC,
        side=Side.SELL,
        order_type=OrderType.LIMIT,
        quantity=quantity,
        limit_price=precio_tp
    )
    tp_response = client.send_order(tp_request)
    
    # 3. Enviar Orden Stop Market de Venta (Stop Loss) vinculada al TP
    if getattr(tp_response, "status", None) == "Accepted":
        sl_request = SendOrderRequest(
            instrument=instrument,
            account_id=account_id,
            time_in_force=TimeInForce.GTC,
            side=Side.SELL,
            order_type=OrderType.STOP_MARKET,
            quantity=quantity,
            stop_price=precio_sl,
            order_id_oco=tp_response.order_id
        )
        sl_response = client.send_order(sl_request)
        
        print(f" -> [OCO ACTIVADO] TP ID: {tp_response.order_id} | SL ID: {sl_response.order_id}")
        return True
    else:
        print(f" -> [ERROR] Falló la creación del Take Profit: {getattr(tp_response, 'errormsg', 'Error desconocido')}")
        return False


if __name__ == "__main__":
    pass

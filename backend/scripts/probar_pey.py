"""Prueba de conexión con pey: crea un cobro CoDi real y guarda el QR como imagen.

Uso, desde backend/:

    uv run python scripts/probar_pey.py             # cobro de $0.01
    uv run python scripts/probar_pey.py --esperar   # además espera a que lo pagues

El dinero pagado a la CLABE de prueba de pey no se devuelve: usa solo $0.01.
"""

import argparse
import asyncio
import base64
import sys
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import RAIZ_BACKEND, obtener_configuracion  # noqa: E402
from app.pey import ClientePey, ErrorPey  # noqa: E402

SALIDA = RAIZ_BACKEND / ".tmp" / "qr-prueba.png"


async def principal() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--monto", type=Decimal, default=Decimal("0.01"))
    parser.add_argument("--concepto", default="Prueba PAGO FACIL")
    parser.add_argument("--minutos", type=int, default=6, help="vigencia del QR (mínimo 6)")
    parser.add_argument("--esperar", action="store_true", help="espera el pago hasta que venza")
    args = parser.parse_args()

    config = obtener_configuracion()
    if args.monto > config.monto_maximo:
        print(f"Monto mayor al máximo permitido (${config.monto_maximo}).")
        return 2

    pey = ClientePey(config.pey_api_base_url, config.pey_api_key.get_secret_value())
    try:
        print(f"Creando cobro de ${args.monto} en {config.pey_api_base_url} ...")
        vigencia = max(args.minutos, 6) * 60
        qr = await pey.crear_qr(args.monto, args.concepto, vigencia, "1", {"origen": "probar_pey"})
        print(f"OK. pey creó el cobro. codiQrId = {qr.id}")

        if qr.qr_image:
            SALIDA.parent.mkdir(exist_ok=True)
            SALIDA.write_bytes(base64.b64decode(qr.qr_image))
            print(f"QR guardado en {SALIDA} (vigencia: {vigencia // 60} min).")
            print("Escanéalo desde la app de tu banco, opción CoDi. La cámara normal no sirve.")
        else:
            print("pey no devolvió la imagen. Contenido del QR:")
            print(qr.qr_string)

        if not args.esperar:
            return 0
        print("Esperando el pago (Ctrl+C para salir) ...")
        for _ in range(vigencia // 3):
            await asyncio.sleep(3)
            pagadas = [t for t in await pey.transacciones_qr(qr.id) if t.get("status") == "PAID"]
            if pagadas:
                print(f"PAGADO. ${pagadas[0].get('amount')} transacción {pagadas[0].get('id')}")
                return 0
        print(f"No llegó ningún pago en {vigencia // 60} minutos; el QR ya venció.")
        return 1
    except ErrorPey as error:
        print(f"ERROR de pey: estado={error.estado} tipo={error.tipo}")
        print(f"  {error.mensaje}")
        if error.request_id:
            print(f"  requestId: {error.request_id}")
        return 1
    finally:
        await pey.cerrar()


if __name__ == "__main__":
    sys.exit(asyncio.run(principal()))

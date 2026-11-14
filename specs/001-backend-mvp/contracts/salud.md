# Contrato: salud del servidor

## 1. Método, ruta y propósito

`GET /salud`: comprobar en segundos que el servidor responde y tiene sus credenciales, sin mostrarlas.

## 2. Requisitos

RF-036, RF-038.

## 3. Petición

Sin parámetros.

## 4. Respuestas

| Código | Cuándo | Cuerpo |
|---|---|---|
| 200 | Siempre que el servidor responde | Tabla de abajo |

| Campo | Tipo | Requisitos |
|---|---|---|
| `estado` | `"ok"` | RF-038 |
| `llave_pey` | booleano: `true` si la llave de pey no está vacía | RF-038 |
| `secreto_aviso_pey` | booleano: `true` si el secreto del aviso no está vacío | RF-038 |

## 5. Ejemplo

```json
{ "estado": "ok", "llave_pey": true, "secreto_aviso_pey": false }
```

## 6. Seguridad

- Solo devuelve booleanos; nunca los valores, ni partes de ellos (RF-036).
- No llama a pey: que la llave exista no prueba que pey la acepte. Eso se comprueba con `scripts/probar_pey.py` (quickstart).
- El prototipo devuelve `pey_api_key` y `pey_webhook_secret`; se renombran a español (research R-10).

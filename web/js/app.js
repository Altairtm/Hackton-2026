import { mostrar_teclado } from "./vistas.js";

const servidor = window.PAGO_FACIL.servidor;

const estado = {
  vista: "teclado",
  monto: "",
  concepto: "",
  mensaje: "",
  en_pantalla: null,
  accion_en_curso: null,
  sonido_desbloqueado: false,
  qr_reabierto: false,
};

mostrar_teclado(estado);

export { servidor };

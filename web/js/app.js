import { desfase, formato, restante } from "./cuenta.js";
import { Escuchas } from "./escucha.js";
import { desbloquear } from "./sonido.js";
import { cancelar_cobro, crear_cobro } from "./servidor.js";
import { aplicar_tecla } from "./teclado.js";
import {
  fijar_mostrar_qr,
  mostrar_aviso_anterior,
  mostrar_error,
  mostrar_generando,
  mostrar_pagado,
  mostrar_qr,
  mostrar_reconectando,
  mostrar_teclado,
  mostrar_vencido,
  ocultar_espera,
} from "./vistas.js";

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

/** @type {number} */
let cuenta_id = 0;

/** @type {object | null} */
let cobro_actual = null;

/** @type {object | null} */
let ultimo_pago = null;

/** @type {number} */
let diferencia_cuenta = 0;

/** @type {string} */
let mensaje_cancelar = "";

/**
 * @param {object} cobro
 * @param {object} pago
 * @param {boolean} vigente
 * @returns {void}
 */
function pintar_pagado(cobro, pago, vigente) {
  mostrar_pagado({
    monto_recibido: pago.monto_recibido,
    concepto: typeof cobro.concepto === "string" ? cobro.concepto : "",
    monto_pedido: cobro.monto,
    monto_distinto: Boolean(pago.monto_distinto),
    numero: pago.numero,
    total: cobro.total_recibido,
    vigente,
  });
}

const escuchas = new Escuchas({
  pagado(pago, cobro) {
    cobro_actual = cobro;
    ultimo_pago = pago;
    estado.vista = "pago_recibido";
    estado.qr_reabierto = false;
    const segundos = restante(cobro, diferencia_cuenta, Date.now() / 1000);
    pintar_pagado(cobro, pago, segundos >= 1);
  },
  anterior(pago, cobro) {
    mostrar_aviso_anterior(
      pago.monto_recibido,
      typeof cobro.concepto === "string" ? cobro.concepto : "",
    );
  },
  cancelado() {
    if (estado.accion_en_curso === "cancelando") {
      return;
    }
    volver_al_teclado();
  },
  reconectando(visible) {
    mostrar_reconectando(visible);
  },
  vencido(cobro) {
    cobro_actual = cobro;
    estado.vista = "qr_vencido";
    mostrar_vencido(cobro, true);
  },
  error() {
    parar_cuenta();
    cobro_actual = null;
    estado.vista = "error";
    estado.en_pantalla = null;
    mostrar_error();
  },
  fin() {
    ocultar_espera();
  },
});

mostrar_teclado(estado);
conectar();

/**
 * @returns {void}
 */
function conectar() {
  const raiz = document.getElementById("vistas");
  if (!raiz) {
    return;
  }
  for (const boton of raiz.querySelectorAll('[data-prueba^="tecla-"]')) {
    boton.addEventListener("click", al_tecla);
  }
  const concepto = raiz.querySelector('[data-prueba="concepto"]');
  if (concepto instanceof HTMLInputElement) {
    concepto.addEventListener("input", () => {
      estado.concepto = concepto.value;
    });
  }
  const cobrar = raiz.querySelector('[data-prueba="cobrar"]');
  if (cobrar) {
    cobrar.addEventListener("click", () => {
      void al_cobrar();
    });
  }
  for (const boton of raiz.querySelectorAll('[data-prueba="nuevo-cobro"]')) {
    boton.addEventListener("click", al_nuevo);
  }
  const libre = raiz.querySelector('[data-prueba="monto-libre"]');
  if (libre) {
    libre.addEventListener("click", () => {
      void pedir_cobro(null);
    });
  }
  const otra_vez = raiz.querySelector('[data-prueba="mostrar-qr"]');
  if (otra_vez) {
    otra_vez.addEventListener("click", al_mostrar_qr);
  }
  const cancelar = raiz.querySelector('[data-prueba="cancelar"]');
  if (cancelar) {
    cancelar.addEventListener("click", () => {
      void al_cancelar();
    });
  }
}

/**
 * Nuevo cobro vacía el teclado y sigue escuchando el cobro como anterior
 * (spec 002, RF-041, RF-042, RF-043).
 *
 * @returns {void}
 */
function al_nuevo() {
  volver_al_teclado();
}

/**
 * Deja el cobro en pantalla como anterior y vuelve al teclado vacío
 * (spec 002, RF-042, RF-043, RF-048, RF-049, RF-074).
 *
 * @returns {void}
 */
function volver_al_teclado() {
  escuchas.pasar_a_anterior();
  parar_cuenta();
  cobro_actual = null;
  estado.vista = "teclado";
  estado.monto = "";
  estado.concepto = "";
  estado.mensaje = "";
  estado.en_pantalla = null;
  estado.qr_reabierto = false;
  ultimo_pago = null;
  mensaje_cancelar = "";
  mostrar_reconectando(false);
  mostrar_teclado(estado);
}

/**
 * Pide cancelar el cobro pendiente. Mientras responde, el botón no se repite
 * (spec 002, RF-047, RF-050, RF-072, RF-073).
 *
 * @returns {Promise<void>}
 */
async function al_cancelar() {
  if (estado.accion_en_curso || estado.vista !== "qr" || !cobro_actual) {
    return;
  }
  if (cobro_actual.estado !== "pendiente") {
    return;
  }
  const id = cobro_actual.id;
  estado.accion_en_curso = "cancelando";
  mensaje_cancelar = "";
  pintar_qr_actual();
  const resultado = await cancelar_cobro(id);
  if (estado.accion_en_curso !== "cancelando") {
    return;
  }
  estado.accion_en_curso = null;
  if (resultado.cobro) {
    volver_al_teclado();
    return;
  }
  mensaje_cancelar = resultado.mensaje ?? "";
  if (estado.vista === "qr" && cobro_actual) {
    pintar_qr_actual();
  }
}

/**
 * @param {Event} evento
 * @returns {void}
 */
function al_tecla(evento) {
  const boton = evento.currentTarget;
  if (!(boton instanceof HTMLElement)) {
    return;
  }
  const nombre = boton.getAttribute("data-prueba") ?? "";
  estado.monto = aplicar_tecla(estado.monto, nombre.slice("tecla-".length));
  estado.mensaje = "";
  estado.vista = "teclado";
  mostrar_teclado(estado);
}

/**
 * Pide el cobro. El segundo toque se ignora mientras el primero no termina
 * (spec 002, RF-009, RF-010, RF-011, RF-014, RF-025).
 *
 * @returns {void}
 */
function al_cobrar() {
  void pedir_cobro(Number(estado.monto));
}

/**
 * Cobrar y Monto libre comparten el bloqueo mientras el servidor crea (spec 002, RF-008, RF-011).
 *
 * @param {number | null} monto
 * @returns {Promise<void>}
 */
async function pedir_cobro(monto) {
  if (estado.accion_en_curso) {
    return;
  }
  desbloquear();
  estado.sonido_desbloqueado = true;
  estado.accion_en_curso = "creando";
  estado.vista = "generando";
  mostrar_generando(estado);
  const resultado = await crear_cobro(monto, estado.concepto);
  estado.accion_en_curso = null;
  if (resultado.cobro) {
    estado.en_pantalla = resultado.cobro.id;
    estado.vista = "qr";
    empezar_cuenta(resultado.cobro);
    escuchas.poner_en_pantalla(resultado.cobro);
    return;
  }
  estado.mensaje = resultado.mensaje ?? "";
  estado.vista = "teclado";
  parar_cuenta();
  mostrar_teclado(estado);
}

/**
 * Vuelve a la vista QR del mismo cobro mientras siga vigente (spec 002, RF-069, RF-070).
 *
 * @returns {void}
 */
function al_mostrar_qr() {
  const actual = cobro_actual;
  if (!actual || !ultimo_pago || estado.vista !== "pago_recibido") {
    return;
  }
  const segundos = restante(actual, diferencia_cuenta, Date.now() / 1000);
  if (segundos < 1) {
    return;
  }
  estado.qr_reabierto = true;
  estado.vista = "qr";
  pintar_qr_actual();
}

/**
 * @returns {void}
 */
function parar_cuenta() {
  if (cuenta_id !== 0) {
    window.clearInterval(cuenta_id);
    cuenta_id = 0;
  }
}

/**
 * Pinta el QR del cobro en pantalla, con Cancelar cobro si sigue pendiente
 * (spec 002, RF-046, RF-050, RF-072).
 *
 * @returns {void}
 */
function pintar_qr_actual() {
  const actual = cobro_actual;
  if (!actual) {
    return;
  }
  const segundos = restante(actual, diferencia_cuenta, Date.now() / 1000);
  mostrar_qr({
    qr_imagen: typeof actual.qr_imagen === "string" ? actual.qr_imagen : "",
    monto: actual.monto,
    concepto: typeof actual.concepto === "string" ? actual.concepto : "",
    cuenta: formato(segundos),
    pendiente: actual.estado === "pendiente",
    cancelando: estado.accion_en_curso === "cancelando",
    mensaje_cancelar,
  });
}

/**
 * @param {object} cobro
 * @returns {boolean}
 */
function tiene_pagos(cobro) {
  return Array.isArray(cobro.pagos) && cobro.pagos.length > 0;
}

/**
 * Fija el desfase al recibir el cobro. Recalcularlo en cada tick dejaría la cuenta quieta
 * (spec 002, RF-018, RF-019, DP-8).
 *
 * @param {{ qr_imagen?: string, monto?: number | null, concepto?: string, expira_en: number, hora_servidor?: number | null }} cobro
 * @returns {void}
 */
function empezar_cuenta(cobro) {
  parar_cuenta();
  cobro_actual = cobro;
  diferencia_cuenta = desfase(cobro, Date.now() / 1000);
  const pintar = () => {
    const actual = cobro_actual;
    if (!actual) {
      return;
    }
    const segundos = restante(actual, diferencia_cuenta, Date.now() / 1000);
    // 0:00 es lo que se ve cuando queda menos de un segundo (RF-035, RF-071).
    if (segundos < 1 && estado.qr_reabierto && ultimo_pago) {
      estado.qr_reabierto = false;
      estado.vista = "pago_recibido";
      pintar_pagado(actual, ultimo_pago, false);
      return;
    }
    if (segundos < 1 && !tiene_pagos(actual) && estado.vista === "qr") {
      parar_cuenta();
      estado.vista = "qr_vencido";
      mostrar_vencido(actual, true);
      return;
    }
    if (estado.vista === "qr") {
      pintar_qr_actual();
    }
    if (estado.vista === "pago_recibido") {
      fijar_mostrar_qr(segundos >= 1);
    }
  };
  pintar();
  cuenta_id = window.setInterval(pintar, 250);
}

export { servidor };

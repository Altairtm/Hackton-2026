import { desfase, formato, restante } from "./cuenta.js";
import { Escuchas } from "./escucha.js";
import { desbloquear } from "./sonido.js";
import { crear_cobro } from "./servidor.js";
import { aplicar_tecla } from "./teclado.js";
import {
  mostrar_generando,
  mostrar_pagado,
  mostrar_qr,
  mostrar_reconectando,
  mostrar_teclado,
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

const escuchas = new Escuchas({
  pagado(pago, cobro) {
    parar_cuenta();
    estado.vista = "pago_recibido";
    mostrar_pagado({
      monto_recibido: pago.monto_recibido,
      concepto: typeof cobro.concepto === "string" ? cobro.concepto : "",
      monto_pedido: cobro.monto,
      monto_distinto: Boolean(pago.monto_distinto),
    });
  },
  reconectando(visible) {
    mostrar_reconectando(visible);
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
 * @returns {Promise<void>}
 */
async function al_cobrar() {
  if (estado.accion_en_curso) {
    return;
  }
  desbloquear();
  estado.sonido_desbloqueado = true;
  estado.accion_en_curso = "creando";
  estado.vista = "generando";
  mostrar_generando(estado);
  const resultado = await crear_cobro(Number(estado.monto), estado.concepto);
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
 * @returns {void}
 */
function parar_cuenta() {
  if (cuenta_id !== 0) {
    window.clearInterval(cuenta_id);
    cuenta_id = 0;
  }
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
  const diferencia = desfase(cobro, Date.now() / 1000);
  const pintar = () => {
    const segundos = restante(cobro, diferencia, Date.now() / 1000);
    mostrar_qr({
      qr_imagen: typeof cobro.qr_imagen === "string" ? cobro.qr_imagen : "",
      monto: cobro.monto,
      concepto: typeof cobro.concepto === "string" ? cobro.concepto : "",
      cuenta: formato(segundos),
    });
  };
  pintar();
  cuenta_id = window.setInterval(pintar, 250);
}

export { servidor };

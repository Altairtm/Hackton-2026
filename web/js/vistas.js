import { cobrar_activo } from "./teclado.js";

const TEXTO_GENERANDO = "Generando QR…";
let listas = false;

/**
 * Deja en el DOM el Teclado y Generando QR, ocultos hasta que una vista los muestre
 * (spec 002, RF-001, RF-010).
 */
function asegurar() {
  if (listas) {
    return;
  }
  const raiz = document.getElementById("vistas");
  if (!raiz) {
    return;
  }
  listas = true;
  raiz.append(crear_teclado(), crear_generando());
}

/**
 * @returns {HTMLElement}
 */
function crear_teclado() {
  const vista = document.createElement("section");
  vista.setAttribute("data-prueba", "vista-teclado");
  vista.hidden = true;

  const monto = document.createElement("p");
  monto.setAttribute("data-prueba", "monto");
  vista.append(monto);

  const teclas = document.createElement("div");
  teclas.className = "teclas";
  for (const digito of ["1", "2", "3", "4", "5", "6", "7", "8", "9"]) {
    teclas.append(crear_tecla(`tecla-${digito}`, digito));
  }
  teclas.append(crear_tecla("tecla-punto", "."));
  teclas.append(crear_tecla("tecla-0", "0"));
  teclas.append(crear_tecla("tecla-borrar", "Borrar"));
  vista.append(teclas);

  const concepto = document.createElement("input");
  concepto.type = "text";
  concepto.setAttribute("data-prueba", "concepto");
  concepto.setAttribute("maxlength", "40");
  vista.append(concepto);

  const cobrar = document.createElement("button");
  cobrar.type = "button";
  cobrar.setAttribute("data-prueba", "cobrar");
  cobrar.textContent = "Cobrar";
  vista.append(cobrar);

  const mensaje = document.createElement("p");
  mensaje.setAttribute("data-prueba", "mensaje");
  vista.append(mensaje);
  return vista;
}

/**
 * @param {string} nombre
 * @param {string} texto
 * @returns {HTMLButtonElement}
 */
function crear_tecla(nombre, texto) {
  const boton = document.createElement("button");
  boton.type = "button";
  boton.setAttribute("data-prueba", nombre);
  boton.textContent = texto;
  return boton;
}

/**
 * @returns {HTMLElement}
 */
function crear_generando() {
  const vista = document.createElement("section");
  vista.setAttribute("data-prueba", "vista-generando");
  vista.hidden = true;

  const texto = document.createElement("p");
  texto.setAttribute("data-prueba", "generando");
  texto.textContent = TEXTO_GENERANDO;

  const indicador = document.createElement("span");
  indicador.className = "cargando";
  indicador.setAttribute("aria-hidden", "true");
  vista.append(texto, indicador);
  return vista;
}

/**
 * @param {string} nombre
 */
function mostrar_solo(nombre) {
  const raiz = document.getElementById("vistas");
  if (!raiz) {
    return;
  }
  for (const nodo of raiz.children) {
    if (!(nodo instanceof HTMLElement) || !nodo.hasAttribute("data-prueba")) {
      continue;
    }
    nodo.hidden = nodo.getAttribute("data-prueba") !== nombre;
  }
}

/**
 * Pinta la vista Teclado solo con texto y atributos fijos
 * (spec 002, RF-001, RF-002, RF-005, RF-006, RF-060, RF-077).
 *
 * @param {{ monto?: string, concepto?: string, mensaje?: string }} estado
 * @returns {void}
 */
export function mostrar_teclado(estado) {
  asegurar();
  const monto = document.querySelector('[data-prueba="monto"]');
  const concepto = document.querySelector('[data-prueba="concepto"]');
  const cobrar = document.querySelector('[data-prueba="cobrar"]');
  const mensaje = document.querySelector('[data-prueba="mensaje"]');
  if (monto) {
    monto.textContent = `$${estado.monto ?? ""}`;
  }
  if (concepto instanceof HTMLInputElement) {
    concepto.value = estado.concepto ?? "";
  }
  if (cobrar instanceof HTMLButtonElement) {
    cobrar.disabled = !cobrar_activo(estado.monto ?? "");
  }
  if (mensaje) {
    mensaje.textContent = estado.mensaje ?? "";
  }
  mostrar_solo("vista-teclado");
}

/**
 * Pinta Generando QR y oculta el resto (spec 002, RF-010, RF-077).
 *
 * @param {object} _estado
 * @returns {void}
 */
export function mostrar_generando(_estado) {
  asegurar();
  const generando = document.querySelector('[data-prueba="generando"]');
  if (generando) {
    generando.textContent = TEXTO_GENERANDO;
  }
  mostrar_solo("vista-generando");
}

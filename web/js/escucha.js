import { Avisados } from "./avisados.js";
import { desfase } from "./cuenta.js";
import { mantener_encendida } from "./pantalla.js";
import { ver_cobro } from "./servidor.js";
import { sonar, vibrar } from "./sonido.js";

const CONSULTA_MS = 3_000;
const REINTENTO_MS = 15_000;

/**
 * Un cobro en escucha: canal, consulta cada 3 s y reintento cada 15 s
 * (spec 002, RF-020, RF-030, RF-031, RF-033, RF-034).
 */
export class Escucha {
  /**
   * @param {string} id
   * @param {object} cobro
   * @param {boolean} con_canal
   * @param {(aviso: { tipo: string, escucha: Escucha, cobro?: object }) => void} al_recibir
   */
  constructor(id, cobro, con_canal, al_recibir) {
    this.id = id;
    this.cobro = cobro;
    this.desfase = desfase(cobro, Date.now() / 1000);
    /** @type {"sin_canal" | "abriendo" | "abierto" | "cortado" | "cerrado"} */
    this.canal = con_canal ? "abriendo" : "sin_canal";
    this.consultando = false;
    this.es_anterior = false;
    this._al_recibir = al_recibir;
    /** @type {EventSource | null} */
    this._fuente = null;
    /** @type {number} */
    this._consulta = 0;
    /** @type {number} */
    this._reintento = 0;
    this._terminada = false;
    if (con_canal) {
      this._abrir_canal();
    } else {
      this._consultar_luego(CONSULTA_MS);
    }
  }

  /**
   * @returns {void}
   */
  _abrir_canal() {
    if (this._fuente) {
      const anterior = this._fuente;
      this._fuente = null;
      anterior.close();
    }
    this.canal = "abriendo";
    const url = `${window.PAGO_FACIL.servidor}/api/cobros/${this.id}/eventos`;
    const fuente = new EventSource(url);
    this._fuente = fuente;
    fuente.addEventListener("open", () => {
      if (this._fuente !== fuente || this._terminada) {
        return;
      }
      this.canal = "abierto";
      this._parar_consulta();
      this._parar_reintento();
      console.info(`escucha ${this.id}: abierto`);
      this._al_recibir({ tipo: "abierto", escucha: this });
    });
    fuente.addEventListener("estado", (evento) => {
      this._aplicar_evento(fuente, evento);
    });
    fuente.addEventListener("pago", (evento) => {
      if (this._fuente !== fuente || this._terminada) {
        return;
      }
      const datos = leer_json(evento);
      if (datos && typeof datos === "object" && datos.cobro) {
        this._aplicar(datos.cobro);
      }
    });
    fuente.addEventListener("vencido", (evento) => {
      if (this._fuente !== fuente || this._terminada) {
        return;
      }
      const datos = leer_json(evento);
      if (datos) {
        this.cobro = datos;
      }
      this._al_recibir({ tipo: "vencido", escucha: this, cobro: datos || this.cobro });
    });
    fuente.addEventListener("fin", () => {
      if (this._fuente !== fuente || this._terminada) {
        return;
      }
      console.info(`escucha ${this.id}: fin`);
      this._al_recibir({ tipo: "fin", escucha: this });
      this.terminar();
    });
    fuente.addEventListener("error", () => {
      if (this._fuente !== fuente || this._terminada) {
        return;
      }
      this.canal = "cortado";
      console.info(`escucha ${this.id}: cortado`);
      this._al_recibir({ tipo: "cortado", escucha: this });
      this._consultar_luego(CONSULTA_MS);
      // Solo el cierre definitivo (HTTP distinto de 200) se reabre a los 15 s.
      // Un corte de red lo reintenta el propio navegador (R-5, RF-034).
      if (fuente.readyState === EventSource.CLOSED) {
        this._programar_reintento();
      }
    });
  }

  /**
   * @param {EventSource} fuente
   * @param {Event} evento
   * @returns {void}
   */
  _aplicar_evento(fuente, evento) {
    if (this._fuente !== fuente || this._terminada) {
      return;
    }
    const datos = leer_json(evento);
    if (datos) {
      this._aplicar(datos);
    }
  }

  /**
   * @param {object} cobro
   * @returns {void}
   */
  _aplicar(cobro) {
    if (this._terminada) {
      return;
    }
    this.cobro = cobro;
    this.desfase = desfase(cobro, Date.now() / 1000);
    this._al_recibir({ tipo: "cobro", escucha: this, cobro });
  }

  /**
   * @param {number} espera
   * @returns {void}
   */
  _consultar_luego(espera) {
    if (this._terminada || this.canal === "abierto") {
      return;
    }
    window.clearTimeout(this._consulta);
    this.consultando = true;
    this._consulta = window.setTimeout(() => {
      void this._consultar();
    }, espera);
  }

  /**
   * @returns {Promise<void>}
   */
  async _consultar() {
    if (this._terminada || this.canal === "abierto") {
      return;
    }
    console.info(`escucha ${this.id}: consulta`);
    const resultado = await ver_cobro(this.id);
    if (this._terminada || this.canal === "abierto") {
      return;
    }
    if (resultado.cobro) {
      const cobro = resultado.cobro;
      if (cobro.hora_servidor != null && cobro.hora_servidor >= cobro.fin_ventana) {
        console.info(`escucha ${this.id}: fin`);
        this._al_recibir({ tipo: "fin", escucha: this, cobro });
        this.terminar();
        return;
      }
      this._aplicar(cobro);
      if (this._fuente && this._fuente.readyState === EventSource.CLOSED) {
        this._programar_reintento();
      }
      this._consultar_luego(CONSULTA_MS);
      return;
    }
    if (resultado.no_existe) {
      this._al_recibir({ tipo: "no_existe", escucha: this });
      this.terminar();
      return;
    }
    if (resultado.sin_conexion) {
      this._consultar_luego(CONSULTA_MS);
    }
  }

  /**
   * @returns {void}
   */
  _programar_reintento() {
    if (this._reintento !== 0 || this._terminada || this.canal === "abierto") {
      return;
    }
    this._reintento = window.setTimeout(() => {
      this._reintento = 0;
      if (this._terminada || this.canal === "abierto") {
        return;
      }
      this._abrir_canal();
    }, REINTENTO_MS);
  }

  /**
   * @returns {void}
   */
  _parar_consulta() {
    window.clearTimeout(this._consulta);
    this._consulta = 0;
    this.consultando = false;
  }

  /**
   * @returns {void}
   */
  _parar_reintento() {
    window.clearTimeout(this._reintento);
    this._reintento = 0;
  }

  /**
   * Cierra el canal y detiene la consulta (spec 002, RF-040).
   *
   * @returns {void}
   */
  terminar() {
    if (this._terminada) {
      return;
    }
    this._terminada = true;
    this.canal = "cerrado";
    this._parar_consulta();
    this._parar_reintento();
    if (this._fuente) {
      const fuente = this._fuente;
      this._fuente = null;
      fuente.close();
    }
  }
}

/**
 * Las escuchas de esta pantalla. En el corte 1 solo está el cobro en pantalla
 * (spec 002, RF-021, RF-022, RF-023, RF-029, RF-058).
 */
export class Escuchas {
  /**
   * @param {{
   *   pagado: (pago: object, cobro: object) => void,
   *   reconectando: (visible: boolean) => void,
   *   vencido: (cobro: object) => void,
   *   error: () => void,
   *   fin: () => void,
   * }} vistas
   */
  constructor(vistas) {
    this._vistas = vistas;
    this._avisados = new Avisados();
    /** @type {Map<string, Escucha>} */
    this._por_id = new Map();
    /** @type {string | null} */
    this._en_pantalla = null;
    this._pantalla_pedida = false;
  }

  /**
   * @param {{ id: string }} cobro
   * @returns {void}
   */
  poner_en_pantalla(cobro) {
    if (!this._pantalla_pedida) {
      this._pantalla_pedida = true;
      void mantener_encendida(true);
    }
    const escucha = new Escucha(cobro.id, cobro, true, (aviso) => {
      this._recibir(aviso);
    });
    this._por_id.set(cobro.id, escucha);
    this._en_pantalla = cobro.id;
  }

  /**
   * El corte 1 deja de escuchar el cobro en pantalla (spec 002, RF-042).
   *
   * @returns {void}
   */
  terminar_en_pantalla() {
    const id = this._en_pantalla;
    if (!id) {
      return;
    }
    const escucha = this._por_id.get(id);
    this._por_id.delete(id);
    this._en_pantalla = null;
    if (escucha) {
      escucha.terminar();
    }
    this._vistas.reconectando(false);
    this._soltar_si_vacia();
  }

  /**
   * @param {string} id
   * @param {string} tipo
   * @returns {void}
   */
  _cerrar(id, tipo) {
    const era_pantalla = id === this._en_pantalla;
    this._por_id.delete(id);
    if (era_pantalla) {
      this._en_pantalla = null;
      this._vistas.reconectando(false);
      if (tipo === "no_existe") {
        this._vistas.error();
      } else {
        this._vistas.fin();
      }
    }
    this._soltar_si_vacia();
  }

  /**
   * @returns {void}
   */
  _soltar_si_vacia() {
    if (this._por_id.size === 0) {
      this._pantalla_pedida = false;
      void mantener_encendida(false);
    }
  }

  /**
   * @param {{ tipo: string, escucha: Escucha, cobro?: object }} aviso
   * @returns {void}
   */
  _recibir(aviso) {
    const en_pantalla = aviso.escucha.id === this._en_pantalla;
    if (aviso.tipo === "cortado" && en_pantalla) {
      this._vistas.reconectando(true);
      return;
    }
    if (aviso.tipo === "abierto" && en_pantalla) {
      this._vistas.reconectando(false);
      return;
    }
    if (aviso.tipo === "vencido" && en_pantalla) {
      const cobro = aviso.cobro || aviso.escucha.cobro;
      const pagos = cobro && Array.isArray(cobro.pagos) ? cobro.pagos : [];
      if (pagos.length === 0 && cobro) {
        this._vistas.vencido(cobro);
      }
      return;
    }
    if (aviso.tipo === "fin" || aviso.tipo === "no_existe") {
      this._cerrar(aviso.escucha.id, aviso.tipo);
      return;
    }
    if (aviso.tipo !== "cobro" || !aviso.cobro) {
      return;
    }
    const nuevos = this._avisados.nuevos(aviso.cobro);
    if (!en_pantalla) {
      return;
    }
    for (const pago of nuevos) {
      sonar();
      vibrar();
      this._vistas.pagado(pago, aviso.cobro);
    }
  }
}

/**
 * @param {Event} evento
 * @returns {object | null}
 */
function leer_json(evento) {
  if (!("data" in evento) || typeof evento.data !== "string") {
    return null;
  }
  try {
    const datos = JSON.parse(evento.data);
    if (!datos || typeof datos !== "object") {
      return null;
    }
    return datos;
  } catch {
    return null;
  }
}

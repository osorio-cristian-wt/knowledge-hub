# Análisis de requisitos — Knowledge Hub (ecosistema OpenClaw)

> Documento de análisis. No define diseño ni implementación; registra el problema,
> el alcance, los requisitos y las decisiones tomadas en la sesión de relevamiento
> (transcripción `IA Integration.txt`) y en las rondas de preguntas posteriores.
>
> Fecha: 2026-07-09 · Analista: Cristian Osorio · Usuaria final: Daiana

---

## 1. Contexto y problema

Daiana es gerente de **Cleanora** (empresa de limpieza/pintura que opera en EE.UU.),
una unidad de negocio dentro de la estructura mayor **Home Alliance**. La operación
vive repartida en muchos sistemas (BookingKoala, GoHighLevel, OpenPhone, Slack, n8n,
Stripe) pero la **documentación y los datos de gestión viven en Google Drive**
(Google Docs y Sheets trabajados directamente en la nube).

Dolores relevados en la reunión:

- Volumen inmanejable de archivos ("la punta del iceberg"; decenas de miles de
  documentos en el Drive corporativo). Abrir 3 documentos solo para responder una
  pregunta simple es lo normal.
- Información fragmentada entre áreas y entre dos niveles: lo propio de Cleanora y
  lo que impone la estructura de Home Alliance (reportes, jerarquías, accesos).
- Consolidación manual de reportes: otras personas cargan datos (ej. Nick carga
  ventas a diario), ella cruza todo semanalmente a mano, "numerito por numerito".
- ~**65% de la operación está documentada**; los accesos son irregulares (a veces
  hay que pedirlos, pero se otorgan).
- Restricción personal fuerte: **no tiene tiempo ni perfil técnico**. Cualquier
  solución tiene que ser de fricción casi nula, tanto para instalar como para operar.

## 2. Visión

Centralizar el conocimiento de la empresa en un repositorio local de archivos `.md`
y usar **OpenClaw** como consultor de esa información: Daiana le pregunta en lenguaje
natural (por chat) y el agente responde, arma reportes, diagnostica y genera
entregables, buscando de forma dirigida gracias a una estructura e índice de
documentos — sin barrer miles de archivos ni quemar tokens.

La instalación completa del ecosistema en la PC de Daiana la **guía el propio Claw**
(autoinstalación conversacional) a partir de un único script de arranque.

## 3. Actores

| Actor | Rol |
|---|---|
| **Daiana** | Usuaria final única (fase 1). Gerente de Cleanora. No técnica. Opera desde su PC Windows y su celular. |
| **Cristian** | Consultor/mantenedor. Publica el ecosistema en el repo público de GitHub; no opera el sistema en el día a día. |
| **Colaboradores de Cleanora/Home Alliance** | No usan el sistema, pero editan los documentos de origen en Drive (sus cambios deben detectarse y atribuirse). |
| **Equipo de Cleanora (futuro)** | En agosto reciben el documento de políticas final "para usar con una IA". Fuera del alcance de fase 1; se registra como evolución. |

## 4. Arquitectura de repositorios (restricción estructural)

Dos repositorios con roles y políticas de privacidad opuestas:

1. **Repo ecosistema (este repo, público en GitHub)** — scripts de instalación,
   configuración de OpenClaw, skills, pipeline de conversión, documentación.
   **Jamás contiene datos de la empresa.** Es también el canal de actualización:
   queda clonado en la PC de Daiana y Claw lo actualiza vía `git pull` (periódico
   o cuando Cristian avisa).
2. **Repo conocimiento (privado, git local en la PC de Daiana)** — el espejo `.md`
   de la documentación de la empresa más lo que el agente genere. **Sin remoto:
   nunca se sube a GitHub ni a ningún servicio.** Git funciona solo como versionado
   y backup local, invisible para Daiana.

## 5. Alcance

### En alcance (fase 1)

- Autoinstalación guiada por Claw en una (1) PC Windows.
- Fuente de conocimiento única: **Google Drive** (Docs y Sheets nativos), con
  **selección curada** de carpetas/archivos definida con Daiana.
- Pipeline de sincronización unidireccional Drive → export → conversión a `.md`
  (markitdown de Microsoft) → clasificación en la estructura → commit local.
- Consulta conversacional por WhatsApp/Telegram, incluyendo **casos de uso
  numéricos desde el inicio** (P&L, scorecard, reportes de ventas, diagnósticos).
- Versionado local con trazabilidad legible (fecha y autor del cambio).
- Comportamientos proactivos (ver RF-30s) y sistema de skills (ver RF-40s).

### Fuera de alcance (fase 1) — registrado como evolución

- **Escritura de vuelta a Drive** (ej. completar el reporte semanal directamente).
  Fase 2 explícita: en fase 1 el agente genera entregables localmente y Daiana los
  sube a mano si corresponde.
- Otras fuentes de conocimiento (Slack, GoHighLevel, BookingKoala, OpenPhone, n8n).
- Multiusuario / uso por el equipo de Cleanora (hito de agosto: el documento de
  políticas pasa al equipo — posible fase futura).
- Modelos locales / operación sin API cloud.

## 6. Requisitos funcionales

### Instalación y actualización (RF-01…)

- **RF-01** — El arranque en la PC de Daiana es **un único script/instalador** que
  deja OpenClaw corriendo. Todo lo demás (git, Python/markitdown, credenciales de
  Drive, creación del repo de conocimiento, estructura, canal de chat) lo instala y
  configura **el propio Claw conversando con ella**, paso a paso.
- **RF-02** — El instalador no asume entorno de desarrollo previo ni conocimientos
  técnicos: cada paso que requiera acción de Daiana (loguearse a Google, escanear un
  QR, pegar una API key) se le pide en lenguaje simple con instrucciones exactas.
- **RF-03** — El ecosistema es **actualizable desde el repo público de GitHub**:
  Claw hace pull (periódico o a pedido) y aplica mejoras sin reinstalación.
- **RF-04** — OpenClaw corre con **cuenta LLM propia de Daiana** (ella la crea
  guiada por el instalador; costos y límites son suyos).

### Sincronización Drive → espejo local (RF-10…)

- **RF-10** — Acceso a Drive vía **OAuth con la cuenta corporativa de Daiana**
  (supuesto S-01 a validar: el Workspace de Home Alliance permite la autorización).
- **RF-11** — Se sincroniza solo la **selección curada**: carpetas/archivos que
  Daiana marca como relevantes. La selección puede crecer con el tiempo.
- **RF-12** — Los Google Docs/Sheets nativos se **exportan** (docx/xlsx) y se
  convierten a `.md` con markitdown. Formatos adicionales (PDF, slides) no están
  comprometidos en fase 1.
- **RF-13** — Doble disparador: sincronización **programada** (cadencia a definir
  en diseño) y **manual bajo demanda** ("actualizá la documentación") desde el chat.
- **RF-14** — En cada sincronización se detecta **qué cambió** respecto de la
  versión anterior y se registra un commit local por cambio con: **fecha del cambio
  y autor** (quién lo modificó en Drive, si la API lo expone — supuesto S-02) y un
  resumen legible de la modificación.
- **RF-15** — La sincronización es unidireccional (solo lectura sobre Drive). Nada
  del pipeline modifica los archivos de origen.

### Estructura del conocimiento e índice (RF-20…)

- **RF-20** — El repo de conocimiento tiene un **esqueleto predefinido de dos
  contextos**, reflejando cómo Daiana necesita razonar:
  1. **Cleanora como negocio** — dividido por áreas (estrategia, marketing, ventas,
     dispatching/operaciones, RRHH, finanzas).
  2. **Cleanora dentro de Home Alliance** — jerarquía, departamentos, reportes que
     le piden, de dónde sale cada número.
- **RF-21** — Clasificación **híbrida**: el esqueleto viene dado por el ecosistema;
  el agente clasifica cada documento importado dentro de él y **Daiana valida/corrige**.
- **RF-22** — Existe un **índice/catálogo** (mapa de qué hay y dónde) que el agente
  consulta primero para dirigir la búsqueda. Objetivo explícito: responder sin
  escanear el corpus completo (eficiencia de tokens, ver RNF-03).
- **RF-23** — La estructura debe soportar corpus bilingüe (documentos en inglés y
  español mezclados).

### Consulta y casos de uso (RF-25…)

- **RF-25** — Preguntas y respuestas sobre cualquier área del conocimiento
  ("¿cuál es la política de X?", "¿dónde saco el reporte que me pide For A?").
- **RF-26** — **Reportes de planificación integrales** que crucen información de
  múltiples áreas/documentos.
- **RF-27** — **Diagnóstico numérico**: análisis sobre datos de Sheets (P&L,
  scorecard, ventas) del tipo "se cayeron las ventas → es este canal de leads el que
  no está funcionando". En alcance desde fase 1.
- **RF-28** — Generación de **entregables** a partir del conocimiento (ej.
  presentación/curso del manual de políticas). Se generan localmente; idioma
  **según lo pida cada vez** (sin regla fija español/inglés).
- **RF-29** — Historial consultable en lenguaje natural: "¿qué cambió esta semana
  en ventas?" se responde a partir de los commits/diffs, **sin exponer git** a
  Daiana (para ella son "cambios con fecha y autor").

### Proactividad (RF-30…)

- **RF-30** — **Aviso de cambios importantes**: cuando la sincronización detecta un
  cambio relevante (ej. cambio en políticas de la empresa), Claw le avisa a Daiana
  por el canal de chat mostrándole el cambio, con fecha y autor. Cambios de rutina
  (ej. actualización diaria de números de ventas) **no** generan aviso individual.
  El criterio importante/rutinario es un punto abierto de diseño (PA-03).
- **RF-31** — **Resumen periódico** (digest) de todo lo que cambió en la
  documentación, importante o no. Cadencia a definir.
- **RF-32** — **Recordatorios de reportes**: avisos de tareas recurrentes de Daiana
  (ej. consolidar el reporte semanal de ventas para gerencia).
- **RF-33** — **Alertas sobre los datos**: al sincronizar, detección de anomalías en
  los números (caída de ventas, lead source en cero, etc.) con aviso sin que ella
  pregunte.

### Skills y mejora continua (RF-40…)

- **RF-40** — Si Claw detecta que Daiana hace **algo repetitivo** con el sistema,
  debe **guiarla para crear una skill** que lo encapsule para fácil reutilización.
- **RF-41** — Claw debe **recomendar skills existentes** apropiadas para los
  trabajos que ella va a encarar (ej. análisis en profundidad de ventas), tanto del
  catálogo del ecosistema como de las creadas por ella.
- **RF-42** — Las skills genéricas (sin datos de la empresa) pueden vivir en el repo
  público y distribuirse vía actualización (RF-03); las que contengan información de
  la empresa viven en el repo privado.

## 7. Requisitos no funcionales

- **RNF-01 — Privacidad**: los datos de la empresa nunca se persisten fuera de la
  PC de Daiana (ni GitHub ni ningún remoto). Sí está aceptado que el contenido
  viaje a la **API cloud del LLM** durante las consultas. No hay filtrado de datos
  sensibles: todo lo curado se espeja tal cual (decisión registrada, riesgo R-02).
- **RNF-02 — Usabilidad**: usuaria única no técnica. Cero terminal después del
  script inicial; cero conceptos de git/markdown expuestos; toda interacción por
  chat en lenguaje natural (con ella, en español).
- **RNF-03 — Eficiencia de tokens/costo**: la estructura + índice deben permitir
  búsqueda dirigida. El costo corre por cuenta de Daiana (RF-04), así que el
  consumo por consulta importa.
- **RNF-04 — Plataforma**: Windows (PC personal de Daiana). Sin requisito de
  servidor externo.
- **RNF-05 — Recuperabilidad**: ante un error del agente o una conversión mala,
  debe poder volverse a la versión anterior del conocimiento (git local como red de
  seguridad, invisible para ella).
- **RNF-06 — Plazos**: sin fecha dura; se prioriza por valor ("lo antes posible").
  Hito contextual: en agosto 2026 el documento de políticas pasa al equipo.

## 8. Restricciones

- **C-01** — Stack fijado por decisión del proyecto: OpenClaw como agente,
  markitdown (Microsoft, open source) como conversor, git para versionado.
- **C-02** — Dos repos separados con las políticas del §4; prohibido mezclar datos
  de la empresa en el repo público.
- **C-03** — Canal de interacción: WhatsApp o Telegram (elección puntual pendiente,
  PA-04).
- **C-04** — Los documentos de origen se siguen trabajando en Google Drive por el
  resto de la empresa; el sistema no cambia el flujo de trabajo de nadie más que
  Daiana.

## 9. Supuestos y riesgos

| ID | Tipo | Descripción | Impacto si falla |
|---|---|---|---|
| S-01 | Supuesto | El Workspace de Home Alliance permite autorizar OAuth de la cuenta de Daiana para Drive API. | **Bloqueante** para el sync; habría que rediseñar el acceso (validar antes que nada). |
| S-02 | Supuesto | La API de Drive expone el autor de la última modificación de los archivos curados. | RF-14/RF-30 pierden el "quién"; quedaría solo fecha y diff. |
| S-03 | Supuesto | Daiana consigue u obtiene los accesos a los documentos de otras áreas cuando los necesita (en la reunión: "me los dan"). | Huecos en el conocimiento; el índice debe marcar lo inaccesible. |
| R-01 | Riesgo | Política corporativa de Home Alliance sobre sacar datos de la empresa a una PC personal y a una API externa (en la reunión se optó por "pedir perdón"). | Posible orden de apagado del sistema; decisión y responsabilidad quedan del lado de Daiana. |
| R-02 | Riesgo | El espejo incluye datos sensibles (PII de clientes, sueldos, pagos) sin filtrar, y viajan a la API en consultas. | Exposición ante incidente en la PC o en el proveedor LLM. Mitigación futura: lista de exclusión. |
| R-03 | Riesgo | Conversión Sheets → md: se pierden fórmulas (quedan valores) y hojas grandes pueden volverse tablas enormes. | Diagnósticos numéricos (RF-27) menos confiables o caros; tratar en diseño del pipeline. |
| R-04 | Riesgo | ~35% de la operación no está documentada. | El agente no puede responder lo que no existe; oportunidad: que Claw señale huecos de documentación. |
| R-05 | Riesgo | Costos LLM a cargo de Daiana con casos de uso numéricos intensivos. | Sorpresa de facturación; mitigación: RNF-03 + visibilidad de consumo. |

## 10. Preguntas abiertas (para la fase de diseño)

- **PA-01** — Relevamiento de la selección curada inicial: qué carpetas/archivos
  concretos entran (sesión con Daiana). *(El mecanismo de alta ya está diseñado —
  DD-17/DD-18; falta solo el contenido inicial.)*
- ~~**PA-02** — Cadencias~~ → resuelto en diseño (DD-13): sync diario 07:00 +
  manual; digest lunes 08:00; configurables.
- ~~**PA-03** — Criterio de "cambio importante"~~ → resuelto en diseño (DD-09):
  metadata de importancia primero, juicio del agente para lo no obvio.
- ~~**PA-04** — WhatsApp vs Telegram~~ → resuelto en diseño (DD-10): Telegram;
  WhatsApp posible segundo canal futuro.
- **PA-05** — Qué cuenta LLM conviene a Daiana (API key vs suscripción) y costo
  mensual estimado según los casos de uso.
- ~~**PA-06** — Representación de Sheets numéricos~~ → resuelto en diseño
  (DD-02/DD-14): CSV por hoja + ficha md; el agente calcula con código.
- **PA-07** — Qué hace el sistema con documentos a los que Daiana pierde o no tiene
  acceso (marcado en el índice, re-intento, aviso).
- **PA-08** — Evolución a fase 2: escritura a Drive y uso por el equipo (agosto).

## 11. Registro de decisiones del relevamiento

| # | Decisión | Elección |
|---|---|---|
| D-01 | Frontera de privacidad | API cloud OK; prohibido todo remoto persistente |
| D-02 | Usuario/máquina | Solo Daiana, su PC Windows |
| D-03 | Disparo del sync | Programado + manual bajo demanda |
| D-04 | Formatos de origen | Google Docs/Sheets nativos (export vía Drive API) |
| D-05 | Dirección del flujo | Solo lectura; escritura a Drive = fase 2 |
| D-06 | Taxonomía | Híbrida: esqueleto fijo de dos contextos, el agente clasifica, Daiana valida |
| D-07 | Canal | WhatsApp/Telegram (elección final pendiente, PA-04) |
| D-08 | Cuenta LLM | Propia de Daiana |
| D-09 | Datos numéricos | En alcance desde fase 1 |
| D-10 | Alcance Drive | Selección curada |
| D-11 | Versionado | Backup invisible + fecha/autor legibles + avisos de cambios importantes |
| D-12 | Bootstrap | Script único; Claw guía todo lo demás |
| D-13 | Acceso Drive | OAuth cuenta corporativa (validar S-01) |
| D-14 | Proactividad | Avisos importantes + digest + recordatorios + alertas de datos + skills (RF-40/41) |
| D-15 | Datos sensibles | Sin filtrado; se espeja todo lo curado |
| D-16 | Fuentes fase 1 | Solo Drive |
| D-17 | Actualización | Vía repo público de GitHub |
| D-18 | Plazos | Sin fecha dura; hito contextual agosto 2026 |
| D-19 | Idioma de entregables | Según lo pida cada vez |

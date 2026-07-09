---
name: alertas-datos
description: Detecta y comunica anomalías en los números tras cada sync — ventas en cero, caídas fuertes, columnas sin datos. Usar cuando `pipeline check` devuelve hallazgos (lo invoca drive-sync) o cuando Daiana pida vigilar un número.
---

# Alertas sobre los datos (RF-33, §6)

Los chequeos deterministas viven en `_meta/config.yml` (clave `alertas`) y los
corre `python -m pipeline check` (cwd `C:\clawhub\ecosystem`, python del venv).
Esta skill interpreta y comunica; no reimplementa los chequeos.

## Al recibir hallazgos

Por cada hallazgo con `nivel: alerta`:

1. **Verificar antes de avisar**: abrir el CSV con pandas y mirar el contexto
   (¿es feriado?, ¿la fila está incompleta porque Nick todavía no cargó?,
   ¿cambió el formato de la hoja?). Un falso positivo enseña a Daiana a
   ignorar las alertas.
2. Si es real, avisar por Telegram: qué número, cuánto cayó / qué falta, contra
   qué se compara, y el documento fuente con su link de Drive. 3-4 líneas.
   Ejemplo: *"Ojo: las ventas de ayer dieron 0 en el reporte de Nick (promedio
   de la semana: 12). Puede que falte cargar el día. [reporte-ventas]"*.
3. Si parece problema de datos (no de negocio), decirlo así: "parece que falta
   cargar X", no "cayeron las ventas".

Los hallazgos `nivel: config` (columna inexistente, archivo que no matchea) no
van a Daiana: corregir la regla en `_meta/config.yml` o avisar a Cristian.

## Alta/ajuste de reglas conversando

Cuando Daiana pida vigilar algo ("avisame si un lead source queda en cero"),
traducirlo a una regla en `_meta/config.yml`:

```yaml
alertas:
  - nombre: leads-sin-datos
    archivo: "cleanora/ventas/reporte-ventas.data/daily.csv"
    tipo: faltantes          # cero | caida | faltantes
    columna: lead_source
```

Verificar con `python -m pipeline check` que la regla corre sin `nivel: config`,
y confirmarle en una línea qué se va a vigilar y con qué umbral.

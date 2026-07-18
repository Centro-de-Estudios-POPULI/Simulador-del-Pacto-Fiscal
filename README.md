# Simulador del Pacto Fiscal

Plataforma interactiva del **Observatorio de Finanzas Públicas y Desarrollo Territorial**
(Centro de Estudios POPULI) para simular la **coparticipación tributaria** en Bolivia.

Permite elegir qué impuestos nacionales de renta interna forman la masa coparticipable
(IVA, IT, IUE, ICE, RC-IVA, ISAE, Gravamen Arancelario) y cómo se reparten entre el TGN,
las gobernaciones, los municipios y las universidades, y recalcula el efecto en cada
departamento y municipio del país.

**En vivo:** https://centro-de-estudios-populi.github.io/Simulador-del-Pacto-Fiscal/

## Características

- **Base coparticipable seleccionable** (checkboxes + presets IT / IT+IVA / IT+IUE / renta interna completa).
- **Reparto TGN / gobernaciones / municipios / universidades** con modo Automático (rebalancea el resto) o Manual (cifras exactas con validación).
- **Modo Adicional (vs. régimen vigente) o Total** (bajo la propuesta).
- **Fondo de equidad** ajustable (población, territorio, NBI, fragilidad fiscal) sobre los puntos municipales adicionales.
- **Dos mapas** georreferenciados (departamental y municipal) con drill-down.
- **Comparador de escenarios** (hasta 4 configuraciones lado a lado).

## Base legal

Ley 1551 (Participación Popular), Ley 031 (LMAD) D.T. 3ª y 4ª, Ley 195/2011 (UPEA),
Ley 843, Ley 2042 (base neta del Gravamen Arancelario). Ver el bloque de metodología del tablero.

## Datos

Recaudación 2025 (percibido) del **Presupuesto Abierto del MEFP**; población y NBI del
Censo INE 2024; fragilidad fiscal e ingresos corrientes municipales del SIGEP / Atlas Fiscal
Municipal; ingresos de gobernaciones del portal de Finanzas Públicas Departamentales (CAIF).

## Reproducir

La página (`index.html`) es autónoma: se arma inyectando los datos en el template.

```bash
python scripts/build_simulador_fiscal.py     # template + data/*.json  -> index.html
```

Para regenerar los datos desde las fuentes (requiere descargar los insumos, ver notas en
cada script):

```bash
python scripts/extraer_impuestos.py     # CSV de ingreso MEFP        -> data/impuestos_2025.json
python scripts/generar_mapas_svg.py     # GeoJSON OEP 2025            -> data/mapa_{muni,dep}.json
```

## Ecosistema

- [Observatorio de Finanzas Públicas y Desarrollo Territorial](https://centro-de-estudios-populi.github.io/observatorio-ofpdt/)
- [Atlas Fiscal Municipal](https://centro-de-estudios-populi.github.io/Atlas-Fiscal-Municipal/)
- [Finanzas Públicas Departamentales](https://centro-de-estudios-populi.github.io/Finanzas-P-blicas-Departamentales/)

---

Ejercicio ilustrativo, no una asignación oficial. Centro de Estudios POPULI.

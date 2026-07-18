# -*- coding: utf-8 -*-
"""
Ensambla simulador_fiscal.html inyectando los datasets en simulador_fiscal.template.html.
EDITAR SIEMPRE EL TEMPLATE, nunca el HTML generado.

Placeholders en el template (comentarios JS):
  /*__IMP__*/    -> data/impuestos_2025.json (lista de impuestos + otros_impuestos)
  /*__ENT__*/    -> data/_scenario_ent_slim.json (343 entidades: s,n,d,t,p,a,nb,fr,ic)
  /*__GOB__*/    -> data/_scenario_gob.json (base de gobernaciones por depto)
  /*__MMUNI__*/  -> data/mapa_muni.json (337 paths municipales)
  /*__MDEP__*/   -> data/mapa_dep.json (9 paths departamentales)
"""
import json, os

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
D = os.path.join(ROOT, 'data')
TPL = os.path.join(ROOT, 'simulador_fiscal.template.html')
OUT = os.path.join(ROOT, 'index.html')   # en este repo la salida es la página raíz servida por Pages


def load(name):
    with open(os.path.join(D, name), encoding='utf-8') as f:
        return f.read()


def main():
    with open(TPL, encoding='utf-8') as f:
        html = f.read()
    subs = {
        '/*__IMP__*/': load('impuestos_2025.json'),
        '/*__ENT__*/': load('_scenario_ent_slim.json'),
        '/*__GOB__*/': load('_scenario_gob.json'),
        '/*__MMUNI__*/': load('mapa_muni.json'),
        '/*__MDEP__*/': load('mapa_dep.json'),
    }
    # Se inyecta el dato seguido de '||' para que quede "DATO || {fallback}":
    # así el template SIN construir sigue siendo JS válido (usa el fallback) y el
    # archivo construido usa el dato inyectado (siempre truthy).
    for ph, data in subs.items():
        if ph not in html:
            raise SystemExit(f'Placeholder ausente en el template: {ph}')
        html = html.replace(ph, data.strip() + ' ||', 1)
    with open(OUT, 'w', encoding='utf-8') as f:
        f.write(html)
    print(f'Generado {OUT} ({os.path.getsize(OUT)//1024} KB)')


if __name__ == '__main__':
    main()

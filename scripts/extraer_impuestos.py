# -*- coding: utf-8 -*-
"""
Extrae los ingresos por impuesto (gestión 2025) desde el CSV de Presupuesto
Abierto del MEFP y genera data/impuestos_2025.json, insumo del simulador fiscal.

Fuente: data/_raw_mefp/presupuesto_ingreso_gestion_2025.csv
  (portal abierto.economiayfinanzas.gob.bo, ingreso/gestiones/gestion_2025.zip)

Clasificador de rubros (renta nacional + subnacional de dominio propio):
  13100 Renta Interna | 13200 Renta Aduanera | 13300 Municipales | 13400 Departamentales
El desglose efectivo vs certificados de crédito fiscal se lee del último dígito
del rubro_sub_cuenta (2/7 = certificados; resto = efectivo). Validado contra el
IT conocido (efectivo 6.047,7 MM / certificados 1.275,4 MM).

La bandera `coparticipable` sale de la investigación normativa (Ley 1551 art. 20,
Ley 031 D.T. 3ª/4ª): la masa coparticipable es la RENTA INTERNA nacional en efectivo,
EXCLUYENDO impuestos con régimen propio (IDH, IEHD, IPJ) y los de dominio subnacional.
"""
import csv, json, os

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
CSV_IN = os.path.join(ROOT, 'data', '_raw_mefp', 'presupuesto_ingreso_gestion_2025.csv')
JSON_OUT = os.path.join(ROOT, 'data', 'impuestos_2025.json')

CERT_SUF = {'2', '7'}  # sub_cuenta que termina en 2 o 7 = certificados de crédito fiscal

# Nivel de recaudación por clase de rubro
NIVEL = {'13100': 'nacional', '13200': 'nacional', '13300': 'municipal', '13400': 'departamental'}

# Metadatos por rubro_cuenta: sigla corta, ¿coparticipable?, nota normativa.
# (coparticipable se finaliza con la investigación normativa; ver informe adjunto)
META = {
    '13110': dict(sigla='IUE',   grupo='Renta Interna',  coparticipable=True),
    '13120': dict(sigla='IT',    grupo='Renta Interna',  coparticipable=True),
    '13130': dict(sigla='IVA-MI',grupo='Renta Interna',  coparticipable=True),
    '13140': dict(sigla='IVA-M', grupo='Renta Interna',  coparticipable=True),
    '13150': dict(sigla='ICE-MI',grupo='Renta Interna',  coparticipable=True),
    '13160': dict(sigla='ICE-M', grupo='Renta Interna',  coparticipable=True),
    '13170': dict(sigla='IEHD/IDH', grupo='Hidrocarburos', coparticipable=False,
                  nota='Régimen propio: IEHD 25% deptos (Ley 1654), IDH Ley 3058. No entra a la masa.'),
    '13190': dict(sigla='Otros', grupo='Renta Interna',  coparticipable=None),  # se desglosa
    '13210': dict(sigla='GA',    grupo='Renta Aduanera', coparticipable=True,
                  nota='Coparticipable sobre base NETA: menos certificados y presupuesto Aduana (<=10%, Ley 2042 art.25).'),
    # Subnacionales de dominio propio (nunca a masa coparticipable nacional)
    '13310': dict(sigla='IPBI',  grupo='Municipal',      coparticipable=False),
    '13330': dict(sigla='IPVA',  grupo='Municipal',      coparticipable=False),
    '13360': dict(sigla='ITMI',  grupo='Municipal',      coparticipable=False),
    '13370': dict(sigla='IMT',   grupo='Municipal',      coparticipable=False),
    '13390': dict(sigla='Otros-M', grupo='Municipal',    coparticipable=False),
    '13410': dict(sigla='ITGB',  grupo='Departamental',  coparticipable=False),
    '13490': dict(sigla='Otros-D', grupo='Departamental',coparticipable=False),
}

# Desglose de "Otros Impuestos" (13190) por sub_cuenta, con su tratamiento.
META_SUB = {
    # Coparticipables (Ley 1551 art.19: RC-IVA e ISAE están en la lista de renta interna)
    '13191': dict(sigla='RC-IVA', desc='Régimen Complementario al IVA', coparticipable=True),
    '13192': dict(sigla='ISAE',   desc='Impuesto a las Salidas Aéreas al Exterior', coparticipable=True),
    '13197': dict(sigla='Otros-cert', desc='Otros en certificados', coparticipable=False),
    # NO coparticipables — regímenes especiales (no figuran en art.19 Ley 1551) y régimen propio
    '13194': dict(sigla='RAU',    desc='Régimen Agropecuario Unificado', coparticipable=False),
    '13195': dict(sigla='RTS',    desc='Régimen Tributario Simplificado', coparticipable=False),
    '13196': dict(sigla='STI',    desc='Régimen Tributario Integrado', coparticipable=False),
    '13198': dict(sigla='ITF',    desc='Impuesto a las Transacciones Financieras (Ley 3446: 100% TGN)', coparticipable=False),
    '13199': dict(sigla='IPJ/Otros', desc='Impuesto a la Participación en Juegos y otros (Ley 060: régimen propio)', coparticipable=False),
}


def num(x):
    try:
        return float(x or 0)
    except ValueError:
        return 0.0


def main():
    cuentas = {}   # cuenta -> acumulador
    subs = {}      # (13190) sub_cuenta -> acumulador
    with open(CSV_IN, encoding='utf-8', errors='replace') as f:
        r = csv.DictReader(f)
        for row in r:
            clase = row.get('rubro_clase', '')
            if clase not in NIVEL:
                continue
            p = num(row.get('percibido'))
            if p == 0:
                continue
            cuenta = row.get('rubro_cuenta', '')
            sc = row.get('rubro_sub_cuenta', '')
            # En los impuestos principales el par …1/…2 marca efectivo/certificado.
            # En "Otros Impuestos" (13190) el último dígito identifica el impuesto
            # (13192=ISAE, etc.); solo 13197 es "En Certificados de Crédito Fiscal".
            if cuenta == '13190':
                is_cert = (sc == '13197')
            else:
                is_cert = bool(sc) and sc[-1] in CERT_SUF
            c = cuentas.setdefault(cuenta, dict(cuenta=cuenta, clase=clase, nivel=NIVEL[clase],
                                                desc=row.get('rubro_desc_cuenta', ''),
                                                ef=0.0, cert=0.0, total=0.0))
            (c.__setitem__('cert', c['cert'] + p) if is_cert else c.__setitem__('ef', c['ef'] + p))
            c['total'] += p
            if cuenta == '13190':
                s = subs.setdefault(sc, dict(sub=sc, desc=row.get('rubro_desc_sub_cuenta', ''),
                                             ef=0.0, cert=0.0, total=0.0))
                (s.__setitem__('cert', s['cert'] + p) if is_cert else s.__setitem__('ef', s['ef'] + p))
                s['total'] += p

    impuestos = []
    for cuenta, c in cuentas.items():
        m = META.get(cuenta, dict(sigla=cuenta, grupo='?', coparticipable=False))
        imp = dict(cuenta=cuenta, sigla=m['sigla'], desc=c['desc'].strip(),
                   grupo=m['grupo'], nivel=c['nivel'],
                   coparticipable=m['coparticipable'], nota=m.get('nota', ''),
                   ef=round(c['ef']), cert=round(c['cert']), total=round(c['total']))
        # Gravamen Arancelario: coparticipable sobre base NETA (Ley 2042 art. 25) =
        # efectivo menos el presupuesto de la Aduana, con tope del 10% de la recaudación total.
        # Se aproxima con el tope legal (10% del total) como deducción conservadora.
        if cuenta == '13210':
            aduana = round(0.10 * c['total'])
            imp['ef_bruto'] = round(c['ef'])
            imp['ef'] = round(c['ef']) - aduana        # ef que entra a la masa (neto de Aduana)
            imp['deduccion_aduana'] = aduana
        impuestos.append(imp)
    impuestos.sort(key=lambda x: -x['total'])

    otros = []
    for sc, s in subs.items():
        m = META_SUB.get(sc, dict(sigla=sc, desc=s['desc'], coparticipable=False))
        otros.append(dict(sub=sc, sigla=m['sigla'], desc=(s['desc'] or m['desc']).strip(),
                          coparticipable=m['coparticipable'],
                          ef=round(s['ef']), cert=round(s['cert']), total=round(s['total'])))
    otros.sort(key=lambda x: -x['total'])

    out = dict(
        meta=dict(fuente='MEFP Presupuesto Abierto - ingreso gestión 2025 (percibido)',
                  clasificador='rubro 13000 Ingresos por Impuestos',
                  nota_efectivo='ef/cert por último dígito de rubro_sub_cuenta (2,7=certificados)',
                  unidad='Bs'),
        impuestos=impuestos,
        otros_impuestos=otros,
    )
    with open(JSON_OUT, 'w', encoding='utf-8') as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print('Escrito', JSON_OUT)
    for i in impuestos:
        cp = {True: 'SÍ', False: 'no', None: '~'}[i['coparticipable']]
        print(f"  {i['sigla']:9} cop={cp:3} ef {i['ef']/1e6:8.1f}  cert {i['cert']/1e6:7.1f}  tot {i['total']/1e6:8.1f}  {i['desc']}")


if __name__ == '__main__':
    main()

import json, datetime, urllib.request, sys

UA = {'User-Agent': 'Mozilla/5.0 (piso-bitcoin-bot)'}

def get(url):
    req = urllib.request.Request(url, headers=UA)
    return json.load(urllib.request.urlopen(req, timeout=30))

def estado(valor, objetivo, mayor_es_mejor, margen=0.06):
    if mayor_es_mejor:
        if valor >= objetivo:
            return 'ALCANZADO'
        if valor >= objetivo * (1 - margen):
            return 'ACERCÁNDOSE'
        return 'LEJOS'
    if valor <= objetivo:
        return 'ALCANZADO'
    if valor <= objetivo * (1 + margen):
        return 'ACERCÁNDOSE'
    return 'LEJOS'

def main():
    rows = []
    hoy = datetime.date.today().isoformat()

    # --- Bitstamp: OHLC diario (precio actual + serie para MA y ATH) ---
    bs = get('https://www.bitstamp.net/api/v2/ohlc/btcusd/?step=86400&limit=1000')
    ohlc = bs['data']['ohlc']
    cierres = [float(o['close']) for o in ohlc]
    altos = [float(o['high']) for o in ohlc]
    price = cierres[-1]

    # ATH aproximado desde la serie disponible
    ath = max(altos)
    idx_ath = altos.index(ath)
    ts_ath = int(ohlc[idx_ath]['timestamp'])
    d_ath = datetime.datetime.utcfromtimestamp(ts_ath).date()
    dias = (datetime.date.today() - d_ath).days
    chg = (price - ath) / ath * 100

    # MA de las ultimas muestras disponibles (aprox 200 semanas)
    ventana = cierres[-1400:]
    ma200w = sum(ventana) / len(ventana) if ventana else price
    ratio_ma = price / ma200w if ma200w else 0

    # --- Alternative.me: Miedo y Codicia ---
    fg = get('https://api.alternative.me/fng/?limit=1')
    fng = int(fg['data'][0]['value'])

    rows.append({'key': 'precio_btc', 'valor': '$' + format(round(price), ','), 'objetivo': 'referencia', 'estado': 'INFO'})
    rows.append({'key': 'dias_ath', 'valor': str(dias) + ' días', 'objetivo': '≥ 380 días', 'estado': estado(dias, 380, True)})
    rows.append({'key': 'caida_ath', 'valor': str(round(chg, 1)) + '%', 'objetivo': '≤ -55%', 'estado': ('ALCANZADO' if chg <= -55 else ('ACERCÁNDOSE' if chg <= -52 else 'LEJOS'))})
    rows.append({'key': 'ma200w', 'valor': round(ratio_ma, 2), 'objetivo': '≤ 1.00', 'estado': estado(ratio_ma, 1.0, False)})
    rows.append({'key': 'fng', 'valor': fng, 'objetivo': '≤ 25', 'estado': estado(fng, 25, False)})

    # --- On-chain BGeometrics (best effort; si falla, se marca sin dato) ---
    onchain = [
        ('mvrv', 'https://bitcoin-data.com/v1/mvrv/last', '≤ 1.00', 1.0),
        ('sopr365', 'https://bitcoin-data.com/v1/sopr/last', '≤ 1.00', 1.0),
        ('realizado', 'https://bitcoin-data.com/v1/realized-price/last', '≤ 53000', 53000),
        ('supply_profit', 'https://bitcoin-data.com/v1/supply-in-profit/last', '≤ 50%', 50),
    ]

    for key, url, obj_txt, obj in onchain:
        try:
            data = get(url)
            v = None
            for campo in ('mvrv', 'sopr', 'realizedPrice', 'realized_price', 'supplyInProfit', 'value', 'd'):
                if isinstance(data, dict) and campo in data:
                    v = float(data[campo]); break
            if v is None:
                raise ValueError('campo no encontrado')
            rows.append({'key': key, 'valor': round(v, 2), 'objetivo': obj_txt, 'estado': estado(v, obj, False)})
        except Exception:
            rows.append({'key': key, 'valor': 'sin dato', 'objetivo': obj_txt, 'estado': 'LEJOS'})

    out = {'actualizado': hoy, 'precio_usd': round(price, 2), 'rows': rows}

    with open('data/data.json', 'w', encoding='utf-8') as f:
        json.dump(out, f, ensure_ascii=False, indent=2)

main()

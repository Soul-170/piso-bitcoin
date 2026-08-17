import json, datetime, urllib.request, sys

UA = {'User-Agent': 'piso-bitcoin-bot'}

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

    # --- CoinGecko: precio, ATH y serie para MA 200 semanas ---
    mk = get('https://api.coingecko.com/api/v3/coins/bitcoin?localization=false&tickers=false&market_data=true&community_data=false&developer_data=false')
    md = mk['market_data']
    price = md['current_price']['usd']
    ath = md['ath']['usd']
    chg = md['ath_change_percentage']['usd']
    ath_date = md['ath_date']['usd'][:10]
    d_ath = datetime.date.fromisoformat(ath_date)
    dias = (datetime.date.today() - d_ath).days

    chart = get('https://api.coingecko.com/api/v3/coins/bitcoin/market_chart?vs_currency=usd&days=1400&interval=daily')
    precios = [p[1] for p in chart['prices']]
    ma200w = sum(precios) / len(precios) if precios else price
    ratio_ma = price / ma200w if ma200w else 0

    # --- Alternative.me: Miedo y Codicia ---
    fg = get('https://api.alternative.me/fng/?limit=1')
    fng = int(fg['data'][0]['value'])

    rows.append({'key': 'dias_ath', 'valor': str(dias) + ' días', 'objetivo': '≥ 380 días', 'estado': estado(dias, 380, True)})
    rows.append({'key': 'caida_ath', 'valor': round(chg, 1), 'objetivo': '≤ -55%', 'estado': ('ALCANZADO' if chg <= -55 else ('ACERCÁNDOSE' if chg <= -52 else 'LEJOS'))})
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

    linea = hoy + ',' + str(round(price, 2)) + ',' + str(dias) + ',' + str(round(chg, 1)) + ',' + str(round(ratio_ma, 2)) + ',' + str(fng)
    try:
        with open('data/historico.csv', 'a', encoding='utf-8') as h:
            h.write(linea + '\n')
    except Exception:
        pass
    print('OK', out['actualizado'])

if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        print('ERROR:', e, file=sys.stderr)
        sys.exit(1)

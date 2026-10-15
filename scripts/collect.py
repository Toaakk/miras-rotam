#!/usr/bin/env python3
"""OSM Overpass -> 39 İstanbul ilçesi JSON; Python 3 stdlib.
Çalıştırma: python scripts/collect.py --district Eyüpsultan
Tam tarama: python scripts/collect.py --all (sunucuya saygılı bekleme uygular)
Her başarılı ilçe için veri dosyasını atomik yazar. Hatalı istekte eski dosyayı korur.
"""
import argparse,json,urllib.request,urllib.parse,time,random,sys
from pathlib import Path
DISTRICTS="Adalar,Arnavutköy,Ataşehir,Avcılar,Bağcılar,Bahçelievler,Bakırköy,Başakşehir,Bayrampaşa,Beşiktaş,Beykoz,Beylikdüzü,Beyoğlu,Büyükçekmece,Çatalca,Çekmeköy,Esenler,Esenyurt,Eyüpsultan,Fatih,Gaziosmanpaşa,Güngören,Kadıköy,Kağıthane,Kartal,Küçükçekmece,Maltepe,Pendik,Sancaktepe,Sarıyer,Silivri,Sultanbeyli,Sultangazi,Şile,Şişli,Tuzla,Ümraniye,Üsküdar,Zeytinburnu".split(',')
ROOT=Path(__file__).resolve().parents[1]/'data'; ROOT.mkdir(exist_ok=True)
SERVERS=['https://overpass.kumi.systems/api/interpreter','https://overpass-api.de/api/interpreter']
def category(t):
    historic=str(t.get('historic','')).lower();religion=str(t.get('religion','')).lower();building=str(t.get('building','')).lower();amenity=t.get('amenity','')
    if amenity=='place_of_worship' or religion or building in ('mosque','church','synagogue'):
        if religion=='muslim' or building=='mosque' or t.get('name','').lower().endswith('camii'):return 'cami'
        if religion=='christian' or building in ('church','cathedral','chapel'):return 'kilise'
        if religion=='jewish' or building=='synagogue':return 'sinagog'
    if historic in ('tomb','mausoleum','grave'):return 'turbe'
    if historic in ('castle','fort','tower','city_gate'):return 'kule'
    if historic in ('palace','manor') or building in ('palace','manor'):return 'saray'
    if t.get('tourism')=='museum' or historic in ('archaeological_site','ruins'):return 'muze'
    if historic and historic not in ('no','memorial','wayside_cross','boundary_stone'):return 'eser'
    return None
def query(d):
    # İlçe ilişkisi İstanbul il alanıyla sınırlandırılır; eş adlı başka iller dışlanır.
    safe=d.replace('\\','').replace('"','')
    return f"""[out:json][timeout:100];area["name"="İstanbul"]["admin_level"="4"]["boundary"="administrative"]->.city;rel(area.city)["name"="{safe}"]["admin_level"="6"]["boundary"="administrative"]->.district;.district map_to_area ->.a;(nwr(area.a)["amenity"="place_of_worship"];nwr(area.a)["building"="mosque"];nwr(area.a)["building"="church"];nwr(area.a)["building"="synagogue"];nwr(area.a)["historic"];nwr(area.a)["tourism"="museum"];);out center;"""
def collect(d):
    data=urllib.parse.urlencode({'data':query(d)}).encode()
    error=None
    for url in SERVERS:
        try:
            req=urllib.request.Request(url,data=data,headers={'User-Agent':'MirasRotamDatasetBuilder/0.3 (educational prototype)','Content-Type':'application/x-www-form-urlencoded'})
            with urllib.request.urlopen(req,timeout=135) as resp: result=json.load(resp)
            if not isinstance(result.get('elements'),list):raise ValueError('elements yok')
            break
        except Exception as e:error=e;print(f'{d}: {url}: {e}',file=sys.stderr);time.sleep(3)
    else:raise RuntimeError(f'Kaynak erişilemiyor: {error}')
    places={}
    for el in result['elements']:
        t=el.get('tags') or {};cat=category(t);name=(t.get('name:tr') or t.get('name') or '').strip()
        coords=el if 'lat' in el else el.get('center') or {};lat=coords.get('lat');lng=coords.get('lon')
        if not cat or not name or not isinstance(lat,(int,float)) or not isinstance(lng,(int,float)):continue
        if not (40.7<=lat<=41.7 and 27.9<=lng<=30):continue
        id=1_000_000_000_000+{'node':0,'way':100_000_000_000,'relation':200_000_000_000}[el['type']]+int(el['id'])
        historical=cat=='cami' and bool(t.get('heritage') or t.get('start_date') or t.get('historic') in ('yes','mosque'))
        places[id]={'id':id,'name':name,'cat':cat,'city':'İstanbul','district':d,'hood':t.get('addr:neighbourhood') or t.get('addr:suburb') or t.get('addr:quarter') or 'Mahalle bilgisi teyit edilmeli','lat':lat,'lng':lng,'desc':'OpenStreetMap kaydından alınmıştır. Tarihçe ve ziyaret koşulları doğrulanmadı.','source':f'https://www.openstreetmap.org/{el["type"]}/{el["id"]}','historicCandidate':historical}
    # Başarılı fakat boş sonuç eski veri dosyasını silmesin.
    if not places:raise RuntimeError('0 sonuç: sorgu/bölge kontrol edilmeli, dosya değiştirilmedi')
    output={'district':d,'source':'OpenStreetMap / Overpass API','license':'ODbL 1.0 — https://www.openstreetmap.org/copyright','updated':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),'places':list(places.values())}
    tmp=ROOT/(d+'.json.tmp');tmp.write_text(json.dumps(output,ensure_ascii=False,separators=(',',':')),encoding='utf8');tmp.replace(ROOT/(d+'.json'))
    print(d,len(places),flush=True)
if __name__=='__main__':
    ap=argparse.ArgumentParser();g=ap.add_mutually_exclusive_group(required=True);g.add_argument('--district',choices=DISTRICTS);g.add_argument('--all',action='store_true');args=ap.parse_args()
    failures=[]
    for d in DISTRICTS if args.all else [args.district]:
        try:collect(d)
        except Exception as e:failures.append(d);print(f'HATA {d}: {e}',file=sys.stderr)
        if args.all:time.sleep(12+random.uniform(0,5))
    if failures:print('Eksik ilçeler:',', '.join(failures),file=sys.stderr);sys.exit(1)

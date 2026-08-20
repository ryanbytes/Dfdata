#!/usr/bin/env python3
from __future__ import annotations
import csv, gzip, io, json, re, urllib.parse, urllib.request, zipfile
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
FEED=ROOT/'feed'/'v1'; STATE=ROOT/'state'; SOURCES=ROOT/'pipeline'/'ats_sources.json'
NOTICES='https://raw.githubusercontent.com/kadoa-org/layoffs-tracker/main/public/data/notices.json'
STATES='https://raw.githubusercontent.com/kadoa-org/layoffs-tracker/main/public/data/states.json'
GAZ='https://www2.census.gov/geo/docs/maps-data/data/gazetteer/2025_Gazetteer/2025_Gaz_place_national.zip'
ALL='AL AK AZ AR CA CO CT DE FL GA HI ID IL IN IA KS KY LA ME MD MA MI MN MS MO MT NE NV NH NJ NM NY NC ND OH OK OR PA RI SC SD TN TX UT VT VA WA WV WI WY DC'.split()
SUP={
'HI':('Hawaii DLIR','https://labor.hawaii.gov/wdc/real-time-warn-updates/','official_page'),
'MS':('Mississippi Department of Employment Security','https://mdes.ms.gov/information-center/warn-information/','official_reports'),
'WY':('Wyoming Department of Workforce Services','https://dws.wyo.gov/dws-division/workforce-standards-and-compliance/labor-standards/warn-act/','official_document'),
'AR':('Arkansas Division of Workforce Services','https://dws.arkansas.gov/employers/','no_public_registry_found'),
'NH':('New Hampshire Employment Security','https://www.nhes.nh.gov/','no_public_registry_found')}
COUNTRIES=[
(r'Belgium|Ghent|Zwijnaarde','Belgium'),(r'India|Bengaluru|Bangalore|Hyderabad|Pune|Chennai|Mumbai|Gurugram|Gurgaon|Noida','India'),
(r'Philippines|Manila','Philippines'),(r'Mexico','Mexico'),(r'Canada','Canada'),(r'United Kingdom|London,? England','United Kingdom'),
(r'Ireland','Ireland'),(r'Germany','Germany'),(r'France','France'),(r'Netherlands','Netherlands'),(r'Poland','Poland'),(r'Romania','Romania'),
(r'Portugal','Portugal'),(r'Spain','Spain'),(r'Italy','Italy'),(r'Sweden','Sweden'),(r'Switzerland','Switzerland'),(r'Czech Republic|Czechia','Czechia'),
(r'Hungary','Hungary'),(r'Brazil','Brazil'),(r'Argentina','Argentina'),(r'Colombia','Colombia'),(r'Costa Rica','Costa Rica'),(r'Australia','Australia'),
(r'New Zealand','New Zealand'),(r'Singapore','Singapore'),(r'Japan','Japan'),(r'South Korea|Korea, Republic of','South Korea'),(r'Taiwan','Taiwan'),
(r'Malaysia','Malaysia'),(r'Vietnam','Vietnam'),(r'Thailand','Thailand'),(r'Indonesia','Indonesia'),(r'China','China'),(r'Israel','Israel'),
(r'United Arab Emirates|UAE|Dubai','United Arab Emirates'),(r'South Africa','South Africa')]
UA={'User-Agent':'DalitFinder/0.5 (+https://github.com/ryanbytes/Dfdata)'}
TODAY=date.today(); NOW=datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00','Z')

def get(url, data=None, headers=None):
    h=dict(UA); h.update(headers or {})
    req=urllib.request.Request(url,data=data,headers=h,method='POST' if data else 'GET')
    with urllib.request.urlopen(req,timeout=60) as r:return r.read()
def jget(url,**kw):return json.loads(get(url,**kw).decode())
def canon(s):
    s=s.lower().replace('&',' and '); s=re.sub(r'\b(incorporated|inc|llc|ltd|limited|corp|corporation|company|co)\b\.?',' ',s)
    return re.sub(r'[^a-z0-9]+',' ',s).strip()
def slug(s):return (re.sub(r'[^a-z0-9]+','-',s.lower()).strip('-')[:96] or 'company')
def ckey(st,city):return st.upper(),re.sub(r'[^a-z0-9]+',' ',re.sub(r'\b(city|town|village|borough|municipality|cdp)\b$','',city.lower()).strip()).strip()
def country(loc):
    if re.search(r'United States|\bUSA\b|\bU\.S\.\b',loc,re.I):return None
    for p,c in COUNTRIES:
        if re.search(p,loc,re.I):return c
    return None
def centroids():
    z=zipfile.ZipFile(io.BytesIO(get(GAZ))); name=next(n for n in z.namelist() if n.endswith('.txt'))
    out={}; rows=csv.DictReader(io.StringIO(z.read(name).decode('utf-8-sig')),delimiter='\t')
    for r in rows:
        try: out.setdefault(ckey(r['USPS'],r['NAME']),(float(r['INTPTLAT']),float(r['INTPTLONG'])))
        except Exception: pass
    return out

def collect_jobs(src):
    if src['provider']=='WORKDAY':
        ep=f"https://{src['host']}/wday/cxs/{src['tenant']}/{src['site']}/jobs"; out=[]; off=0
        while off<300:
            d=jget(ep,data=json.dumps({'appliedFacets':{},'limit':20,'offset':off,'searchText':''}).encode(),headers={'Content-Type':'application/json'})
            page=d.get('jobPostings') or []
            for x in page:
                loc=(x.get('locationsText') or '').strip(); c=country(loc); path=x.get('externalPath')
                if c and path: out.append({'id':str(path).rstrip('/').split('/')[-1],'title':x.get('title') or '', 'location':loc,'country':c,'url':urllib.parse.urljoin(f"https://{src['host']}",path)})
            off+=len(page)
            if len(page)<20:break
        return out
    ep=f"https://boards-api.greenhouse.io/v1/boards/{src['board_token']}/jobs"; out=[]
    for x in jget(ep).get('jobs') or []:
        loc=((x.get('location') or {}).get('name') or '').strip(); c=country(loc)
        if c:out.append({'id':str(x.get('id')),'title':x.get('title') or '','location':loc,'country':c,'url':x.get('absolute_url') or ep})
    return out

def ats_history():
    STATE.mkdir(parents=True,exist_ok=True); p=STATE/'ats_history.json'
    try:h=json.loads(p.read_text())
    except Exception:h={'sources':{}}
    by=defaultdict(list); errs=[]
    for s in json.loads(SOURCES.read_text()):
        st=h['sources'].setdefault(s['id'],{'company':s['company'],'jobs':{}})
        try:
            fresh=collect_jobs(s)
            for old in st['jobs'].values():old['active']=False
            for x in fresh:
                old=st['jobs'].get(x['id']); x['first_seen']=old.get('first_seen',NOW) if old else NOW; x['last_seen']=NOW; x['active']=True; st['jobs'][x['id']]=x
        except Exception as e:errs.append(f"{s['id']}: {e}")
        vals=list(st['jobs'].values()); by[canon(s['company'])].extend(vals)
        for a in s.get('aliases',[]):by[canon(a)].extend(vals)
    h['updated_at']=NOW;p.write_text(json.dumps(h,sort_keys=True,separators=(',',':'))+'\n');return by,errs

def coverage(states,errs):
    known={x['state']:x for x in states}; rows=[]
    for st in ALL:
        if st in known:
            x=known[st]; rows.append({'state':st,'status':'active','agency':x.get('agency'),'last_filed':x.get('last_filed'),'coverage':x.get('coverage'),'source':'normalized state WARN records'})
        else:
            a,u,s=SUP.get(st,(None,None,'no_automated_source'));rows.append({'state':st,'status':s,'agency':a,'last_filed':None,'coverage':None,'source_url':u})
    return {'schema':1,'generated_at':NOW,'jurisdictions':rows,'disclaimer':'Coverage varies by jurisdiction. A missing record is not evidence that no layoff occurred.','ats_errors':errs}

def main():
    FEED.mkdir(parents=True,exist_ok=True); notices=jget(NOTICES); states=jget(STATES); geo=centroids(); jobs,errs=ats_history(); matches={}
    for n in notices:
        st=(n.get('state') or '').upper(); company=(n.get('company') or '').strip(); day=(n.get('received_date') or n.get('effective_date') or '')[:10]
        try:d=date.fromisoformat(day)
        except Exception:continue
        if not st or not company or d<TODAY-timedelta(days=730) or d>TODAY:continue
        rel=[]
        for x in jobs.get(canon(company),[]):
            try:f=date.fromisoformat(x['first_seen'][:10])
            except Exception:continue
            if d<=f<=d+timedelta(days=540):rel.append(x)
        if not rel:continue
        cid=slug(company); city=(n.get('city') or '').strip(); cs=sorted({x['country'] for x in rel}); c=matches.setdefault(cid,{'id':cid,'name':company,'industry':str(n.get('industry') or ''),'events':[],'signals':[],'locations':[]})
        c['events'].append({'id':str(n.get('id') or f'{cid}-{day}-{st}'),'date':day,'us_location':', '.join(x for x in [city,st] if x),'workers_affected':n.get('num_affected') if isinstance(n.get('num_affected'),int) else None,'rating':'POSSIBLE','rationale':f"A documented U.S. WARN event overlaps with {len(rel)} foreign job-posting signal(s) ({', '.join(cs)}). This does not prove replacement of U.S. workers.",'overseas_activity_count':len(rel),'countries':cs,'source_url':'https://github.com/kadoa-org/layoffs-tracker'})
        c['signals']+=rel
        co=geo.get(ckey(st,city)) if city else None
        if co and not c['locations']:
            c['locations'].append({'id':f'{cid}-{st}-{slug(city)}','name':f'{company} — {city} WARN location','address':f'{city}, {st}','latitude':round(co[0],6),'longitude':round(co[1],6),'location_precision':'CITY'})
    companies=[]
    for c in matches.values():
        c['signals']=list({(x['url'],x['title'],x['location']):x for x in c['signals']}.values());c['events'].sort(key=lambda x:x['date'],reverse=True);c['overseas_activity_count']=len(c['signals']);c['countries']=sorted({x['country'] for x in c['signals']});companies.append(c)
    companies.sort(key=lambda x:(x['events'][0]['date'],x['name']),reverse=True);cov=coverage(states,errs);payload={'schema':1,'generated_at':NOW,'companies':companies};text=json.dumps(payload,ensure_ascii=False,sort_keys=True,separators=(',',':'))+'\n'
    (FEED/'companies.json').write_text(text);(FEED/'coverage.json').write_text(json.dumps(cov,sort_keys=True,separators=(',',':'))+'\n');(FEED/'stats.json').write_text(json.dumps({'generated_at':NOW,'matched_companies':len(companies),'matched_events':sum(len(x['events']) for x in companies),'ats_errors':len(errs)},sort_keys=True,separators=(',',':'))+'\n')
    with gzip.GzipFile(filename='',mode='wb',fileobj=open(FEED/'companies.json.gz','wb'),compresslevel=9,mtime=0) as f:f.write(text.encode())
if __name__=='__main__':main()

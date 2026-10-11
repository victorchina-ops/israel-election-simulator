import concurrent.futures, datetime, hashlib, json, pathlib, re, urllib.request
from html.parser import HTMLParser

OUT = pathlib.Path(__file__).parent
SOURCES = {
 'n12-home':'https://www.n12.co.il/',
 'n12-politics':'https://www.mako.co.il/news-politics',
 'n12-elections':'https://www.mako.co.il/news-israel-elections/2026',
 'c13-home':'https://13tv.co.il/',
 'c13-politics':'https://13tv.co.il/news/politics/',
 'c13-political-index':'https://13tv.co.il/news/politics/politics/',
 'c14-home':'https://www.c14.co.il/',
 'c14-politics':'https://www.c14.co.il/archive/65839',
 'c14-elections':'https://www.c14.co.il/elections26',
 'i24-home':'https://www.i24news.tv/he',
 'i24-elections':'https://www.i24news.tv/he/news/israel-elections-2026',
 'maariv-home':'https://www.maariv.co.il/',
 'maariv-politics':'https://www.maariv.co.il/news/politics',
 'maariv-last-known':'https://www.maariv.co.il/news/politics/article-1375198',
 'zman-home':'https://www.zman.co.il/',
 'zman-polls':'https://www.zman.co.il/feed/33350/',
 'ih-home':'https://www.israelhayom.co.il/',
 'ih-news':'https://www.israelhayom.co.il/news',
 'ih-politics':'https://www.israelhayom.co.il/news/politics',
 'to120-data':'https://twonetwenty.com/data',
 'to120-evidence':'https://twonetwenty.com/he/evidence',
 'ch16-home':'https://www.ch16.co.il/',
}

class Extract(HTMLParser):
 def __init__(self):
  super().__init__(); self.a=None; self.links=[]; self.parts=[]; self.skip=0
 def handle_starttag(self,tag,attrs):
  attrs=dict(attrs)
  if tag in ['script','style']: self.skip+=1
  if tag=='a': self.a=[attrs.get('href'),[]]
 def handle_endtag(self,tag):
  if tag in ['script','style']: self.skip=max(0,self.skip-1)
  if tag=='a' and self.a:
   self.links.append({'href':self.a[0],'text':' '.join(self.a[1]).strip()}); self.a=None
 def handle_data(self,data):
  if not self.skip:
   data=' '.join(data.split())
   if data: self.parts.append(data)
   if data and self.a: self.a[1].append(data)

def fetch(item):
 name,url=item
 receipt={'name':name,'requestedUrl':url,'fetchedAtUtc':datetime.datetime.now(datetime.timezone.utc).isoformat()}
 try:
  req=urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0'})
  with urllib.request.urlopen(req,timeout=35) as res:
   body=res.read(); receipt.update(status=res.status,finalUrl=res.url,contentType=res.headers.get('Content-Type'))
  (OUT/(name+'.html')).write_bytes(body)
  parser=Extract(); parser.feed(body.decode('utf-8',errors='replace'))
  text='\n'.join(parser.parts)
  (OUT/(name+'.txt')).write_text(text,encoding='utf-8')
  (OUT/(name+'-links.json')).write_text(json.dumps(parser.links,ensure_ascii=False,indent=2),encoding='utf-8')
  receipt.update(bytes=len(body),sha256=hashlib.sha256(body).hexdigest(),pollLinks=[x for x in parser.links if re.search('סקר|poll',x['text'],re.I)])
 except Exception as err: receipt.update(status='inaccessible',error=str(err))
 return receipt

if __name__=='__main__':
 with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool: receipts=list(pool.map(fetch,SOURCES.items()))
 (OUT/'network-receipts.json').write_text(json.dumps(receipts,ensure_ascii=False,indent=2),encoding='utf-8')
 for row in receipts: print(json.dumps(row,ensure_ascii=False))

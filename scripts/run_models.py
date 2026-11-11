#!/usr/bin/env python3
"""OpenRouter calls with immutable attempts; API key is never serialized."""
import argparse, concurrent.futures, getpass, json, os, re, ssl, time, urllib.request
from pathlib import Path

def request(url, body=None, key=None):
    import certifi
    headers={'Content-Type':'application/json'}
    if key: headers['Authorization']='Bearer '+key
    req=urllib.request.Request(url, data=None if body is None else json.dumps(body).encode(), headers=headers)
    with urllib.request.urlopen(req, timeout=1200, context=ssl.create_default_context(cafile=certifi.where())) as f:
        return json.load(f)

def extract(content):
    content=content.strip()
    match=re.fullmatch(r'```(?:html)?\s*([\s\S]*?)\s*```',content)
    return match.group(1) if match else content

def run_one(item, cfg, root, key):
    mid=item['id'];slug=re.sub(r'[^a-zA-Z0-9_.-]','_',mid)
    base=root/slug;base.mkdir(parents=True,exist_ok=True)
    for i in range(1,10000):
        target=base/f'attempt-{i:03d}'
        try: target.mkdir();break
        except FileExistsError: continue
    body={'model':mid,'messages':[{'role':'system','content':cfg.get('system','Return only a complete single-file HTML document. Use public CDN dependencies where needed. No prose.')},{'role':'user','content':cfg['prompt']}], 'max_tokens':item.get('max_tokens',cfg.get('max_tokens',64000))}
    if 'reasoning' in cfg: body['reasoning']=cfg['reasoning']
    (target/'request.json').write_text(json.dumps(body,indent=2),encoding='utf-8')
    start=time.monotonic()
    try:
        data=request('https://openrouter.ai/api/v1/chat/completions',body,key)
        elapsed=time.monotonic()-start
        (target/'response.json').write_text(json.dumps(data,indent=2),encoding='utf-8')
        choice=data.get('choices',[{}])[0];content=choice.get('message',{}).get('content') or ''
        html=extract(content) if isinstance(content,str) else ''
        (target/'scene.html').write_text(html,encoding='utf-8')
        status='needs_browser_validation' if choice.get('finish_reason')=='stop' and '</html>' in html.lower() else 'incomplete'
        cost=data.get('usage',{}).get('cost')
        meta={'model':mid,'elapsed_seconds':elapsed,'cost_usd':cost,'finish_reason':choice.get('finish_reason'),'status':status,'attempt':i,'max_tokens':body['max_tokens']}
    except Exception as e:
        meta={'model':mid,'status':'request_failed','error_type':type(e).__name__,'elapsed_seconds':time.monotonic()-start,'attempt':i}
    (target/'metrics.json').write_text(json.dumps(meta,indent=2),encoding='utf-8')
    print(json.dumps({**meta,'path':str(target)}),flush=True)
    return meta

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--catalog',type=Path);p.add_argument('--config',type=Path);p.add_argument('--output',type=Path);p.add_argument('--workers',type=int,default=3);a=p.parse_args()
    if a.catalog:
        a.catalog.parent.mkdir(parents=True,exist_ok=True);a.catalog.write_text(json.dumps(request('https://openrouter.ai/api/v1/models'),indent=2));return
    if not a.config or not a.output:p.error('--config and --output are required')
    cfg=json.loads(a.config.read_text());assert isinstance(cfg['prompt'],str) and cfg['prompt'];assert cfg['models']
    key=os.environ.get('OPENROUTER_API_KEY') or getpass.getpass('OpenRouter key: ')
    if not key: p.error('Missing OpenRouter key')
    a.output.mkdir(parents=True,exist_ok=True)
    with concurrent.futures.ThreadPoolExecutor(max_workers=max(1,min(a.workers,4))) as pool:
        results=list(pool.map(lambda item:run_one(item,cfg,a.output,key),cfg['models']))
    if any(x['status']!='needs_browser_validation' for x in results):raise SystemExit(2)
if __name__=='__main__':main()

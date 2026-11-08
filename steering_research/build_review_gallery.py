"""Build a LOCAL, self-contained visual review gallery from candidate cross-split pairs.

The HTML embeds source-video images; do not upload/commit or redistribute without rights.
It does NOT decide whether two clips are from the same recording.
"""
from __future__ import annotations
import argparse
import base64
import csv
import html
import io
from pathlib import Path
from PIL import Image, ImageOps


def thumb(image_path, maximum=(240,150)):
    if not image_path:
        return None
    path=Path(image_path)
    if not path.exists():
        return None
    try:
        with Image.open(path) as img:
            img=ImageOps.exif_transpose(img).convert('RGB')
            img.thumbnail(maximum)
            out=io.BytesIO()
            img.save(out,format='JPEG',quality=68,optimize=True)
            return 'data:image/jpeg;base64,'+base64.b64encode(out.getvalue()).decode('ascii')
    except (OSError, ValueError):
        return None


def make_gallery(csv_path, output, limit=60):
    with Path(csv_path).open('r',encoding='utf-8-sig',newline='') as fh:
        rows=list(csv.DictReader(fh))
    if not rows:
        raise ValueError('No cross-split similarity candidates found; no gallery needed')
    blocks=[]
    found=0
    for idx,row in enumerate(rows[:limit],start=1):
        images=[]
        for suffix in ('a','b'):
            data=thumb(row.get('frame_'+suffix,''))
            if data:
                found+=1
                image=f'<img src="{data}" alt="Review frame {suffix}"/>'
            else:
                image='<div class="missing">Local image path unavailable</div>'
            images.append('<div><strong>'+html.escape(row.get('video_id_'+suffix,''))+'</strong>'
                          +'<p>'+html.escape(row.get('partition_'+suffix,''))+' · '+
                          html.escape(row.get('angle_'+suffix+'_deg',''))+'°</p>'+image+'</div>')
        blocks.append('<article><h2>Candidate '+str(idx)+' · pHash '+html.escape(row.get('phash_distance',''))+
                      ' · '+html.escape(row.get('priority',''))+'</h2><div class="images">'+''.join(images)+
                      '</div><p>Frame A: '+html.escape(row.get('frame_a',''))+'</p><p>Frame B: '+
                      html.escape(row.get('frame_b',''))+'</p><p><b>Record decision in CSV:</b> SAME_SOURCE / '
                      'DIFFERENT_SOURCE / UNCERTAIN; support it with source-video evidence.</p></article>')
    page='''<!doctype html><html lang="en"><meta charset="utf-8"/><title>Local F1 source review</title>
    <style>body{font:15px system-ui,Arial;background:#0f1622;color:#e6eaf1;max-width:1100px;margin:auto;padding:24px}
    article{background:#1e293b;border-radius:14px;padding:20px;margin:20px 0}
    .images{display:grid;grid-template-columns:1fr 1fr;gap:14px}.images>div{min-width:0}
    img{max-width:100%;border-radius:6px}.missing{padding:32px;background:#354359}
    p{overflow-wrap:anywhere;color:#cbd5e1}h1,h2{font-weight:650}
    @media(max-width:580px){.images{grid-template-columns:1fr}}</style><h1>Cross-split frame review — LOCAL ONLY</h1>
    <p>Visual hash similarity alone does not establish matching source video. This file embeds copyrighted-source
    imagery on YOUR machine for inspection only; do not commit, upload, or redistribute it without permission.</p>'''
    page+=''.join(blocks)+'</html>'
    output=Path(output)
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(page,encoding='utf-8')
    return {'candidate_pairs':min(limit,len(rows)),'images_embedded':found,'output':str(output)}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--review-csv',required=True)
    p.add_argument('--output',default='results/steering_split_review/cross_split_gallery_LOCAL_ONLY.html')
    p.add_argument('--limit',type=int,default=60)
    a=p.parse_args()
    print(make_gallery(a.review_csv,a.output,a.limit))

if __name__=='__main__':main()

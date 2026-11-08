"""Plot measured training loss and per-epoch validation MAE as a standalone SVG.

Never infer convergence from training loss alone. Old history files without validation
values produce only a training-loss plot and disclose the missing series.
"""
from __future__ import annotations
import argparse
import html
import json
from pathlib import Path


def series_panel(values, title, unit, top, bottom, stroke, x_max):
    x0, x1 = 105, 885
    if not values:
        return (f'<text x="110" y="{(top+bottom)//2}" fill="#9aa8b8" font-size="16">'
                'No per-epoch validation metrics in this history</text>')
    low, high = min(values), max(values)
    if high <= low:
        pad = max(abs(low)*.05, 1.0)
        high, low = high+pad, low-pad
    else:
        pad = max((high-low)*.08, .01)
        high, low = high+pad, low-pad
    points = [(x0+i*(x1-x0)/max(x_max-1,1), bottom-(v-low)/(high-low)*(bottom-top))
              for i,v in enumerate(values)]
    path = ' '.join(f'{x:.1f},{y:.1f}' for x,y in points)
    dots = ''.join(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="3.5" fill="{stroke}"/>' for x,y in points)
    return (f'<text x="105" y="{top-21}" font-size="19" font-weight="bold" fill="#edf2fa">'
            f'{html.escape(title)} ({unit})</text>'
            f'<path d="M{x0} {top}V{bottom}H{x1}" fill="none" stroke="#516079" stroke-width="1.2"/>'
            f'<text x="52" y="{top+5}" font-size="14" fill="#cbd5e1">{high:.2f}</text>'
            f'<text x="52" y="{bottom+5}" font-size="14" fill="#cbd5e1">{low:.2f}</text>'
            f'<polyline fill="none" stroke="{stroke}" stroke-width="3" points="{path}"/>{dots}')


def render(history_file, output_file):
    data = json.loads(Path(history_file).read_text(encoding='utf-8'))
    rows = data.get('history', [])
    if not rows:
        raise ValueError('No epochs in training history')
    train = [float(r['train_smooth_l1']) for r in rows]
    val_rows = [r for r in rows if r.get('validation_mae_deg') is not None]
    val = [float(r['validation_mae_deg']) for r in val_rows] if len(val_rows)==len(rows) else []
    n = len(rows)
    body = series_panel(train,'Training SmoothL1 loss','loss',140,335,'#ef6b66',n)
    body += series_panel(val,'Validation MAE','degrees',440,635,'#62b5ff',n)
    best_epoch = data.get('best_epoch')
    best_text = (f'Best validation epoch: {int(best_epoch)}' if best_epoch and val else
                 'Best validation epoch: unavailable')
    ticks = ''.join(f'<text x="{105+i*780/max(n-1,1):.1f}" y="687" fill="#cad4e2" '
                    f'font-size="13" text-anchor="middle">{i+1}</text>'
                    for i in range(n) if i==0 or i==n-1 or i%(max(1,n//10))==0)
    subtitle = (f'{best_text} · {len(rows)} epochs · '
                'exploratory; source-footage independence not certified')
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="1000" height="730" viewBox="0 0 1000 730">'
           '<rect width="1000" height="730" fill="#101722"/>'
           f'<text x="60" y="51" font-family="Arial" font-size="27" font-weight="bold" fill="white">'
           f'Steering CV training &amp; validation · {html.escape(str(data.get("mode","model")))}</text>'
           f'<text x="60" y="80" font-family="Arial" font-size="14" fill="#cbd5e1">'
           f'{html.escape(subtitle)}</text><g font-family="Arial">{body}{ticks}'
           '<text x="495" y="717" font-size="15" fill="#cbd5e1" text-anchor="middle">Epoch</text>'
           '</g></svg>')
    out = Path(output_file)
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(svg,encoding='utf-8')
    return out


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--history',required=True)
    p.add_argument('--output',required=True)
    a=p.parse_args()
    print(f'Wrote {render(a.history,a.output)}')


if __name__=='__main__': main()

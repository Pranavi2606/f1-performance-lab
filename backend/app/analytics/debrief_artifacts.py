"""Public-data debrief artifacts. Inferred regions are never official FIA corner numbers."""
from __future__ import annotations
from datetime import datetime
from html import escape
from io import BytesIO
from typing import Any
import math


def _ts(s: str) -> float:
    return datetime.fromisoformat(s.replace('Z', '+00:00')).timestamp()


def map_for_lap(location: list[dict[str, Any]], lap: dict[str, Any], corner_ranges: list[list[float]] | None = None) -> dict[str, Any]:
    """Map XY observations in one lap to normalized within-lap progress; corner ranges are proxies."""
    start = _ts(lap['date_start'])
    duration = float(lap['lap_duration'])
    if duration <= 0:
        return {'ready': False, 'reason': 'Invalid lap duration'}
    rows: list[tuple[float,float,float]] = []
    for p in location:
        if p.get('x') is None or p.get('y') is None or not p.get('date'):
            continue
        try:
            t = _ts(p['date'])
            x, y = float(p['x']), float(p['y'])
            if start <= t <= start + duration and math.isfinite(x) and math.isfinite(y):
                rows.append((t,x,y))
        except (ValueError,TypeError):
            continue
    rows.sort()
    if len(rows) < 12:
        return {'ready':False,'reason':'Insufficient GPS XY observations for the selected lap'}
    # The public coordinates use arbitrary units. Elapsed-lap fraction is for label placement,
    # not a verified physical path-distance mapping. Large position glitches can distort the trace.
    stride = max(1, len(rows)//450)
    sampled = rows[::stride]
    if sampled[-1] != rows[-1]:
        sampled.append(rows[-1])
    points=[{'x':round(x,2),'y':round(y,2),'progress_pct':round((t-start)*100/duration,2)} for t,x,y in sampled]
    corners=[]
    for i, bounds in enumerate(corner_ranges or [],1):
        if len(bounds)!=2: continue
        midpoint=(float(bounds[0])+float(bounds[1]))/2
        p=min(points,key=lambda p:abs(p['progress_pct']-midpoint))
        corners.append({'id':i,'x':p['x'],'y':p['y'],'progress_pct':p['progress_pct'],
                        'label':f'Zone {i}', 'origin':'inferred_braking_zone'})
    return {'ready':True,'points':points,'markers':corners, 'source':'OpenF1 location XY',
            'reference_lap':int(lap['lap_number']),
            'note':'Markers are inferred telemetry braking zones, not official track corner IDs. XY coordinates are approximate and the location feed may be noisy.'}


def render_markdown(report: dict[str, Any]) -> str:
    primary=report.get('primary_driver') or {}
    comparisons=report.get('comparisons') or []
    lines=['# Driver Performance Debrief',
           '',
           f"**Event:** {report.get('race_name','Unavailable')} · {report.get('year','?')} · Round {report.get('round','?')}",
           f"**Source:** OpenF1 public car telemetry and lap records · Session {report.get('session_key','?')}",
           f"**Reference driver:** {primary.get('full_name','Unavailable')} · lap {primary.get('lap_number','?')} · {primary.get('lap_time_s','?')} s",
           '', '## One-to-many comparison', '',
           '| Comparison | Lap | Lap time (s) | Delta vs reference (s) |',
           '|---|---:|---:|---:|']
    for c in comparisons:
        lines.append(f"| {c.get('compare_driver','?')} | {c.get('compare_lap_number','?')} | {c.get('compare_lap_time_s','?')} | {c.get('lap_delta_s','?')} |")
    for c in comparisons:
        lines.extend(['',f"## {c.get('compare_driver','Comparison')} corner-like debrief",'',
                      c.get('overall_summary','No summary available.'),'',
                      '| Zone | Lap range (%) | Approx. delta (s) | Observation |',
                      '|---|---|---:|---|'])
        for z in c.get('corner_comparisons',[]):
            bounds=z.get('window_pct',[])
            range_text='–'.join(f'{float(x):.1f}' for x in bounds) if len(bounds)==2 else 'Unavailable'
            summary=str(z.get('summary','')).replace('|','/')
            lines.append(f"| {z.get('corner_like_segment','?')} | {range_text} | {z.get('compare_minus_primary_time_s','?')} | {summary} |")
    lines.extend(['','## Measurement and validity notes','',
                  '- **Measured public data:** speed, throttle, binary brake, gear, RPM, lap timestamps and available location XY.',
                  '- **Derived:** progress-aligned overlays and approximate time deltas.',
                  '- **Not available:** official steering angle, yaw/slip, brake pressure, true tyre wear, and direct oversteer/understeer diagnosis.',
                  '- Corner markers and braking windows are inferred heuristics, not official FIA corner IDs.',
                  '- A CV steering-angle series, when uploaded, is an experimental visual estimate and must be independently validated; it is not official telemetry.',
                  '- Faster/slower observations do not establish causal explanations or vehicle balance.',
                  '- Comparing independently fastest race laps may involve different fuel loads, tyre compounds, traffic or weather.',
                  '',f"**Model limitation:** {report.get('limitations','Unavailable')}",''])
    return '\n'.join(lines)


def render_pdf(report: dict[str, Any]) -> bytes:
    """Readable, evidence-first technical debrief. Graphs use observed/derived traces only."""
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.enums import TA_CENTER
    from reportlab.lib.pagesizes import A4
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, KeepTogether, PageBreak
    from reportlab.graphics.shapes import Drawing, Line, PolyLine, String, Rect

    buf=BytesIO()
    page_w,page_h=A4
    doc=SimpleDocTemplate(buf,pagesize=A4,leftMargin=42,rightMargin=42,topMargin=42,bottomMargin=44,
        title='F1 Driver Performance Debrief')
    styles=getSampleStyleSheet()
    styles.add(ParagraphStyle(name='DebTitle',parent=styles['Title'],fontName='Helvetica-Bold',fontSize=20,leading=25,textColor=colors.HexColor('#132238'),spaceAfter=10))
    styles.add(ParagraphStyle(name='DebSubtitle',parent=styles['Normal'],fontSize=11,leading=16,textColor=colors.HexColor('#4e6075'),spaceAfter=10))
    styles.add(ParagraphStyle(name='DebHeading',parent=styles['Heading2'],fontSize=14,leading=19,textColor=colors.HexColor('#132238'),spaceBefore=14,spaceAfter=8))
    styles.add(ParagraphStyle(name='DebBody',parent=styles['Normal'],fontSize=9.5,leading=14,spaceAfter=6,textColor=colors.HexColor('#28384e')))
    styles.add(ParagraphStyle(name='DebTiny',parent=styles['Normal'],fontSize=8,leading=11,spaceAfter=5,textColor=colors.HexColor('#617184')))
    styles.add(ParagraphStyle(name='DebCell',parent=styles['Normal'],fontSize=8.5,leading=12,textColor=colors.HexColor('#223247')))
    styles.add(ParagraphStyle(name='DebCellHeading',parent=styles['DebCell'],fontName='Helvetica-Bold',textColor=colors.white))
    primary=report.get('primary_driver') or {}
    comparisons=report.get('comparisons') or []
    esc=lambda s:escape(str(s))
    story=[Paragraph('F1 DRIVER PERFORMANCE DEBRIEF',styles['DebTitle']),
      Paragraph(f"{esc(report.get('race_name','Unavailable'))}  |  {esc(report.get('year','?'))}  |  OpenF1 public historical data  |  Session {esc(report.get('session_key','?'))}",styles['DebSubtitle']),
      Paragraph(f"<b>Reference:</b> {esc(primary.get('full_name','Unavailable'))}  |  Lap {esc(primary.get('lap_number','?'))}  |  {esc(primary.get('lap_time_s','?'))} s",styles['DebBody']),
      Paragraph('OVERVIEW',styles['DebHeading'])]
    data=[['COMPARISON DRIVER','LAP','LAP TIME','DELTA VS REF']]
    for c in comparisons:
      data.append([esc(c.get('compare_driver','?')),esc(c.get('compare_lap_number','?')),f"{float(c.get('compare_lap_time_s',0)):.3f} s",f"{float(c.get('lap_delta_s',0)):+.3f} s"])
    if len(data)==1: data.append(['No comparison','-','-','-'])
    table=Table([[Paragraph(esc(cell), styles['DebCellHeading'] if row_idx==0 else styles['DebCell']) for cell in row] for row_idx,row in enumerate(data)],colWidths=[235,60,100,110],repeatRows=1,hAlign='LEFT')
    table.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#203247')),
      ('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.white,colors.HexColor('#f0f4f8')]),
      ('BOX',(0,0),(-1,-1),.4,colors.HexColor('#d5dee9')),('VALIGN',(0,0),(-1,-1),'MIDDLE'),
      ('LEFTPADDING',(0,0),(-1,-1),10),('BOTTOMPADDING',(0,0),(-1,-1),8),('TOPPADDING',(0,0),(-1,-1),8)]))
    story.append(table)
    story.extend([Spacer(1,8),Paragraph('Negative delta means the comparison lap is faster. Different lap numbers, fuel loads, compounds and track conditions can influence results.',styles['DebTiny'])])

    def delta_plot(rows: list[dict[str,Any]]) -> Drawing | None:
      samples=[]
      for p in rows:
        try:
          x=float(p['progress_pct']); y=float(p['delta_time_s'])
          if math.isfinite(x) and math.isfinite(y): samples.append((x,y))
        except (ValueError,KeyError,TypeError): continue
      if len(samples)<4:return None
      W=500;H=190;L=48;R=16;B=35;T=18
      ys=[v for _,v in samples]
      ylo=min(min(ys),0);yhi=max(max(ys),0)
      if yhi-ylo<.1:yhi=ylo+.1
      pad=max((yhi-ylo)*.07,.025);ylo-=pad;yhi+=pad
      sx=lambda x:L+(W-L-R)*min(100,max(0,x))/100
      sy=lambda y:B+(H-B-T)*(y-ylo)/(yhi-ylo)
      d=Drawing(W,H)
      d.add(Rect(0,0,W,H,fillColor=colors.HexColor('#f7f9fc'),strokeColor=colors.HexColor('#dce4ed'),strokeWidth=.6,rx=6,ry=6))
      for j in range(5):
        y=ylo+(yhi-ylo)*j/4
        d.add(Line(L,sy(y),W-R,sy(y),strokeColor=colors.HexColor('#e2e8f0'),strokeWidth=.5))
        d.add(String(L-7,sy(y)-2,f'{y:+.2f}',textAnchor='end',fontSize=8,fillColor=colors.HexColor('#58687b')))
      for v in (0,25,50,75,100):
        d.add(String(sx(v),B-17,f'{v}%',textAnchor='middle',fontSize=8,fillColor=colors.HexColor('#58687b')))
      d.add(Line(L,sy(0),W-R,sy(0),strokeColor=colors.HexColor('#8a97a8'),strokeWidth=1))
      coords=[]
      for x,y in samples:
        coords.extend([sx(x),sy(y)])
      d.add(PolyLine(coords,strokeColor=colors.HexColor('#d62d2a'),strokeWidth=2,fillColor=None))
      d.add(String(W/2,10,'Normalized lap progress',textAnchor='middle',fontSize=8,fillColor=colors.HexColor('#58687b')))
      return d

    for c in comparisons:
      name=esc(c.get('compare_driver','Comparison'))
      heading=Paragraph(name,styles['DebHeading'])
      summary=Paragraph(f"<b>Lap {esc(c.get('compare_lap_number','?'))}</b> · {esc(c.get('compare_lap_time_s','?'))} s · <b>Difference:</b> {float(c.get('lap_delta_s',0)):+.3f} s vs reference",styles['DebBody'])
      story.extend([Spacer(1,12),heading,summary])
      chart=delta_plot(c.get('trace') or [])
      if chart is not None:
        story.extend([Paragraph('Approximate lap-time delta',styles['DebBody']),chart,Spacer(1,6),
          Paragraph('Positive = comparison behind reference. Aligned to normalized lap progress, not validated common track position.',styles['DebTiny'])])
      else:
        story.append(Paragraph('Delta chart unavailable: insufficient aligned trace samples.',styles['DebTiny']))
      segments=c.get('corner_comparisons') or []
      if segments:
        story.append(Paragraph('Detected braking-zone comparison',styles['DebHeading']))
        rows=[['ZONE','LAP WINDOW','DELTA','MIN SPEED (REF / CMP)','EXIT SPEED (REF / CMP)']]
        for z in segments[:10]:
          bounds=z.get('window_pct') or []
          rng='–'.join(f'{float(v):.1f}%' for v in bounds) if len(bounds)==2 else '—'
          a=z.get('primary') or {};b=z.get('compare') or {}
          rows.append([str(z.get('corner_like_segment','?')),rng,f"{float(z.get('compare_minus_primary_time_s',0)):+.3f} s",
                f"{float(a.get('min_speed_kph',0)):.1f} / {float(b.get('min_speed_kph',0)):.1f}",
                f"{float(a.get('exit_speed_kph',0)):.1f} / {float(b.get('exit_speed_kph',0)):.1f}"])
        t=Table([[Paragraph(esc(cell),styles['DebCellHeading'] if i==0 else styles['DebCell']) for cell in row] for i,row in enumerate(rows)],colWidths=[42,96,60,146,161],repeatRows=1,hAlign='LEFT')
        t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#203247')),
          ('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.white,colors.HexColor('#f0f4f8')]),
          ('VALIGN',(0,0),(-1,-1),'MIDDLE'),('BOTTOMPADDING',(0,0),(-1,-1),7),('TOPPADDING',(0,0),(-1,-1),7)]))
        story.append(t)
        story.append(Paragraph('Zone IDs are algorithmically inferred braking windows, not official FIA corner identifiers. Differences do not establish their cause.',styles['DebTiny']))
    story.extend([Spacer(1,12),Paragraph('MEASUREMENT LIMITATIONS',styles['DebHeading'])])
    for line in ['Observed public channels: speed, throttle, binary brake, gear, RPM and available XY location.',
      'Derived: progress-aligned telemetry overlays, approximate time deltas and inferred braking windows.',
      'Unavailable: measured steering angle, brake pressure, yaw/slip, true tyre wear and direct oversteer diagnosis.',
      'Experimental computer-vision wheel rotation, if uploaded, is not official steering telemetry and is not automatically synchronized.',
      str(report.get('limitations',''))]:
      story.append(Paragraph('• '+esc(line),styles['DebBody']))

    def footer(canvas, document):
      canvas.setFont('Helvetica',8)
      canvas.setFillColor(colors.HexColor('#718096'))
      canvas.drawString(42,24,'F1 Performance Lab · Historical public-data research · Not team telemetry')
      canvas.drawRightString(page_w-42,24,f'Page {document.page}')
    doc.build(story,onFirstPage=footer,onLaterPages=footer)
    return buf.getvalue()

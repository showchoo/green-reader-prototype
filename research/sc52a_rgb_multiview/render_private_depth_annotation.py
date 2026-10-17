#!/usr/bin/env python3
"""Create a single-file OFFLINE viewer for privately held v11.1 DEPTH16 ZIPs.

Image colors are diagnostic only. A selected polygon is an *annotation*,
never an independently verified board, pose, world slope or green contour.
Nothing connects to a server. The original ZIP/raw depth is not embedded;
a coarse display preview is embedded, so HTML remains private as well.
"""
import argparse
import base64
import hashlib
import html
import json
import math
from pathlib import Path
import statistics
import struct
import zlib

from audit_depth16_confidence_stability import read_session


def sha256(path):
    h=hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda:stream.read(1<<20),b""):
            h.update(chunk)
    return h.hexdigest()


def png_chunk(tag,data):
    return struct.pack(">I",len(data))+tag+data+struct.pack(
        ">I",zlib.crc32(tag+data)&0xffffffff)


def encode_png_rgb(width,height,rgb):
    """stdlib PNG, color type 2, 8-bit; no EXIF or GPS metadata."""
    if width<=0 or height<=0 or len(rgb)!=width*height*3:
        raise ValueError("Invalid PNG dimensions or buffer")
    raw=b"".join(b"\x00"+rgb[y*width*3:(y+1)*width*3]
                 for y in range(height))
    return (b"\x89PNG\r\n\x1a\n"+
            png_chunk(b"IHDR",struct.pack(">IIBBBBB",width,height,8,2,0,0,0))+
            png_chunk(b"IDAT",zlib.compress(raw,level=6))+
            png_chunk(b"IEND",b""))


def percentile(values,percent):
    if not values:return None
    v=sorted(values)
    k=(len(v)-1)*percent/100
    a=int(k);b=min(len(v)-1,a+1)
    return v[a]*(b-k)+v[b]*(k-a)


def preview_images(session):
    """Median of available frames at each pixel; no spatial interpolation."""
    frames=session["raw_frames"]
    if not frames:raise ValueError("No valid DEPTH16 frames")
    w,h=session["width"],session["height"]
    values=[]
    for idx in range(w*h):
        mm=[int(frame[idx])&0x1fff for frame in frames]
        good=[v for v in mm if v>0]
        values.append(statistics.median(good) if good else 0)
    nonzero=[v for v in values if v>0]
    if len(nonzero)<100:raise ValueError("Insufficient valid distance pixels for preview")
    lo=percentile(nonzero,2);hi=percentile(nonzero,98)
    if hi-lo<10:hi=lo+10
    rgb=bytearray(w*h*3)
    for idx,mm in enumerate(values):
        if mm==0:
            color=(220,25,125)  # missing depth visibly magenta
        else:
            gray=round(255*max(0,min(1,(mm-lo)/(hi-lo))))
            color=(gray,gray,gray)
        rgb[idx*3:idx*3+3]=bytes(color)
    # Show last valid frame's vendor confidence, not certainty of real depth.
    selected=frames[-1]
    conf=bytearray(w*h*3)
    palette=((70,200,95),(50,50,50),(35,56,90),(60,92,150),
             (86,143,194),(140,178,207),(190,216,235),(245,246,249))
    for i,v in enumerate(selected):
        r=int(v)&8191
        conf[i*3:i*3+3]=bytes(palette[(int(v)>>13)&7] if r else (220,25,125))
    return (encode_png_rgb(w,h,bytes(rgb)),
            encode_png_rgb(w,h,bytes(conf)),
            {"distance_preview_p02_mm":round(lo,2),
             "distance_preview_p98_mm":round(hi,2),
             "nonzero_median_composite_pixels":len(nonzero),
             "confidence_preview_uses_last_valid_frame":True,
             "confidence_map_not_a_ground_truth_accuracy_metric":True})


HTML_TEMPLATE=r"""<!doctype html>
<html lang="ja">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>DEPTH16 private ROI review | OFFLINE</title>
<style>
:root{color-scheme:dark;font:16px/1.55 system-ui,sans-serif}
body{max-width:850px;margin:1rem auto;padding:0 12px;background:#101820;color:#e9f4f8}
h1{font-size:1.35rem;margin:0 0 .4rem}
.warning{border:2px solid #e8a055;background:#30271c;padding:12px;border-radius:8px}
pre{white-space:pre-wrap;overflow-wrap:anywhere;background:#18232d;padding:10px;border-radius:6px}
.toolbar{display:flex;gap:10px;flex-wrap:wrap;align-items:center;margin:14px 0}
button,select{padding:8px 12px;background:#284454;color:#fff;border:1px solid #6192ab;border-radius:6px}
button:disabled{opacity:.4}
.canvas{position:relative;max-width:100%;width:max-content;margin:auto;touch-action:none}
.canvas img{display:block;max-width:100%;height:auto;image-rendering:auto}
.canvas canvas{position:absolute;inset:0;width:100%;height:100%;touch-action:none;cursor:crosshair}
small{color:#a6bbc6}
</style>
</head><body>
<h1>Camera2 DEPTH16：四隅確認ツール（完全オフライン）</h1>
<div class="warning"><strong>重要：</strong> この画像は距離を可視化した診断図でありRGB写真ではありません。
板の四隅を画像上で明確に確認できない場合は<strong>クリックせず判定不能</strong>としてください。
仮に4点を指定しても、板の物理的な同定や傾斜精度を証明しません。</div>
<p>ZIP：<code id="name"></code>。深度画像の原点は左上、
右向きがx、下向きがyです。端末画面の回転表示とは異なります。</p>
<div class="toolbar">
<label>表示 <select id="mode">
<option value="distance">距離の中央値（濃淡）</option>
<option value="confidence">最終DEPTH16画像の信頼度コード（色）</option></select></label>
<button type="button" id="undo">最後の点を取り消す</button>
<button type="button" id="reset">四隅をやり直す</button>
<button type="button" id="save" disabled>四隅JSONを保存</button></div>
<div class="canvas" id="layer">
<img id="view" width="__WIDTH__" height="__HEIGHT__" alt="DEPTH16 derived diagnostic image">
<canvas id="overlay" width="__WIDTH__" height="__HEIGHT__"></canvas></div>
<p><small>クリックする順序：1 左上 → 2 右上 → 3 右下 → 4 左下。
4点が板そのものに対応することを確認できる場合のみ保存してください。
点を保存しても研究解析は承認されません。個人の測定記録として保管してください。</small></p>
<pre id="state" aria-live="polite"></pre>
<p><small>ピンク色は深度無効画素。距離画像の白黒は2%～98%点で表示用に伸縮しています。
色や輪郭は現実の材質・エッジを示しません。ネット送信・外部ライブラリ・CDNはありません。</small></p>
<script>
"use strict";
const DATA=__METADATA__;
const DISTANCE="__DISTANCE_PNG__";
const CONFIDENCE="__CONFIDENCE_PNG__";
const points=[];
const image=document.getElementById("view");
const canvas=document.getElementById("overlay");
const ctx=canvas.getContext("2d");
const state=document.getElementById("state");
const save=document.getElementById("save");
document.getElementById("name").textContent=DATA.zip_name;
const width=DATA.width,height=DATA.height;
function valid(pts) {
 if(pts.length!==4)return false;
 const area=pts.reduce((acc,p,i)=>{let q=pts[(i+1)%4];return acc+p[0]*q[1]-q[0]*p[1]},0);
 if(area<=width*height*.06)return false;
 for(let i=0;i<4;i++){
   const a=pts[i],b=pts[(i+1)%4],c=pts[(i+2)%4];
   const cross=(b[0]-a[0])*(c[1]-b[1])-(b[1]-a[1])*(c[0]-b[0]);
   if(cross<=0)return false;
 }
 if(!(pts[0][1]<pts[3][1]&&pts[1][1]<pts[2][1]&&
      pts[0][0]<pts[1][0]&&pts[3][0]<pts[2][0]))return false;
 return pts.every(p=>p[0]>=3&&p[0]<width-3&&p[1]>=3&&p[1]<height-3);
}
function draw(){
 ctx.clearRect(0,0,width,height);
 ctx.strokeStyle="rgba(50,220,255,.28)";ctx.lineWidth=1;
 for(let x=0;x<=width;x+=80){ctx.beginPath();ctx.moveTo(x,0);ctx.lineTo(x,height);ctx.stroke()}
 for(let y=0;y<=height;y+=80){ctx.beginPath();ctx.moveTo(0,y);ctx.lineTo(width,y);ctx.stroke()}
 if(points.length){ctx.strokeStyle="#ffcf6e";ctx.lineWidth=2;ctx.beginPath();
   ctx.moveTo(...points[0]);for(let i=1;i<points.length;i++)ctx.lineTo(...points[i]);
   if(points.length===4)ctx.closePath();ctx.stroke();
   points.forEach((p,i)=>{ctx.beginPath();ctx.fillStyle="#fcf6dd";
     ctx.arc(p[0],p[1],6,0,2*Math.PI);ctx.fill();ctx.fillStyle="#000";
     ctx.font="bold 12px system-ui";ctx.fillText(String(i+1),p[0]+7,p[1]-7)})}
 const allowed=valid(points);save.disabled=!allowed;
 state.textContent="座標 (x,y)："+JSON.stringify(points)+
  "\n状態："+(allowed?"四隅形式OK。ただし板の実体は未検証。":
         points.length===4?"四隅の順序・形状が不正。やり直してください。":
         "板が画像で確認できなければ指定しないでください。")+
  "\nZIP SHA-256: "+DATA.sha256;
}
function updateMode(){image.src="data:image/png;base64,"+
 (document.getElementById("mode").value==="confidence"?CONFIDENCE:DISTANCE)}
canvas.addEventListener("pointerdown",e=>{
 if(points.length>=4)return;
 const r=canvas.getBoundingClientRect();
 const x=Math.min(width-1,Math.max(0,Math.round((e.clientX-r.left)*width/r.width)));
 const y=Math.min(height-1,Math.max(0,Math.round((e.clientY-r.top)*height/r.height)));
 points.push([x,y]);draw();
});
document.getElementById("undo").onclick=()=>{points.pop();draw()};
document.getElementById("reset").onclick=()=>{points.length=0;draw()};
document.getElementById("mode").onchange=updateMode;
save.onclick=()=>{
 if(!valid(points))return;
 const obj={schema_version:1,sessions:[{sha256:DATA.sha256,
       source:"manual_depth_view",corners_px:points}]};
 const blob=new Blob([JSON.stringify(obj,null,2)+"\n"],{type:"application/json"});
 const a=document.createElement("a");
 const link=URL.createObjectURL(blob);
 a.href=link;a.download=DATA.zip_name.replace(/\.zip$/i,"")+"_roi_private.json";
 a.click();setTimeout(()=>URL.revokeObjectURL(link),1500);
};
updateMode();draw();
</script></body></html>
"""


def render(path):
    session=read_session(path)
    p1,p2,stats=preview_images(session)
    meta={"zip_name":Path(path).name,
          "width":session["width"],"height":session["height"],
          "sha256":sha256(path),
          "four_corners_independently_verified":False,
          "board_semantics_unproven":True,
          "physical_slope_certified":False,
          **stats}
    # JSON is HTML-safe and local; no interpolation into tag attributes.
    packed=json.dumps(meta,ensure_ascii=False).replace("<","\\u003c").replace(">","\\u003e").replace("&","\\u0026")
    out=(HTML_TEMPLATE
         .replace("__WIDTH__",str(session["width"]))
         .replace("__HEIGHT__",str(session["height"]))
         .replace("__METADATA__",packed)
         .replace("__DISTANCE_PNG__",base64.b64encode(p1).decode("ascii"))
         .replace("__CONFIDENCE_PNG__",base64.b64encode(p2).decode("ascii")))
    return out,meta


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("session",type=Path,help="A private v11.1 depth ZIP")
    p.add_argument("--output",type=Path,required=True,help="Private local .html")
    args=p.parse_args()
    if args.output.suffix.lower()!=".html":
        p.error("Output must end in .html")
    text,meta=render(args.session)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(text,encoding="utf-8")
    print(json.dumps({"status":"local_html_created","path":str(args.output),
                      "width":meta["width"],"height":meta["height"],
                      "annotation_truth":"unverified","image_embedded":True},ensure_ascii=False))


if __name__=="__main__":main()

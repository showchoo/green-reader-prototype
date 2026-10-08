"""v7.8: persist whether each Depth point came from Raw or Full ARCore Depth.

Keep the six-column historical depth_points CSV untouched, and write a
separate index-aligned source sidecar for success and failure records.
The actual surface fitting and scan acceptance rules remain unchanged.
"""
from pathlib import Path
root=Path("app/src/main/java/jp/example/greenreader")
models=root/"precision/PrecisionModels.kt"
collector=root/"precision/PrecisionDepthCollector.kt"
rec=root/"field/ScanFieldRecorder.kt"
main=root/"MainActivity.kt"
gradle=Path("app/build.gradle.kts")
m=models.read_text(encoding="utf8")
c=collector.read_text(encoding="utf8")
r=rec.read_text(encoding="utf8")
s=main.read_text(encoding="utf8")
g=gradle.read_text(encoding="utf8")

def one(src,old,new,label):
    n=src.count(old)
    if n!=1:raise SystemExit("v7.8 "+label+": expected 1 match, got "+str(n))
    return src.replace(old,new,1)

m=one(m,
'''    val confidence: Float,
    val frameTimestampNs: Long
)''',
'''    val confidence: Float,
    val frameTimestampNs: Long,
    val depthSource: String = "unknown"
)''',
"source model property")
old="samples += PrecisionDepthPoint(local[0], local[1], local[2], confs[i], timestamp)"
if c.count(old)!=2:raise SystemExit("v7.8 expected one raw and one full collector write")
c=c.replace(old,'samples += PrecisionDepthPoint(local[0], local[1], local[2], confs[i], timestamp, "raw")',1)
c=c.replace(old,'samples += PrecisionDepthPoint(local[0], local[1], local[2], confs[i], timestamp, "full")',1)

r=one(r,
'''        writeDownload(context, rel, "precision_depth_points.csv", "text/csv") { out ->
            writePrecisionPoints(out, precisionPoints)
        }
        writeDownload(context, rel, "precision_diagnostics.txt"''',
'''        writeDownload(context, rel, "precision_depth_points.csv", "text/csv") { out ->
            writePrecisionPoints(out, precisionPoints)
        }
        writeDownload(context, rel, "precision_depth_sources.csv", "text/csv") { out ->
            writePrecisionSources(out, precisionPoints)
        }
        writeDownload(context, rel, "precision_diagnostics.txt"''',
"modern record source sidecar")
r=one(r,
'''        File(dir, "precision_depth_points.csv").outputStream().use { out ->
            writePrecisionPoints(out, precisionPoints)
        }
        File(dir, "precision_diagnostics.txt")''',
'''        File(dir, "precision_depth_points.csv").outputStream().use { out ->
            writePrecisionPoints(out, precisionPoints)
        }
        File(dir, "precision_depth_sources.csv").outputStream().use { out ->
            writePrecisionSources(out, precisionPoints)
        }
        File(dir, "precision_diagnostics.txt")''',
"legacy record source sidecar")

anchor='''    private fun writePrecisionPoints(
        out: java.io.OutputStream,''';
helper=r'''    private fun writePrecisionSources(
        out: java.io.OutputStream,
        points: List<PrecisionDepthPoint>
    ) {
        out.bufferedWriter().use { w ->
            w.write("index,frame_timestamp_ns,depth_source\n")
            points.forEachIndexed { index, point ->
                w.write(index.toString() + "," + point.frameTimestampNs + "," +
                    point.depthSource + "\n")
            }
        }
    }

'''
r=one(r,anchor,helper+anchor,"source file writer")
# Preserve old CSV header byte-for-byte for offline replay compatibility.
assert 'w.write("index,x_m,y_m,z_m,confidence,frame_timestamp_ns\\n")' in r
assert "val depthSource: String = \\"unknown\\"" in m
assert 'depthSource' in r

if "Precision 7.7" not in s:raise SystemExit("v7.7 must precede v7.8")
s=s.replace("Precision 7.7","Precision 7.8")
g=one(g,'versionName = "7.7"','versionName = "7.8"',"versionName")
g=one(g,'versionCode = 770','versionCode = 780',"versionCode")
models.write_text(m,encoding="utf8")
collector.write_text(c,encoding="utf8")
rec.write_text(r,encoding="utf8")
main.write_text(s,encoding="utf8")
gradle.write_text(g,encoding="utf8")
print("Applied Precision v7.8 Raw/Full Depth origin sidecar")

from pathlib import Path

p=Path("app/src/main/java/jp/example/greenreader/MainActivity.kt")
s=p.read_text(encoding="utf-8")

start=s.find("    private fun markAt(x: Float, y: Float) {")
end=s.find("\n    private fun ", start+20)
if start < 0 or end < 0:
    raise SystemExit("v5.4 markAt boundaries missing")

fn=s[start:end]

old='''        if (p == null && mode == 1) {
            p = try {
                ballPointFromNeighborDepth(f, x, y)
            } catch (_: Throwable) {
                null
            }
        }
'''
new='''        if (p == null && (mode == 1 || mode == 2)) {
            p = try {
                ballPointFromNeighborDepth(f, x, y)
            } catch (_: Throwable) {
                null
            }
        }
'''
if old not in fn:
    raise SystemExit("v5.4 borrowed-depth block missing")
fn=fn.replace(old,new,1)

old2='''        status.text = if (mode == 1) {
            "ボール位置を取得できませんでした。もう一度タップしてください"
        } else {
            "カップ位置を取得できませんでした。もう一度タップしてください"
        }
'''
new2='''        status.text = if (mode == 1) {
            "ボール位置を取得できませんでした。もう一度タップしてください"
        } else {
            "カップ位置を取得できませんでした。もう一度タップしてください"
        }
        if (mode == 2) {
            precisionLastDiagnostic = "MARK tap-unresolved target=cup"
            showPrecisionFailureDialog("カップ位置を取得できませんでした。もう一度カップをタップしてください")
        }
'''
if old2 not in fn:
    raise SystemExit("v5.4 unresolved-status block missing")
fn=fn.replace(old2,new2,1)

s=s[:start]+fn+s[end:]
p.write_text(s,encoding="utf-8")
print("Applied Precision v5.4 cup neighbor-depth fallback + explicit failure dialog")

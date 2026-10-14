"""v10.2 SC-52A diagnostic-only Raw/Full confidence and local height comparison.

Raw-confidence bins include in-range pixels BEFORE the >=128 trust filter;
this distinguishes genuine sensor sparsity from software rejection.
Raw/Full overlap uses source-tagged world/local points; neither source
is assumed to be ground truth. It does NOT alter slope or acceptance.
"""
from pathlib import Path

root=Path("app/src/main/java/jp/example/greenreader")
collector=root/"precision/PrecisionDepthCollector.kt"
main=root/"MainActivity.kt"
gradle=Path("app/build.gradle.kts")
audit=root/"precision/PrecisionSourceOverlapAudit.kt"
tests=Path("app/src/test/java/jp/example/greenreader/precision/PrecisionSourceOverlapAuditTest.kt")
c=collector.read_text(encoding="utf8")
m=main.read_text(encoding="utf8")
g=gradle.read_text(encoding="utf8")

def one(s,old,new,label):
    count=s.count(old)
    if count != 1:
        raise RuntimeError(f"v10.2 {label}: expected once, found {count}")
    return s.replace(old,new,1)

c=one(c,
'''    private var acquiredFullPointCount = 0L
''',
'''    private var acquiredFullPointCount = 0L
    // Count nonzero/in-range Raw pixels by unsigned confidence byte 0..255.
    // Sampling is performed before the confidence threshold discards a pixel.
    private val rawConfidenceHistogram = LongArray(8)
    private var fullProjectionRejectedPixels = 0L
''',"diagnostic counters")
c=one(c,
'''        acquiredFullPointCount = 0L
''',
'''        acquiredFullPointCount = 0L
        rawConfidenceHistogram.fill(0L)
        fullProjectionRejectedPixels = 0L
''',"counter reset")
c=one(c,
'''        val acquiredFullPointCount: Long = 0L,
''',
'''        val acquiredFullPointCount: Long = 0L,
        val rawConfidenceBins: List<Long> = List(8) { 0L },
        val fullProjectionRejectedPixels: Long = 0L,
''',"snapshot fields")
c=one(c,
'''                    acquiredFullPointCount = items.sumOf { it.acquiredFullPointCount },
''',
'''                    acquiredFullPointCount = items.sumOf { it.acquiredFullPointCount },
                    rawConfidenceBins = (0 until 8).map { index ->
                        items.sumOf { it.rawConfidenceBins[index] }
                    },
                    fullProjectionRejectedPixels =
                        items.sumOf { it.fullProjectionRejectedPixels },
''',"aggregate bins")
c=one(c,
'''        acquiredFullPointCount = acquiredFullPointCount,
''',
'''        acquiredFullPointCount = acquiredFullPointCount,
        rawConfidenceBins = rawConfidenceHistogram.toList(),
        fullProjectionRejectedPixels = fullProjectionRejectedPixels,
''',"snapshot values")
c=one(c,
'''        " acquiredFullPoints=" + acquiredFullPointCount +
''',
'''        " acquiredFullPoints=" + acquiredFullPointCount +
        " rawConfBins32=" + rawConfidenceHistogram.joinToString(",") +
        " fullProjectionRejected=" + fullProjectionRejectedPixels +
''',"collector summary")
c=one(c,
'''                    val conf = cb.get(ci).toInt() and 0xff
                    if (conf < confidenceThreshold) continue''',
'''                    val conf = cb.get(ci).toInt() and 0xff
                    // This is an observation, not a replacement for the
                    // existing confidence gate. Include zero-confidence pixels.
                    if (isRaw) rawConfidenceHistogram[conf ushr 5]++
                    if (conf < confidenceThreshold) continue''',"pre-gate histogram")
c=one(c,
'''                if (!u.isFinite() || !v.isFinite()) continue
                if (u < 0f || v < 0f || u >= imageDims[0].toFloat() || v >= imageDims[1].toFloat()) continue''',
'''                if (!u.isFinite() || !v.isFinite()) {
                    fullProjectionRejectedPixels++
                    continue
                }
                if (u < 0f || v < 0f ||
                    u >= imageDims[0].toFloat() || v >= imageDims[1].toFloat()) {
                    fullProjectionRejectedPixels++
                    continue
                }''',"Full projection invalid count")
c=one(c,
'''    @Synchronized fun framePoseDiagnostics(): String =
        framePoseTelemetry.toDiagnosticText()''',
'''    @Synchronized fun framePoseDiagnostics(): String =
        framePoseTelemetry.toDiagnosticText() + "\\n" +
            PrecisionSourceOverlapAudit.diagnostic(samples)''',"per-window source overlap saved in existing collector_diagnostics")
m=one(m,
'''            " confPass=" + total.confidencePassedPixels +
''',
'''            " confPass=" + total.confidencePassedPixels +
            " rawConfBins32=" + total.rawConfidenceBins.joinToString(",") +
            " fullProjectionRejected=" + total.fullProjectionRejectedPixels +
''',"all-window confidence telemetry")
if m.count("Precision 10.1") < 2:
    raise RuntimeError("v10.2 expected app version Precision 10.1")
m=m.replace("Precision 10.1","Precision 10.2")
g=one(g,'versionName = "10.1"','versionName = "10.2"',"version name")
g=one(g,'versionCode = 1010','versionCode = 1020',"version code")

audit.write_text(r'''package jp.example.greenreader.precision

import java.util.Locale
import kotlin.math.abs
import kotlin.math.floor

/**
 * Observation-only diagnostic: compare independent Raw and Full height
 * estimates at approximately the same 12-cm horizontal (x,z) cell.
 * Height differences do NOT establish which sensor is correct.
 * Does not affect ground classification, scan success or putt guidance.
 */
object PrecisionSourceOverlapAudit {
    private const val CELL_M = 0.12f
    private const val MIN_PER_SOURCE = 3

    data class Summary(
        val matchedCells: Int,
        val rawCells: Int,
        val fullCells: Int,
        val medianSignedHeightDeltaM: Float,
        val medianAbsHeightDeltaM: Float,
        val p90AbsHeightDeltaM: Float
    )

    private class Bucket {
        val raw = ArrayList<Float>()
        val full = ArrayList<Float>()
    }

    private fun median(values: List<Float>): Float {
        val s = values.sorted()
        return if (s.size % 2 == 0)
            (s[s.size / 2 - 1] + s[s.size / 2]) * 0.5f
        else s[s.size / 2]
    }

    fun evaluate(points: List<PrecisionDepthPoint>): Summary {
        val buckets = HashMap<Long, Bucket>()
        // Bounded diagnostic subsampling: do not slow down AR collection
        // or change any of the full-resolution production point cloud.
        val stride = (points.size / 45000).coerceAtLeast(1)
        for (i in points.indices step stride) {
            val p = points[i]
            if (!p.x.isFinite() || !p.y.isFinite() || !p.z.isFinite()) continue
            if (abs(p.x) > 8f || abs(p.z) > 8f) continue
            if (p.depthSource != "raw" && p.depthSource != "full") continue
            val ix = floor(p.x / CELL_M).toInt()
            val iz = floor(p.z / CELL_M).toInt()
            val key = (ix.toLong() shl 32) xor (iz.toLong() and 0xffffffffL)
            val b = buckets.getOrPut(key) { Bucket() }
            if (p.depthSource == "raw") b.raw.add(p.y) else b.full.add(p.y)
        }
        val signed = ArrayList<Float>()
        val absolute = ArrayList<Float>()
        var rawCells = 0
        var fullCells = 0
        for (b in buckets.values) {
            if (b.raw.size >= MIN_PER_SOURCE) rawCells++
            if (b.full.size >= MIN_PER_SOURCE) fullCells++
            if (b.raw.size < MIN_PER_SOURCE || b.full.size < MIN_PER_SOURCE) continue
            val difference = median(b.raw) - median(b.full)
            signed.add(difference)
            absolute.add(abs(difference))
        }
        if (signed.isEmpty()) return Summary(0, rawCells, fullCells,
            Float.NaN, Float.NaN, Float.NaN)
        absolute.sort()
        val p90 = absolute[((absolute.size - 1) * 0.90).toInt()]
        return Summary(signed.size, rawCells, fullCells,
            median(signed), median(absolute), p90)
    }

    fun diagnostic(points: List<PrecisionDepthPoint>): String {
        val s = evaluate(points)
        val fmt: (Float) -> String = { value ->
            if (value.isFinite()) String.format(Locale.US, "%.1f", value * 100f)
            else "NA"
        }
        return "DEPTH_SOURCE_OVERLAP_V1 cellCm=12 matched=" + s.matchedCells +
            " rawCells=" + s.rawCells + " fullCells=" + s.fullCells +
            " medianSignedRawMinusFullCm=" + fmt(s.medianSignedHeightDeltaM) +
            " medianAbsCm=" + fmt(s.medianAbsHeightDeltaM) +
            " p90AbsCm=" + fmt(s.p90AbsHeightDeltaM) +
            " diagnosticOnly=true"
    }
}
''', encoding="utf8")

tests.write_text(r'''package jp.example.greenreader.precision

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class PrecisionSourceOverlapAuditTest {
    private fun point(x: Float, y: Float, source: String) =
        PrecisionDepthPoint(x, y, 0.02f, 0.9f, 10L, source)

    @Test fun matchedHeightOffsetReportedWithoutClaimingGroundTruth() {
        val points = (0 until 6).flatMap {
            listOf(point(0.03f, 0.02f, "raw"), point(0.03f, -0.03f, "full"))
        }
        val s = PrecisionSourceOverlapAudit.evaluate(points)
        assertEquals(1, s.matchedCells)
        assertEquals(0.05f, s.medianSignedHeightDeltaM, 0.001f)
        assertEquals(0.05f, s.medianAbsHeightDeltaM, 0.001f)
        assertTrue(PrecisionSourceOverlapAudit.diagnostic(points).contains("matched=1"))
    }
    @Test fun noCommonCellsNeverFabricateAgreement() {
        val onlyRaw = List(10) { point(0.04f, 0f, "raw") }
        val s = PrecisionSourceOverlapAudit.evaluate(onlyRaw)
        assertEquals(0, s.matchedCells)
        assertTrue(s.medianSignedHeightDeltaM.isNaN())
        assertTrue(PrecisionSourceOverlapAudit.diagnostic(onlyRaw)
            .contains("medianAbsCm=NA"))
    }
    @Test fun nonFiniteAndUnrecognizedSamplesCannotCreatePairs() {
        val pts = listOf(point(Float.NaN, 0f, "raw"),
            point(0f, 1f, "unknown"), point(0f, 0f, "full"))
        assertEquals(0, PrecisionSourceOverlapAudit.evaluate(pts).matchedCells)
        assertFalse(PrecisionSourceOverlapAudit.diagnostic(pts).contains("NaNCm"))
    }
}
''', encoding="utf8")

# Production acceptance, original data exports, and directional guard untouched.
assert 'PrecisionAnchoredGroundSelector.select(' in (root/"precision/PrecisionSurfaceBuilder.kt").read_text()
assert 'PrecisionSlopeAnalyzer.analyze(' in m
assert 'PrecisionDepthSourceAudit.analyze(' in m
assert 'PrecisionMarkerDepthHeightAudit.evaluate(' in m
assert 'SPARSE_RAW_FULL_UNVERIFIED=' in m
assert 'DEPTH_FRESHNESS staleRaw=' in m
assert 'DriveBackupScheduler.onScanSaved(context)' in (root/"field/ScanFieldRecorder.kt").read_text()
assert 'button("次のパット")' in m and 'button("結果入力")' in m

collector.write_text(c,encoding="utf8")
main.write_text(m,encoding="utf8")
gradle.write_text(g,encoding="utf8")
print("v10.2: confidence histogram + source-local geometry audit, diagnostic-only")

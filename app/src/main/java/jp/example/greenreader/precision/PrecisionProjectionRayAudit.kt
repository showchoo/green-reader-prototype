package jp.example.greenreader.precision

import java.util.Locale
import kotlin.math.abs

/**
 * Observational comparison of two pixel-to-camera-ray reconstruction paths:
 *  1) Depth pixel via scaled GPU texture intrinsics (production Raw path).
 *  2) Texture-normalized -> CPU IMAGE_PIXELS, image intrinsics (Full path).
 *
 * Both rays share a depth value, frame camera pose and source pixel.
 * A difference is NOT proof of which path represents physical ground truth.
 */
object PrecisionProjectionRayAudit {
    private const val MAX_PROBES_PER_SOURCE = 8192

    data class Probe(
        val verticalDeltaCm: Float,
        val horizontalDeltaCm: Float,
        val depthM: Float,
        val cameraPitchDeg: Float
    )

    data class Summary(
        val count: Int,
        val invalidMappedPixels: Int,
        val medianSignedVerticalCm: Float,
        val medianAbsVerticalCm: Float,
        val p90AbsVerticalCm: Float,
        val medianHorizontalCm: Float,
        val medianDepthM: Float,
        val minCameraPitchDeg: Float,
        val maxCameraPitchDeg: Float
    )

    private fun median(input: List<Float>): Float {
        if (input.isEmpty()) return Float.NaN
        val s = input.sorted()
        return if (s.size % 2 == 0)
            (s[s.size / 2 - 1] + s[s.size / 2]) * 0.5f
        else s[s.size / 2]
    }

    private fun percentile90Absolute(input: List<Float>): Float {
        if (input.isEmpty()) return Float.NaN
        val sorted = input.map { abs(it) }.sorted()
        val index = (kotlin.math.ceil(0.9 * sorted.size).toInt() - 1)
            .coerceIn(0,sorted.lastIndex)
        return sorted[index]
    }

    class Buffer {
        private val raw = ArrayList<Probe>()
        private val full = ArrayList<Probe>()
        private var invalidRaw = 0
        private var invalidFull = 0
        private var errors = 0

        fun clear() {
            raw.clear()
            full.clear()
            invalidRaw = 0
            invalidFull = 0
            errors = 0
        }

        fun record(source: String, probe: Probe) {
            if (source != "raw" && source != "full") return
            if (!probe.verticalDeltaCm.isFinite() ||
                !probe.horizontalDeltaCm.isFinite() ||
                !probe.depthM.isFinite() ||
                !probe.cameraPitchDeg.isFinite() ||
                probe.depthM <= 0f ||
                probe.horizontalDeltaCm < 0f) return
            val points = if (source == "raw") raw else full
            if (points.size < MAX_PROBES_PER_SOURCE) points.add(probe)
        }

        fun invalidMapping(source: String) {
            if (source == "raw") invalidRaw++
            if (source == "full") invalidFull++
        }

        fun error() { errors++ }

        fun summary(source: String): Summary {
            require(source == "raw" || source == "full")
            val probes = if (source == "raw") raw else full
            val invalid = if (source == "raw") invalidRaw else invalidFull
            if (probes.isEmpty()) return Summary(
                0,invalid,Float.NaN,Float.NaN,Float.NaN,
                Float.NaN,Float.NaN,Float.NaN,Float.NaN
            )
            val delta = probes.map { it.verticalDeltaCm }
            val pitches = probes.map { it.cameraPitchDeg }
            return Summary(
                count = probes.size,
                invalidMappedPixels = invalid,
                medianSignedVerticalCm = median(delta),
                medianAbsVerticalCm = median(delta.map { abs(it) }),
                p90AbsVerticalCm = percentile90Absolute(delta),
                medianHorizontalCm = median(probes.map { it.horizontalDeltaCm }),
                medianDepthM = median(probes.map { it.depthM }),
                minCameraPitchDeg = pitches.minOrNull() ?: Float.NaN,
                maxCameraPitchDeg = pitches.maxOrNull() ?: Float.NaN
            )
        }

        fun diagnostic(): String {
            fun fmt(x: Float): String =
                if (x.isFinite()) String.format(Locale.US,"%.2f",x) else "NA"
            fun section(name: String, s: Summary): String =
                " "+name+"N="+s.count+
                " "+name+"InvalidMap="+s.invalidMappedPixels+
                " "+name+"SignedVerticalCm="+fmt(s.medianSignedVerticalCm)+
                " "+name+"AbsVerticalCm="+fmt(s.medianAbsVerticalCm)+
                " "+name+"P90VerticalCm="+fmt(s.p90AbsVerticalCm)+
                " "+name+"HorizontalCm="+fmt(s.medianHorizontalCm)+
                " "+name+"DepthM="+fmt(s.medianDepthM)+
                " "+name+"MinPitchDeg="+fmt(s.minCameraPitchDeg)+
                " "+name+"MaxPitchDeg="+fmt(s.maxCameraPitchDeg)
            return "PROJECTION_RAY_AUDIT_V1"+
                section("raw",summary("raw"))+
                section("full",summary("full"))+
                " transformErrors="+errors+
                " diagnosticOnly=true groundTruth=false"
        }
    }
}

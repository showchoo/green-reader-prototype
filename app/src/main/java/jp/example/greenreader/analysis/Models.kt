package jp.example.greenreader.analysis

data class Vec3(val x: Float, val y: Float, val z: Float)

data class SlopeSegment(
    val startMeters: Float,
    val endMeters: Float,
    val longitudinalPercent: Float,
    val crossPercent: Float,
    val elevationMeters: Float,
    val sampleCount: Int
)

data class SlopeReport(
    val distanceMeters: Float,
    val segments: List<SlopeSegment>,
    val overallLongitudinalPercent: Float,
    val overallCrossPercent: Float,
    val pointCount: Int
)

data class GrainReport(
    val axisDegrees: Float,
    val confidence: Float,
    val note: String
)

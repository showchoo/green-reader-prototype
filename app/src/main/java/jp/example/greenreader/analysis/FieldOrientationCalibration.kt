package jp.example.greenreader.analysis

object FieldOrientationCalibration {
    fun correctCrossSign(report: SlopeReport): SlopeReport = report.copy(
        segments = report.segments.map { it.copy(crossPercent = -it.crossPercent) },
        overallCrossPercent = -report.overallCrossPercent
    )
}

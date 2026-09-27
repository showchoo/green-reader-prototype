package jp.example.greenreader.precision

data class PrecisionDepthPoint(
    val x: Float,
    val y: Float,
    val z: Float,
    val confidence: Float,
    val frameTimestampNs: Long
)

data class PrecisionSurfaceCell(
    val x: Float,
    val z: Float,
    val height: Float,
    val confidence: Float,
    val observations: Int,
    val madMeters: Float
)

data class PrecisionSurfaceModel(
    val cells: List<PrecisionSurfaceCell>,
    val voxelSizeMeters: Float,
    val sourcePointCount: Int,
    val uniqueFrames: Int,
    val candidateCellCount: Int = cells.size,
    val rejectedCellCount: Int = 0,
    val groundCellCount: Int = cells.size
)

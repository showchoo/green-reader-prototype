package jp.example.greenreader.analysis

import kotlin.math.abs

/**
 * Converts SlopeAnalyzer's arbitrary +t cross axis into the captured screen's
 * canonical "right side of the ball -> cup line" axis.
 *
 * Screen Y grows downward. For a unit ball->cup screen vector (ux, uy), the
 * right-hand normal is (-uy, ux). The projected +t vector may point to either
 * side depending on the AR/world frame, so only its sign against that right
 * normal is needed. Rendering can then use one stable right-normal basis.
 */
object ScreenSideMapper {
    fun projectedCrossToScreenRightSign(
        lineUx: Float,
        lineUy: Float,
        projectedCrossX: Float,
        projectedCrossY: Float
    ): Float? {
        val rightX = -lineUy
        val rightY = lineUx
        val dot = projectedCrossX * rightX + projectedCrossY * rightY
        if (abs(dot) < 0.08f) return null
        return if (dot > 0f) 1f else -1f
    }
}

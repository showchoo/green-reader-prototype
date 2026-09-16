package jp.example.greenreader.analysis

/**
 * Final field calibration for the captured-image overlay.
 *
 * ScreenSideMapper establishes the geometric relationship between AR +t and the
 * visible right side of the ball->cup line. FCNT M07 field tests show that the
 * measured height-gradient convention is the opposite of the overlay's downhill /
 * uphill convention after that geometric mapping. Apply that correction exactly
 * once, at the final screen boundary, so depth fitting and saved raw measurements
 * remain untouched.
 */
object DisplayDirectionCalibration {
    fun renderCrossPercent(rawCrossPercent: Float, geometricCrossToRightSign: Float): Float =
        -rawCrossPercent * geometricCrossToRightSign

    fun renderAimOffsetCm(rawAimOffsetCm: Float, geometricCrossToRightSign: Float): Float =
        -rawAimOffsetCm * geometricCrossToRightSign
}

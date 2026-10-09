package jp.example.greenreader.precision

/**
 * Failures stay failures: classify observed acquisition evidence to explain
 * what a field tester should change, rather than repeatedly saying only
 * "the measurement was unstable".
 *
 * Never interpolates a missing slope or bypasses surface-fit validation.
 */
object PrecisionScanFailureAdvisor {
    enum class Reason {
        NO_QUALITY_EVIDENCE,
        FULL_DEPTH_WITHOUT_GROUND,
        RAW_DEPTH_UNAVAILABLE,
        INSUFFICIENT_GROUND_CELLS,
        MOSTLY_FULL_DEPTH_WITH_NO_VALID_FITS,
        NO_VALID_LOCAL_FITS,
        TOO_LITTLE_PARALLAX,
        NOT_ENOUGH_VALID_WINDOWS
    }

    data class Advice(val reason: Reason, val guidance: String) {
        fun message(): String =
            "測定を確定できません（" + reason.name + "）。" + guidance

        fun diagnostic(): String =
            "FAILURE_ADVICE reason=" + reason.name + " guidance=" + guidance
    }

    fun evaluate(q: PrecisionScanQuality?): Advice {
        if (q == null) return Advice(
            Reason.NO_QUALITY_EVIDENCE,
            "解析用データが不足しています。AR追跡とボール・カップ位置を確認して再スキャンしてください"
        )
        if (q.groundCellCount < 80 && q.rawAcceptedFrames == 0 &&
            q.fullAcceptedFrames > 0
        ) return Advice(
            Reason.FULL_DEPTH_WITHOUT_GROUND,
            "Raw Depthが取得できず、床面の有効範囲も不足しています。壁・靴・家具を画面から外し、床全体を映して端末を左右20〜30cmゆっくり動かしてください"
        )
        if (q.rawAcceptedFrames == 0 && q.fullAcceptedFrames > 0) return Advice(
            Reason.RAW_DEPTH_UNAVAILABLE,
            "Raw Depthが取得できません。床面の模様が見える距離で左右20〜30cm動かして再測定してください"
        )
        if (q.groundCellCount < 80) return Advice(
            Reason.INSUFFICIENT_GROUND_CELLS,
            "床面として採用できた範囲が足りません。ボールとカップの間を中央に映し、壁・家具・足を避けて再測定してください"
        )
        if (q.validWindowCount == 0 && q.rawAcceptedFrames > 0 &&
            q.fullAcceptedFrames > q.rawAcceptedFrames * 3
        ) return Advice(
            Reason.MOSTLY_FULL_DEPTH_WITH_NO_VALID_FITS,
            "Full Depth主体で地面傾斜が整合しません。端末を急に回転せず、床全体を映して左右に移動してください"
        )
        if (q.validWindowCount == 0) return Advice(
            Reason.NO_VALID_LOCAL_FITS,
            "Depth点はありますが、床の局所傾斜が成立していません。ボール・カップ位置と撮影範囲を見直し、床面を中心に再測定してください"
        )
        if (!q.cameraTravelMeters.isFinite() || q.cameraTravelMeters < .10f)
            return Advice(
                Reason.TOO_LITTLE_PARALLAX,
                "視点移動が少なく立体形状の確認が不十分です。床面を映したまま左右に20〜30cmゆっくり動かしてください"
            )
        return Advice(
            Reason.NOT_ENOUGH_VALID_WINDOWS,
            "各測定区間が一致しません。ボールとカップを同じ位置に保ち、一定の速さで床面を撮影してください"
        )
    }
}

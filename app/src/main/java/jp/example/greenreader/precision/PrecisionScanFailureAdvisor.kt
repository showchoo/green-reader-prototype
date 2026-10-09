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
        NO_DEPTH_IMAGES,
        NO_USABLE_DEPTH,
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

    fun evaluate(
        q: PrecisionScanQuality?,
        depth: PrecisionDepthStallPolicy.Decision? = null
    ): Advice {
        if (depth?.state == PrecisionDepthStallPolicy.State.NO_DEPTH_IMAGES ||
            (q != null && q.rawAcceptedFrames == 0 &&
                q.fullAcceptedFrames == 0 && q.uniqueDepthFrames == 0)) {
            return Advice(
                Reason.NO_DEPTH_IMAGES,
                "ARの追跡が正常でもRaw/Full Depth画像を取得できません。\n" +
                "MENU→AR・Depth再起動でセッションを作り直してください。" +
                "再起動後はボール・カップを再指定してください"
            )
        }
        if (depth?.state == PrecisionDepthStallPolicy.State.NO_USABLE_DEPTH) {
            return Advice(
                Reason.NO_USABLE_DEPTH,
                "Depth画像は届いていますが、有効点が取得できません。" +
                "MENU→AR・Depth再起動を試し、改善しなければ床面の特徴が見える場所で再測定してください"
            )
        }
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

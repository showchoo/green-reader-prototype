package jp.example.greenreader.precision

import org.junit.Assert.assertEquals
import org.junit.Test

class PrecisionTemporalQualityGateTest {
    @Test fun unverifiedScoreIsCappedBelowHighConfidence() {
        assertEquals(84, PrecisionTemporalQualityGate.score(100, false))
        assertEquals(84, PrecisionTemporalQualityGate.score(93, false))
        assertEquals(80, PrecisionTemporalQualityGate.score(80, false))
    }

    @Test fun verifiedScoreIsNotChanged() {
        assertEquals(93, PrecisionTemporalQualityGate.score(93, true))
        assertEquals(0, PrecisionTemporalQualityGate.score(0, true))
    }

    @Test fun boundsAreRespected() {
        assertEquals(0, PrecisionTemporalQualityGate.score(-5, false))
        assertEquals(100, PrecisionTemporalQualityGate.score(300, true))
        assertEquals(84, PrecisionTemporalQualityGate.score(300, false))
    }
}

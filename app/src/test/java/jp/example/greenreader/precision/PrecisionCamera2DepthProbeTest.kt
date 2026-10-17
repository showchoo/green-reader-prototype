package jp.example.greenreader.precision

import org.junit.Assert.assertEquals
import org.junit.Test

class PrecisionCamera2DepthProbeTest {
    @Test fun publiclyAdvertisedDepth16IsCandidateNotAccuracyProof() {
        assertEquals("PUBLIC_CAMERA2_DEPTH16",
            PrecisionCamera2DepthProbe.classify(4,4,1,0))
        assertEquals("PUBLIC_CAMERA2_DEPTH16",
            PrecisionCamera2DepthProbe.classify(4,3,1,1))
    }

    @Test fun knownCompleteNoDepthIsNotExposed() {
        assertEquals("NO_PUBLIC_CAMERA2_DEPTH16",
            PrecisionCamera2DepthProbe.classify(3,3,0,0))
    }

    @Test fun inaccessibleHiddenCameraDoesNotClaimDefinitiveNegative() {
        assertEquals("INDETERMINATE",
            PrecisionCamera2DepthProbe.classify(3,2,0,1))
    }

    @Test fun missingCameraEnumerationDoesNotClaimNegative() {
        assertEquals("INDETERMINATE",
            PrecisionCamera2DepthProbe.classify(0,0,0,1))
    }
}

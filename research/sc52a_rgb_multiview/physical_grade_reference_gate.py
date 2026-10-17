"""Validate independent measured rise/run before any precise grade claim.

Never replace missing physical measurements with cardboard length or
estimated shim thickness. Reference uncertainty is worst-case bounded,
not a probabilistic sensor accuracy estimate.
"""
import math


def physical_grade_reference(
    rise_mm, run_mm, rise_tolerance_mm, run_tolerance_mm,
    rise_measured, run_measured, rigid_target, initially_level_verified
):
    flags=(rise_measured,run_measured,rigid_target,initially_level_verified)
    if not all(isinstance(v,bool) for v in flags):
        raise ValueError("Require explicit booleans for independent reference")
    if not all(flags):
        return {"reference_valid":False,
                "reason":"Unmeasured rise/run, nonrigid target, or initial level unverified",
                "reference_grade_pct":None,
                "accuracy_certified":False}
    values=(rise_mm,run_mm,rise_tolerance_mm,run_tolerance_mm)
    if not all(isinstance(v,(int,float)) and math.isfinite(v) for v in values):
        raise ValueError("All measured lengths and tolerances must be finite")
    if not (0<=rise_mm<=150 and 300<=run_mm<=3000 and
            0<=rise_tolerance_mm<=rise_mm and
            0<=run_tolerance_mm<run_mm):
        raise ValueError("Physical dimensions outside calibration bounds")
    lower=100*(rise_mm-rise_tolerance_mm)/(run_mm+run_tolerance_mm)
    upper=100*(rise_mm+rise_tolerance_mm)/(run_mm-run_tolerance_mm)
    nominal=100*rise_mm/run_mm
    max_error=max(nominal-lower,upper-nominal)
    return {"reference_valid":max_error<=.15,
            "reference_grade_pct":round(nominal,5),
            "reference_grade_low_pct":round(lower,5),
            "reference_grade_high_pct":round(upper,5),
            "reference_max_deviation_pp":round(max_error,5),
            "reference_uncertainty_budget_pp":.15,
            "accuracy_certified":False}

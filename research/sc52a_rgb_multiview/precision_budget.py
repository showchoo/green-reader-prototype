"""Illustrative first-order stereo and gravity budget, not device measurements.

Ideal rectified calibrated stereo: depth sigma ~ Z^2 * disparity_sigma/(f*B).
Does NOT model camera pose error, floor segmentation or correlated bias.
"""
import math


def axial_error_mm(distance_m, focal_pixels, baseline_m, disparity_sigma_px):
    args=(distance_m,focal_pixels,baseline_m,disparity_sigma_px)
    if any(not math.isfinite(v) for v in args):
        raise ValueError("values must be finite")
    if distance_m<=0 or focal_pixels<=0 or baseline_m<=0 or disparity_sigma_px<0:
        raise ValueError("invalid physical geometry")
    return 1000*distance_m**2*disparity_sigma_px/(focal_pixels*baseline_m)


def gravity_grade_error_pp(tilt_error_degrees):
    if not math.isfinite(tilt_error_degrees):
        raise ValueError("angle must be finite")
    return abs(100*math.tan(math.radians(tilt_error_degrees)))


def illustrative_budget():
    # These values are ASSUMPTIONS. Neither S20+ image fx nor feature σ
    # has been independently calibrated by the research.
    return {
        "calibrated_device_data":False,
        "hypothetical_fx_px":1000,
        "hypothetical_translation_baseline_m":0.25,
        "first_order_axial_uncertainty_mm":[
            {"distance_m":z,
             "disparity_sigma_0_25px":axial_error_mm(z,1000,.25,.25),
             "disparity_sigma_1px":axial_error_mm(z,1000,.25,1.0)}
            for z in (1,2,3)],
        "gravity_angle_error":[
            {"degrees":d,"grade_error_pp":round(gravity_grade_error_pp(d),3)}
            for d in (.1,.3,1.0)],
        "max_gravity_error_deg_for_0_5pp_independent_budget":
            round(math.degrees(math.atan(.005)),3),
        "limitation":"Not directly an end-to-end slope error; real errors can be systematic and correlated."
    }


if __name__=="__main__":
    import json
    print(json.dumps(illustrative_budget(),indent=2))

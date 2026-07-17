"""Pure helpers for non-destructive cat-sound loudness normalization."""

from __future__ import annotations

import math


def db_to_linear(db: float) -> float:
    """Convert an amplitude gain in decibels to a linear multiplier."""

    if not math.isfinite(db):
        raise ValueError("gain must be finite")
    return 10.0 ** (db / 20.0)


def peak_limited_gain_db(
    track_gain_db: float,
    sample_peak: float,
    master_linear: float,
    *,
    peak_ceiling_dbfs: float = -1.0,
) -> float:
    """Return the requested gain, reduced only enough to respect the peak ceiling.

    ReplayGain normalizes perceived track loudness, but some source recordings have
    isolated peaks that would clip after gain. The common master is part of the
    calculation so quiet sources can retain their full correction without rewriting
    the original recording.
    """

    if not math.isfinite(track_gain_db):
        raise ValueError("track gain must be finite")
    if not math.isfinite(sample_peak) or not 0.0 < sample_peak <= 1.0:
        raise ValueError("sample peak must be finite and in (0, 1]")
    if not math.isfinite(master_linear) or master_linear <= 0.0:
        raise ValueError("master must be finite and positive")
    if not math.isfinite(peak_ceiling_dbfs) or peak_ceiling_dbfs > 0.0:
        raise ValueError("peak ceiling must be finite and no greater than 0 dBFS")

    ceiling_linear = db_to_linear(peak_ceiling_dbfs)
    safe_gain_db = 20.0 * math.log10(ceiling_linear / (master_linear * sample_peak))
    return min(track_gain_db, safe_gain_db)


def playback_multiplier(
    track_gain_db: float,
    sample_peak: float,
    master_linear: float,
    *,
    peak_ceiling_dbfs: float = -1.0,
) -> tuple[float, float, float]:
    """Return ``(multiplier, applied_gain_db, predicted_output_peak)``."""

    applied_gain_db = peak_limited_gain_db(
        track_gain_db,
        sample_peak,
        master_linear,
        peak_ceiling_dbfs=peak_ceiling_dbfs,
    )
    multiplier = master_linear * db_to_linear(applied_gain_db)
    return multiplier, applied_gain_db, sample_peak * multiplier

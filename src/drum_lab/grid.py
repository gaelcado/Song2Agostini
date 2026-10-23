"""Audio grid postprocessing; no drum pitches or reference information."""
import copy
import numpy as np


def clean_model_grid(grid):
    """Merge implausibly close tracker peaks, retaining one observed peak.

    A 0.35 median-quarter refractory window is deliberately below an eighth
    note. Selection minimizes departure from adjacent cluster timing; it never
    moves a beat to a drum onset. Bar phase remains the model's prediction.
    """
    result = copy.deepcopy(grid)
    beats = np.asarray(grid.get('raw_beat_times_seconds',grid['beat_times_seconds']), dtype=float)
    downbeats = np.asarray(grid.get('raw_downbeat_times_seconds',grid['downbeat_times_seconds']), dtype=float)
    for values in (beats, downbeats):
        if values.ndim != 1 or not len(values) or not np.isfinite(values).all() or (values < 0).any() or (np.diff(values) <= 0).any():
            raise ValueError('Pulsations modèle invalides')
    if len(beats) < 2:
        raise ValueError('Pulsations modèle insuffisantes')
    period = float(np.median(np.diff(beats)))
    groups = np.split(beats, np.where(np.diff(beats) >= .35 * period)[0] + 1)
    centers = np.asarray([np.mean(group) for group in groups])
    selected = []
    raw_activation = grid.get('raw_beat_downbeat_activation')
    activation = []
    offset = 0
    for index, group in enumerate(groups):
        target = (centers[index-1] + centers[index+1])/2 if 0 < index < len(groups)-1 else centers[index]
        choice = int(np.argmin(abs(group-target)))
        selected.append(float(group[choice]))
        if raw_activation is not None:
            # A merged doublet keeps the strongest downbeat evidence of its cluster.
            activation.append(float(max(raw_activation[offset:offset+len(group)])))
        offset += len(group)
    clean = np.asarray(selected)
    if len(clean) < 2:
        raise ValueError('Pulsations nettoyées insuffisantes')
    indices = np.unique([int(np.argmin(abs(clean-time))) for time in downbeats])
    gaps = np.diff(indices)
    evidence = dict(grid.get('phase_evidence', {}))
    evidence.update(four_beat_bar_fraction=float(np.mean(gaps == 4)) if len(gaps) else None,
                    bar_intervals_observed=len(gaps),
                    downbeat_beat_index_gaps=gaps.tolist(),
                    local_downbeats_agree_with_fixed_four_beats=bool(len(gaps) and (gaps == 4).all()))
    result.update(raw_beat_times_seconds=beats.tolist(), raw_downbeat_times_seconds=downbeats.tolist(),
                  beat_times_seconds=clean.tolist(), downbeat_times_seconds=clean[indices].tolist(),
                  origin_seconds=float(clean[indices[0]]), bpm=60/float(np.median(np.diff(clean))),
                  phase_evidence=evidence,
                  **({'beat_downbeat_activation': activation} if raw_activation is not None else {}),
                  grid_postprocessing={'policy':'merge_close_model_peaks_v1',
                                       'refractory_fraction_of_median_quarter':.35,
                                       'selection':'observed peak nearest adjacent cluster midpoint',
                                       'removed_beat_peaks':len(beats)-len(clean),
                                       'removed_downbeat_peaks':len(downbeats)-len(indices),
                                       'fixed_meter_disagreement_policy':'retain model timings; flag draft, no forced local phase correction'})
    return result

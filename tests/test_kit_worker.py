"""Synthetic DSP invariants; not a musical benchmark."""
import importlib.util
from pathlib import Path
import unittest
import numpy as np

spec = importlib.util.spec_from_file_location('kit_worker', Path(__file__).parents[1]/'scripts/kit_worker.py')
worker = importlib.util.module_from_spec(spec)
spec.loader.exec_module(worker)

class KitWorkerTests(unittest.TestCase):
    def test_roundtrip_preserves_timing_and_tail(self):
        rng = np.random.default_rng(3)
        waveform = rng.normal(0, .03, (23041, 2)).astype(np.float32)
        spectrum = worker.spectral_analysis(waveform)
        result = worker.spectral_synthesis(spectrum, len(waveform))
        self.assertEqual(result.shape, waveform.shape)
        np.testing.assert_allclose(result, waveform, atol=2e-8)

    def test_last_chunk_padding_never_leaks_into_real_frames(self):
        magnitude = np.ones((2, 2048, 519), dtype=np.float32)
        chunks = list(worker.chunk_magnitudes(magnitude))
        self.assertEqual([(s,c) for s,c,_ in chunks], [(0,512),(512,7)])
        self.assertEqual(chunks[1][2].shape, (1,2,2048,512))
        self.assertTrue(np.all(chunks[1][2][..., :7] == 1))
        self.assertTrue(np.all(chunks[1][2][..., 7:] == 0))
        restored = np.concatenate([x[0,...,:count] for _,count,x in chunks],axis=-1)
        np.testing.assert_array_equal(restored, magnitude)

    def test_invalid_audio_is_rejected(self):
        for waveform in (np.empty((0,2)),np.ones((9,1)),np.full((9,2),np.nan)):
            with self.assertRaises(ValueError): worker.spectral_analysis(waveform)

if __name__ == '__main__': unittest.main()

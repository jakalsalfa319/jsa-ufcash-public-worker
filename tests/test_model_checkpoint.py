"""Fitted Frontier checkpoint: validates serialization, safety and replay.

Small synthetic models are used for test speed. The full production archive is
verified against real UFC source hashes in the existing GitHub worker.
"""
from __future__ import annotations
import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

NEEDED=("numpy","sklearn","joblib","pandas","xgboost","catboost")
AVAILABLE=all(importlib.util.find_spec(name) is not None for name in NEEDED)


@unittest.skipUnless(AVAILABLE,"Pinned ML dependencies not yet installed")
class FittedCheckpointTests(unittest.TestCase):
    def setUp(self):
        import numpy as np
        from sklearn.linear_model import LogisticRegression
        from scripts import model_checkpoint as cp
        self.cp=cp
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        (self.root/"ufcash/data/processed").mkdir(parents=True)
        (self.root/"ufcash/data/processed/features.parquet").write_bytes(b"synthetic fixture - not UFC historical data")
        rng=np.random.default_rng(101)
        self.x=rng.normal(size=(103,56))
        self.models={}
        for idx,name in enumerate(cp.COMPONENTS):
            model=LogisticRegression(C=1.0,fit_intercept=False,max_iter=300)
            target=(self.x[:,0]+.1*self.x[:,idx+1]>0).astype(int)
            model.fit(self.x,target)
            self.models[name]=model
        self.expected=cp.combine(self.models,self.x,1.2)

    def export(self):
        with patch.object(self.cp,"source_hashes",return_value={}),patch.object(self.cp,"SOURCE_FILES",()):
            return self.cp.export_checkpoint(
                self.root,self.models,["synthetic_"+str(i) for i in range(50)],
                self.x,self.expected,1.2,.65,176
            )

    def test_checkpoint_serializes_restores_exact_probabilities(self):
        import numpy as np
        receipt=self.export()
        archive=self.root/"results/frozen_frontier_v2_checkpoint.tar.gz"
        restored=self.cp.load_checkpoint(archive,receipt["archiveSha256"])
        actual=self.cp.combine(restored["models"],self.x,1.2)
        np.testing.assert_allclose(self.expected,actual,atol=2e-10,rtol=0)
        self.assertEqual(receipt["fixtureReplayed"],24)
        self.assertFalse(receipt["prospectiveAccuracyVerified"])

    def test_reject_sha_mismatch_before_unpickling(self):
        r=self.export()
        archive=self.root/"results/frozen_frontier_v2_checkpoint.tar.gz"
        with self.assertRaisesRegex(ValueError,"SHA-256 mismatch"):
            self.cp.load_checkpoint(archive,"0"*64)
        with self.assertRaisesRegex(ValueError,"external trusted"):
            self.cp.load_checkpoint(archive,"")

    def test_reject_corrupt_archive_without_pickle_execution(self):
        receipt=self.export()
        archive=self.root/"results/frozen_frontier_v2_checkpoint.tar.gz"
        archive.write_bytes(archive.read_bytes()+b"NOT THE VERIFIED ARCHIVE")
        with self.assertRaisesRegex(ValueError,"SHA-256 mismatch"):
            self.cp.load_checkpoint(archive,receipt["archiveSha256"])

    def test_complementary_mirror_probabilities(self):
        import numpy as np
        a=self.cp.combine(self.models,self.x,1.2)
        b=self.cp.combine(self.models,-self.x,1.2)
        np.testing.assert_allclose(a+b,1,rtol=0,atol=1e-10)

    def test_mismatched_original_calibration_rejected(self):
        with patch.object(self.cp,"source_hashes",return_value={}):
            with self.assertRaisesRegex(ValueError,"cannot reproduce original calibration"):
                self.cp.export_checkpoint(self.root,self.models,
                    ["synthetic_"+str(i) for i in range(50)],self.x,
                    self.expected+.1,1.2,.65,176)

    def test_missing_historic_source_fails_closed(self):
        with self.assertRaisesRegex(ValueError,"Missing historic source"):
            self.cp.source_hashes(self.root)


if __name__=="__main__":
    unittest.main()

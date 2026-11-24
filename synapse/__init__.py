"""Modular SYNAPSE AUDIO DYNAMICS workflow.

This package plans production and distribution work; external posting, ad spend,
and financial transactions remain explicit integrations requiring approval.
"""

from .models import Track, ReleaseManifest
from .pipeline import SynapsePipeline

__all__ = ["Track", "ReleaseManifest", "SynapsePipeline"]

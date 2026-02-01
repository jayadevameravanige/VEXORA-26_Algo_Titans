"""
VoteGuard ML Module
AI-powered ghost and duplicate voter detection
"""

from .preprocessor import VoterDataPreprocessor
from .ghost_detector import GhostVoterDetector
from .duplicate_detector import DuplicateVoterDetector
from .explainer import VoteGuardExplainer
from .pipeline import VoteGuardPipeline, SecurityError
from .security_guards import SecurityGuard, InputValidator, OutputGuard, AuditLogger

__all__ = [
    'VoterDataPreprocessor',
    'GhostVoterDetector',
    'DuplicateVoterDetector',
    'VoteGuardExplainer',
    'VoteGuardPipeline',
    'SecurityGuard',
    'SecurityError',
    'InputValidator',
    'OutputGuard',
    'AuditLogger'
]

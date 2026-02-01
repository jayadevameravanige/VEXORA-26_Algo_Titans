"""
VoteGuard Detection Pipeline
Orchestrates the complete ghost and duplicate voter detection workflow
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Any, Optional
from dataclasses import dataclass, asdict
import json
from datetime import datetime

from .preprocessor import VoterDataPreprocessor
from .ghost_detector import GhostVoterDetector, GhostDetectionResult
from .duplicate_detector import DuplicateVoterDetector, DuplicateGroup, DuplicateDetectionResult
from .explainer import VoteGuardExplainer, FlagExplanation
from .security_guards import SecurityGuard


class SecurityError(Exception):
    """Raised when security checks fail and analysis is blocked"""
    pass


@dataclass
class PipelineResult:
    """Complete result from the detection pipeline"""
    timestamp: str
    total_records: int
    ghost_voters_flagged: int
    duplicate_voters_flagged: int
    ghost_explanations: List[Dict]
    duplicate_explanations: List[Dict]
    duplicate_groups: List[Dict]
    summary_report: Dict[str, Any]
    security_report: Dict[str, Any] = None
    
    def to_dict(self) -> Dict:
        return asdict(self)
    
    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2, default=str)


class VoteGuardPipeline:
    """
    Complete detection pipeline that:
    1. Loads and preprocesses voter data
    2. Runs SECURITY CHECKS (pre-analysis)
    3. Runs ghost voter detection
    4. Runs duplicate voter detection
    5. Runs SECURITY CHECKS (post-analysis)
    6. Generates explanations for all flagged records
    7. Produces summary report
    
    This is the main interface for the VoteGuard system.
    """
    
    def __init__(
        self,
        ghost_contamination: float = 0.05,
        name_similarity_threshold: float = 80.0,
        ghost_age_threshold: int = 110
    ):
        self.preprocessor = VoterDataPreprocessor()
        self.ghost_detector = GhostVoterDetector(
            contamination=ghost_contamination,
            age_threshold=ghost_age_threshold
        )
        self.duplicate_detector = DuplicateVoterDetector(
            name_similarity_threshold=name_similarity_threshold
        )
        self.explainer = VoteGuardExplainer()
        self.security_guard = SecurityGuard()  # NEW: Security guard
        
        self.df: Optional[pd.DataFrame] = None
        self.result: Optional[PipelineResult] = None
        
    def run(self, data_path: str) -> PipelineResult:
        """
        Run the complete detection pipeline.
        
        Args:
            data_path: Path to the voter CSV file
            
        Returns:
            PipelineResult with all detections and explanations
        """
        print("\n" + "=" * 60)
        print("VoteGuard Detection Pipeline")
        print("=" * 60)
        
        # Step 1: Load and preprocess data
        print("\nLoading and preprocessing data...")
        self.df = self.preprocessor.load_data(data_path)
        self.df = self.preprocessor.extract_features(self.df)
        print(f"   * Loaded {len(self.df)} voter records")
        
        # Step 2: PRE-ANALYSIS SECURITY CHECK
        print("\nRunning pre-analysis security checks...")
        can_proceed, pre_checks = self.security_guard.pre_analysis_check(self.df)
        for check in pre_checks:
            status = "[OK]" if check.passed else "[FAIL]"
            print(f"   {status} {check.check_name}: {check.message}")
        
        if not can_proceed:
            raise SecurityError("Pre-analysis security checks failed. Analysis blocked.")
        
        # Step 2: Ghost voter detection (using user's simple rule-based logic)
        print("\nRunning ghost voter detection...")
        # User's logic: age >= 110 OR last_voted_year < 2000 (or never voted)
        ghost_results = self.ghost_detector.detect_ghosts_simple(self.df)
        print(f"   * Flagged {len(ghost_results)} potential ghost voters")
        
        # Step 3: Duplicate voter detection
        print("\nRunning duplicate voter detection...")
        duplicate_groups, duplicate_results = self.duplicate_detector.detect_duplicates(self.df)
        print(f"   * Found {len(duplicate_groups)} duplicate groups")
        print(f"   * Flagged {len(duplicate_results)} potential duplicate voters")
        
        # Step 4: Generate explanations
        print("\nGenerating explanations...")
        ghost_explanations = []
        for result in ghost_results:
            # Type-insensitive matching for Voter_ID
            match_mask = self.df['Voter_ID'].astype(str) == str(result.voter_id)
            if not match_mask.any():
                continue
            voter_record = self.df[match_mask].iloc[0]
            explanation = self.explainer.explain_ghost_detection(voter_record, result)
            ghost_explanations.append(explanation)
        
        duplicate_explanations = []
        for result in duplicate_results:
            # Type-insensitive matching for Voter_ID
            match_mask = self.df['Voter_ID'].astype(str) == str(result.voter_id)
            if not match_mask.any():
                continue
            voter_record = self.df[match_mask].iloc[0]
            explanation = self.explainer.explain_duplicate_detection(
                voter_record, result, self.df
            )
            duplicate_explanations.append(explanation)
        
        print(f"   * Generated {len(ghost_explanations)} ghost voter explanations")
        print(f"   * Generated {len(duplicate_explanations)} duplicate voter explanations")
        
        # Step 5: POST-ANALYSIS SECURITY CHECK
        print("\nRunning post-analysis security checks...")
        all_confidence_scores = (
            [e.confidence for e in ghost_explanations] + 
            [e.confidence for e in duplicate_explanations]
        )
        total_flagged = len(ghost_results) + len(duplicate_results)
        
        results_valid, post_checks = self.security_guard.post_analysis_check(
            len(self.df), total_flagged, all_confidence_scores
        )
        for check in post_checks:
            status = "[OK]" if check.passed else "[WARN]"
            print(f"   {status} {check.check_name}: {check.message}")
        
        # Step 6: Generate summary report
        print("\nGenerating summary report...")
        summary = self.explainer.generate_summary_report(
            ghost_explanations, duplicate_explanations
        )
        
        # Get security compliance report
        security_report = self.security_guard.get_security_report()
        
        # Build pipeline result
        self.result = PipelineResult(
            timestamp=datetime.now().isoformat(),
            total_records=len(self.df),
            ghost_voters_flagged=len(ghost_results),
            duplicate_voters_flagged=len(duplicate_results),
            ghost_explanations=[e.to_dict() for e in ghost_explanations],
            duplicate_explanations=[e.to_dict() for e in duplicate_explanations],
            duplicate_groups=[asdict(g) for g in duplicate_groups],
            summary_report=summary,
            security_report=security_report
        )
        
        self._print_summary(summary)
        self._print_security_report(security_report)
        
        return self.result
    
    def _print_security_report(self, report: Dict[str, Any]):
        """Print security compliance summary"""
        print("\nSECURITY COMPLIANCE")
        print("-" * 40)
        for safeguard, status in report['safeguards'].items():
            print(f"   * {safeguard}: {status}")
    
    def _print_summary(self, summary: Dict[str, Any]):
        """Print a formatted summary of detection results"""
        print("\n" + "=" * 60)
        print("DETECTION SUMMARY")
        print("=" * 60)
        
        s = summary['summary']
        print(f"\nTotal Flagged Records: {s['total_flagged_records']}")
        print(f"   . Ghost Voters: {s['ghost_voters']}")
        print(f"   . Duplicate Voters: {s['duplicate_voters']}")
        print(f"   . Flagged as Both: {s['flagged_as_both']}")
        
        print(f"\nPriority Breakdown:")
        p = summary['recommended_priority']
        print(f"   - Immediate Review: {p['immediate_review']}")
        print(f"   - Standard Review: {p['standard_review']}")
        print(f"   - Periodic Review: {p['periodic_review']}")
        
        print("\n" + "=" * 60)
        print("Detection pipeline complete!")
        print("=" * 60 + "\n")
    
    def get_flagged_record(self, voter_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed information about a flagged record"""
        if self.result is None:
            return None
        
        # Check ghost explanations
        for exp in self.result.ghost_explanations:
            if exp['voter_id'] == voter_id:
                return exp
        
        # Check duplicate explanations
        for exp in self.result.duplicate_explanations:
            if exp['voter_id'] == voter_id:
                return exp
        
        return None
    
    def get_all_flagged_ids(self) -> List[str]:
        """Get all flagged voter IDs"""
        if self.result is None:
            return []
        
        ghost_ids = [e['voter_id'] for e in self.result.ghost_explanations]
        dup_ids = [e['voter_id'] for e in self.result.duplicate_explanations]
        
        return list(set(ghost_ids + dup_ids))
    
    def export_results(self, output_path: str = "detection_results.json"):
        """Export detection results to JSON file"""
        if self.result is None:
            raise ValueError("No results to export. Run the pipeline first.")
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(self.result.to_json())
        
        print(f"📁 Results exported to {output_path}")


if __name__ == "__main__":
    # Run the pipeline
    pipeline = VoteGuardPipeline()
    result = pipeline.run("voter_data.csv")
    
    # Export results
    pipeline.export_results("detection_results.json")
    
    # Show sample flagged record
    flagged_ids = pipeline.get_all_flagged_ids()
    if flagged_ids:
        sample = pipeline.get_flagged_record(flagged_ids[0])
        print("\n📋 Sample Flagged Record:")
        print(json.dumps(sample, indent=2, default=str))

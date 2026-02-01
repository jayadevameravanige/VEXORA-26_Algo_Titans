"""
VoteGuard Explainer Module
Generates human-readable explanations for flagged voter records
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
import json


@dataclass
class FlagExplanation:
    """Comprehensive explanation for a flagged voter record"""
    voter_id: str
    flag_type: str  # 'GHOST_VOTER', 'DUPLICATE_VOTER', 'BOTH'
    confidence: float
    primary_reason: str
    contributing_factors: List[Dict[str, Any]]
    recommended_action: str
    voter_details: Dict[str, Any]
    
    def to_dict(self) -> Dict:
        return asdict(self)
    
    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2, default=str)


class VoteGuardExplainer:
    """
    Generates explainable, human-readable reports for flagged voter records.
    
    This is critical for the human-in-the-loop workflow:
    - Election officials need to understand WHY a record is flagged
    - Explanations must be non-technical and actionable
    - Confidence scores help prioritize review
    """
    
    def __init__(self):
        self.action_recommendations = {
            'GHOST_VOTER_HIGH': 'Recommend verification of voter status (mortality/migration check)',
            'GHOST_VOTER_MEDIUM': 'Suggest field verification of current residence',
            'GHOST_VOTER_LOW': 'Flag for periodic review during next electoral roll update',
            'DUPLICATE_HIGH': 'Recommend immediate cross-reference with original registration',
            'DUPLICATE_MEDIUM': 'Suggest address verification to confirm separate individuals',
            'DUPLICATE_LOW': 'Flag for manual review - may be valid family members',
        }
    
    def explain_ghost_detection(
        self,
        voter_record: pd.Series,
        ghost_result: Any
    ) -> FlagExplanation:
        """Generate explanation for ghost voter detection"""
        
        # Determine severity based on confidence
        confidence = ghost_result.confidence
        if confidence >= 0.8:
            severity = 'HIGH'
        elif confidence >= 0.5:
            severity = 'MEDIUM'
        else:
            severity = 'LOW'
        
        # Get primary reason (most impactful)
        reasons = ghost_result.reasons
        primary_reason = reasons[0] if reasons else "Statistical anomaly detected"
        
        # Build contributing factors with impact scores
        contributing_factors = []
        for factor, impact in ghost_result.feature_contributions.items():
            if impact > 0:
                contributing_factors.append({
                    'factor': self._format_factor_name(factor),
                    'value': self._get_factor_value(voter_record, factor),
                    'impact': round(impact, 2)
                })
        
        # Sort by impact
        contributing_factors.sort(key=lambda x: x['impact'], reverse=True)
        
        # Get recommended action
        action_key = f'GHOST_VOTER_{severity}'
        recommended_action = self.action_recommendations.get(
            action_key, 
            'Flag for manual review'
        )
        
        # Voter details for context - capture ALL available columns
        # Use string conversion for all values to ensure JSON serializability
        voter_details = {str(k): str(v) if not pd.isna(v) else "" for k, v in voter_record.to_dict().items()}
        
        # Ensure a 'name' field exists for the UI
        if 'name' not in voter_details or not voter_details['name']:
            first = voter_details.get('First_Name', '')
            last = voter_details.get('Last_Name', '')
            voter_details['name'] = f"{first} {last}".strip() or "Unknown"
        
        return FlagExplanation(
            voter_id=ghost_result.voter_id,
            flag_type='GHOST_VOTER',
            confidence=round(confidence, 3),
            primary_reason=primary_reason,
            contributing_factors=contributing_factors,
            recommended_action=recommended_action,
            voter_details=voter_details
        )
    
    def explain_duplicate_detection(
        self,
        voter_record: pd.Series,
        duplicate_result: Any,
        df: pd.DataFrame
    ) -> FlagExplanation:
        """Generate explanation for duplicate voter detection"""
        
        confidence = duplicate_result.confidence
        if confidence >= 0.8:
            severity = 'HIGH'
        elif confidence >= 0.5:
            severity = 'MEDIUM'
        else:
            severity = 'LOW'
        
        # Get duplicate voter details
        duplicate_ids = duplicate_result.duplicate_of
        duplicate_details = []
        for dup_id in duplicate_ids[:3]:  # Limit to 3 for readability
            dup_row = df[df['Voter_ID'] == dup_id]
            if not dup_row.empty:
                dup_row = dup_row.iloc[0]
                duplicate_details.append({
                    'voter_id': dup_id,
                    'name': f"{dup_row.get('First_Name', '')} {dup_row.get('Last_Name', '')}",
                    'address': dup_row.get('Address', 'Unknown')[:50] + '...'
                })
        
        # Primary reason
        reasons = duplicate_result.reasons
        primary_reason = reasons[0] if reasons else "Records match on multiple criteria"
        
        # Contributing factors
        contributing_factors = [
            {'factor': reason, 'value': 'Match', 'impact': 0.3}
            for reason in reasons
        ]
        
        # Add duplicate voter info as factor
        if duplicate_details:
            contributing_factors.insert(0, {
                'factor': 'Matching voter(s)',
                'value': [d['voter_id'] for d in duplicate_details],
                'impact': 0.5
            })
        
        # Recommended action
        action_key = f'DUPLICATE_{severity}'
        recommended_action = self.action_recommendations.get(
            action_key,
            'Flag for manual review'
        )
        
        # Voter details for context - capture ALL available columns
        # Use string conversion for all values to ensure JSON serializability
        voter_details = {str(k): str(v) if not pd.isna(v) else "" for k, v in voter_record.to_dict().items()}
        
        # Ensure a 'name' field exists for the UI
        if 'name' not in voter_details or not voter_details['name']:
            first = voter_details.get('First_Name', '')
            last = voter_details.get('Last_Name', '')
            voter_details['name'] = f"{first} {last}".strip() or "Unknown"
        
        voter_details['duplicate_voters'] = duplicate_details
        
        return FlagExplanation(
            voter_id=duplicate_result.voter_id,
            flag_type='DUPLICATE_VOTER',
            confidence=round(confidence, 3),
            primary_reason=primary_reason,
            contributing_factors=contributing_factors,
            recommended_action=recommended_action,
            voter_details=voter_details
        )
    
    def _format_factor_name(self, factor: str) -> str:
        """Convert technical factor names to human-readable format"""
        mappings = {
            'Age': 'Voter Age',
            'Years_Since_Last_Vote': 'Years Since Last Vote',
            'Years_Since_Registration': 'Years Since Registration',
            'Is_Ghost_Age': 'Exceeds Expected Lifespan',
            'Is_Very_Old': 'Advanced Age Flag',
            'Long_Voting_Gap': 'Extended Voting Inactivity',
            'Old_Registration': 'Historical Registration',
            'Voting_Activity_Score': 'Voting Activity Pattern'
        }
        return mappings.get(factor, factor.replace('_', ' ').title())
    
    def _get_factor_value(self, record: pd.Series, factor: str) -> Any:
        """Get the actual value of a factor from the record"""
        if factor in record:
            value = record[factor]
            # Format special values
            if factor == 'Age':
                return f"{value} years"
            elif factor in ['Is_Ghost_Age', 'Is_Very_Old', 'Long_Voting_Gap', 'Old_Registration']:
                return 'Yes' if value else 'No'
            elif factor == 'Years_Since_Last_Vote':
                return f"{value} years" if value != 999 else "Never voted"
            return value
        return 'N/A'
    
    def generate_summary_report(
        self,
        ghost_explanations: List[FlagExplanation],
        duplicate_explanations: List[FlagExplanation]
    ) -> Dict[str, Any]:
        """Generate a summary report of all detections"""
        
        total_ghosts = len(ghost_explanations)
        total_duplicates = len(duplicate_explanations)
        
        # Find voters flagged as both
        ghost_ids = {e.voter_id for e in ghost_explanations}
        duplicate_ids = {e.voter_id for e in duplicate_explanations}
        both_ids = ghost_ids & duplicate_ids
        
        # Confidence distribution
        ghost_high = sum(1 for e in ghost_explanations if e.confidence >= 0.8)
        ghost_medium = sum(1 for e in ghost_explanations if 0.5 <= e.confidence < 0.8)
        ghost_low = sum(1 for e in ghost_explanations if e.confidence < 0.5)
        
        dup_high = sum(1 for e in duplicate_explanations if e.confidence >= 0.8)
        dup_medium = sum(1 for e in duplicate_explanations if 0.5 <= e.confidence < 0.8)
        dup_low = sum(1 for e in duplicate_explanations if e.confidence < 0.5)
        
        return {
            'summary': {
                'total_flagged_records': total_ghosts + total_duplicates - len(both_ids),
                'ghost_voters': total_ghosts,
                'duplicate_voters': total_duplicates,
                'flagged_as_both': len(both_ids)
            },
            'ghost_voter_breakdown': {
                'high_confidence': ghost_high,
                'medium_confidence': ghost_medium,
                'low_confidence': ghost_low
            },
            'duplicate_voter_breakdown': {
                'high_confidence': dup_high,
                'medium_confidence': dup_medium,
                'low_confidence': dup_low
            },
            'recommended_priority': {
                'immediate_review': ghost_high + dup_high,
                'standard_review': ghost_medium + dup_medium,
                'periodic_review': ghost_low + dup_low
            }
        }


if __name__ == "__main__":
    # Test example
    explainer = VoteGuardExplainer()
    
    print("VoteGuard Explainer Module")
    print("=" * 50)
    print("Ready to generate explanations for flagged records")

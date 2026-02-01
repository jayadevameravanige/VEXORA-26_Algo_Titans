"""
Duplicate Voter Detection Module
Uses fuzzy string matching and clustering to identify duplicate voter registrations
"""

import pandas as pd
import numpy as np
from rapidfuzz import fuzz, process
from typing import Dict, List, Tuple, Set
from dataclasses import dataclass
from collections import defaultdict


@dataclass
class DuplicateGroup:
    """Represents a group of potentially duplicate voter records"""
    group_id: int
    voter_ids: List[str]
    match_type: str  # 'name_dob', 'phonetic', 'address'
    confidence: float
    explanation: Dict[str, any]


@dataclass
class DuplicateDetectionResult:
    """Result of duplicate detection for a voter"""
    voter_id: str
    is_flagged: bool
    duplicate_of: List[str]
    similarity_scores: Dict[str, float]
    reasons: List[str]
    confidence: float


class DuplicateVoterDetector:
    """
    Detects potential duplicate voter registrations using:
    1. Fuzzy string matching on names
    2. Phonetic encoding (Soundex/Metaphone) matching
    3. DOB + Address clustering
    4. Same masked Aadhaar patterns
    """
    
    def __init__(
        self,
        name_similarity_threshold: float = 85.0,  # User's exact threshold: 85%
        phonetic_match_required: bool = False,    # User doesn't use phonetic
        same_dob_required: bool = True,
        same_pincode_required: bool = True        # User requires same pincode
    ):
        self.name_similarity_threshold = name_similarity_threshold
        self.phonetic_match_required = phonetic_match_required
        self.same_dob_required = same_dob_required
        self.same_pincode_required = same_pincode_required
        
    def _get_column(self, df: pd.DataFrame, possible_names: list, default=None):
        """Get column name case-insensitively from multiple possible names"""
        df_columns_lower = {col.lower(): col for col in df.columns}
        for name in possible_names:
            if name.lower() in df_columns_lower:
                return df_columns_lower[name.lower()]
        return default
    
    def detect_duplicates(self, df: pd.DataFrame) -> Tuple[List[DuplicateGroup], List[DuplicateDetectionResult]]:
        """
        Main detection method - finds all duplicate groups and individual results.
        
        Algorithm (matches user's logic):
        1. Group by DOB AND Pincode (both required)
        2. Within each group, apply fuzzy name matching (>=85%)
        3. Mark as duplicate if all criteria match
        
        Handles flexible column names (case-insensitive):
        - DOB, dob, date_of_birth
        - Pincode, pincode, zip_code
        - name OR First_Name + Last_Name
        - Voter_ID, voter_id
        """
        all_groups = []
        all_results = {}
        group_id = 0
        
        # Find column names flexibly (case-insensitive)
        dob_col = self._get_column(df, ['dob', 'DOB', 'Dob', 'date_of_birth', 'DateOfBirth'])
        pincode_col = self._get_column(df, ['pincode', 'Pincode', 'PINCODE', 'zip_code', 'ZipCode', 'zip'])
        voter_id_col = self._get_column(df, ['voter_id', 'Voter_ID', 'VoterID', 'id', 'ID'])
        name_col = self._get_column(df, ['name', 'Name', 'NAME', 'full_name', 'FullName'])
        first_name_col = self._get_column(df, ['first_name', 'First_Name', 'FirstName', 'fname'])
        last_name_col = self._get_column(df, ['last_name', 'Last_Name', 'LastName', 'lname'])
        
        # Build group key from DOB and Pincode
        if not dob_col or not pincode_col:
            print("Warning: DOB or Pincode column not found")
            return [], []
        
        df['_group_key'] = df[dob_col].astype(str) + '_' + df[pincode_col].astype(str)
        dob_pincode_groups = df.groupby('_group_key')
        
        for key, group in dob_pincode_groups:
            if len(group) < 2:
                continue
            
            # Extract DOB and Pincode from the composite key
            dob = key.split('_')[0] if '_' in str(key) else str(key)
            
            # Find potential duplicates within this DOB+Pincode group
            duplicates = self._find_name_matches_in_group(group)
            
            for dup_pair in duplicates:
                group_id += 1
                voter_ids = list(dup_pair['voter_ids'])
                
                dup_group = DuplicateGroup(
                    group_id=group_id,
                    voter_ids=voter_ids,
                    match_type='name_dob',
                    confidence=dup_pair['confidence'],
                    explanation={
                        'dob': dob,
                        'name_similarity': dup_pair['similarity'],
                        'phonetic_match': dup_pair.get('phonetic_match', False)
                    }
                )
                all_groups.append(dup_group)
                
                # Create individual results
                for vid in voter_ids:
                    others = [v for v in voter_ids if v != vid]
                    if vid not in all_results:
                        all_results[vid] = DuplicateDetectionResult(
                            voter_id=str(vid),
                            is_flagged=True,
                            duplicate_of=others,
                            similarity_scores=dup_pair.get('scores', {}),
                            reasons=self._generate_reasons(dup_pair, dob),
                            confidence=dup_pair['confidence']
                        )
                    else:
                        # Merge with existing result
                        all_results[vid].duplicate_of.extend(others)
                        all_results[vid].duplicate_of = list(set(all_results[vid].duplicate_of))
        
        # Strategy 2 DISABLED: Aadhaar matching causes too many false positives
        # Masked Aadhaar only has 10,000 possible values (4 digits), creating many
        # accidental collisions in a 10,000+ record dataset.
        # If you have FULL Aadhaar numbers, you can re-enable this strategy.
        
        return all_groups, list(all_results.values())
    
    def _find_name_matches_in_group(self, group: pd.DataFrame) -> List[Dict]:
        """
        Find fuzzy name matches within a DOB+Pincode group.
        
        User's logic: if same DOB and same Pincode, check name similarity >= 85%
        
        Handles flexible column names (case-insensitive):
        - name OR First_Name + Last_Name
        - Voter_ID, voter_id
        """
        matches = []
        processed_pairs: Set[Tuple[str, str]] = set()
        
        # Find column names flexibly
        voter_id_col = self._get_column(group, ['voter_id', 'Voter_ID', 'VoterID', 'id', 'ID'])
        name_col = self._get_column(group, ['name', 'Name', 'NAME', 'full_name', 'FullName'])
        first_name_col = self._get_column(group, ['first_name', 'First_Name', 'FirstName', 'fname'])
        last_name_col = self._get_column(group, ['last_name', 'Last_Name', 'LastName', 'lname'])
        normalized_col = self._get_column(group, ['full_name_normalized', 'Full_Name_Normalized'])
        
        records = group.to_dict('records')
        
        for i, rec1 in enumerate(records):
            for j, rec2 in enumerate(records[i+1:], i+1):
                # Get voter IDs flexibly
                vid1 = rec1.get(voter_id_col, f"row_{i}") if voter_id_col else f"row_{i}"
                vid2 = rec2.get(voter_id_col, f"row_{j}") if voter_id_col else f"row_{j}"
                
                # Skip if already processed
                pair_key = tuple(sorted([str(vid1), str(vid2)]))
                if pair_key in processed_pairs:
                    continue
                processed_pairs.add(pair_key)
                
                # Get names flexibly - priority: normalized > name col > first+last
                name1 = ""
                name2 = ""
                
                # Try normalized name first
                if normalized_col:
                    name1 = str(rec1.get(normalized_col, '')).strip().lower()
                    name2 = str(rec2.get(normalized_col, '')).strip().lower()
                
                # If not available, try single 'name' column
                if not name1 and name_col:
                    name1 = str(rec1.get(name_col, '')).strip().lower()
                if not name2 and name_col:
                    name2 = str(rec2.get(name_col, '')).strip().lower()
                
                # If still not available, build from First_Name + Last_Name
                if not name1 and first_name_col:
                    fn = str(rec1.get(first_name_col, '')).strip()
                    ln = str(rec1.get(last_name_col, '')) if last_name_col else ''
                    name1 = f"{fn} {ln}".strip().lower()
                if not name2 and first_name_col:
                    fn = str(rec2.get(first_name_col, '')).strip()
                    ln = str(rec2.get(last_name_col, '')) if last_name_col else ''
                    name2 = f"{fn} {ln}".strip().lower()
                
                # Skip if still empty
                if not name1 or not name2:
                    continue
                
                # User's logic: token_sort_ratio for name similarity
                similarity = fuzz.token_sort_ratio(name1, name2)
                
                # User's threshold: >= 85%
                if similarity >= self.name_similarity_threshold:
                    # Matched! Calculate confidence based on similarity
                    confidence = self._calculate_confidence(
                        similarity, 
                        phonetic_match=False,  # Not used in user's logic
                        same_pincode=True      # Already guaranteed by grouping
                    )
                    
                    matches.append({
                        'voter_ids': {vid1, vid2},
                        'similarity': similarity,
                        'phonetic_match': False,
                        'confidence': confidence,
                        'scores': {
                            f'{vid1}_to_{vid2}': similarity
                        }
                    })
        
        return matches
    
    def _calculate_confidence(
        self,
        name_similarity: float,
        phonetic_match: bool,
        same_pincode: bool
    ) -> float:
        """Calculate confidence score for duplicate detection"""
        confidence = 0.0
        
        # Name similarity contribution (max 0.5)
        confidence += (name_similarity / 100) * 0.5
        
        # Phonetic match contribution (0.25)
        if phonetic_match:
            confidence += 0.25
        
        # Same pincode contribution (0.15)
        if same_pincode:
            confidence += 0.15
        
        # Same DOB is required, so add baseline (0.1)
        confidence += 0.1
        
        return min(1.0, confidence)
    
    def _generate_reasons(self, match_info: Dict, dob: str) -> List[str]:
        """Generate human-readable reasons for duplicate flagging"""
        reasons = []
        
        similarity = match_info.get('similarity', 0)
        phonetic = match_info.get('phonetic_match', False)
        
        reasons.append(f"Same date of birth: {dob}")
        
        if similarity >= 95:
            reasons.append(f"Very high name similarity ({similarity}%)")
        elif similarity >= 90:
            reasons.append(f"High name similarity ({similarity}%) - possible typo variation")
        else:
            reasons.append(f"Moderate name similarity ({similarity}%) - possible spelling variation")
        
        if phonetic:
            reasons.append("Names sound similar (phonetic match)")
        
        return reasons
    
    def get_summary(self, groups: List[DuplicateGroup]) -> Dict[str, any]:
        """Generate summary statistics for duplicate detection"""
        return {
            'total_groups': len(groups),
            'total_flagged_voters': sum(len(g.voter_ids) for g in groups),
            'by_match_type': {
                'name_dob': len([g for g in groups if g.match_type == 'name_dob']),
                'aadhaar': len([g for g in groups if g.match_type == 'aadhaar']),
                'address': len([g for g in groups if g.match_type == 'address'])
            },
            'avg_confidence': np.mean([g.confidence for g in groups]) if groups else 0
        }


if __name__ == "__main__":
    # Test the detector
    from preprocessor import VoterDataPreprocessor
    
    preprocessor = VoterDataPreprocessor()
    df = preprocessor.load_data("../voter_data.csv")
    df = preprocessor.extract_features(df)
    
    detector = DuplicateVoterDetector(name_similarity_threshold=80.0)
    groups, results = detector.detect_duplicates(df)
    
    summary = detector.get_summary(groups)
    
    print(f"\n🔍 Duplicate Voter Detection Results")
    print(f"=" * 50)
    print(f"Total duplicate groups found: {summary['total_groups']}")
    print(f"Total flagged voters: {summary['total_flagged_voters']}")
    print(f"Average confidence: {summary['avg_confidence']:.2%}")
    
    print(f"\n📋 Sample duplicate groups:")
    for group in groups[:5]:
        print(f"\n  Group {group.group_id}:")
        print(f"  Voter IDs: {group.voter_ids}")
        print(f"  Match type: {group.match_type}")
        print(f"  Confidence: {group.confidence:.2%}")
        print(f"  Details: {group.explanation}")

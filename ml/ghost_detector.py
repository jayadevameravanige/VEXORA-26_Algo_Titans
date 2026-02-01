"""
Ghost Voter Detection Module
Uses Isolation Forest for anomaly detection to identify potential ghost voters
"""

import pandas as pd
import numpy as np
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
from typing import Dict, List, Tuple, Any
from dataclasses import dataclass


@dataclass
class GhostDetectionResult:
    """Result of ghost voter detection for a single record"""
    voter_id: str
    is_flagged: bool
    anomaly_score: float
    confidence: float
    reasons: List[str]
    feature_contributions: Dict[str, float]


class GhostVoterDetector:
    def __init__(
        self,
        contamination: float = 0.05,  # Expected proportion of ghost records
        random_state: int = 42,
        age_threshold: int = 110,
        inactivity_threshold: int = 20  # Years since last vote
    ):
        self.contamination = contamination
        self.random_state = random_state
        self.age_threshold = age_threshold
        self.inactivity_threshold = inactivity_threshold
        
        self.model = IsolationForest(
            contamination=contamination,
            random_state=random_state,
            n_estimators=100,
            max_samples='auto'
        )
        self.scaler = StandardScaler()
        self.feature_names = []
        self.is_fitted = False
        
    def fit(self, features_df: pd.DataFrame, feature_names: List[str]):
        """Fit the Isolation Forest model on training data"""
        self.feature_names = feature_names
        
        # Scale features for better model performance
        X = self.scaler.fit_transform(features_df)
        
        # Fit the model
        self.model.fit(X)
        self.is_fitted = True
        
        return self
    
    def predict(self, features_df: pd.DataFrame) -> Tuple[np.ndarray, np.ndarray]:
        """
        Predict ghost voters.
        
        Returns:
            predictions: -1 for anomalies (ghosts), 1 for normal
            scores: Anomaly scores (lower = more anomalous)
        """
        if not self.is_fitted:
            raise ValueError("Model must be fitted before prediction")
        
        X = self.scaler.transform(features_df)
        predictions = self.model.predict(X)
        scores = self.model.decision_function(X)
        
        return predictions, scores
    
    def _get_column(self, df: pd.DataFrame, possible_names: list, default=None):
        """Get column value case-insensitively from multiple possible names"""
        df_columns_lower = {col.lower(): col for col in df.columns}
        for name in possible_names:
            if name.lower() in df_columns_lower:
                return df_columns_lower[name.lower()]
        return default
    
    def detect_ghosts_simple(self, df: pd.DataFrame) -> List[GhostDetectionResult]:
        """
        Simple rule-based ghost detection:
        - age >= 110 years → ghost
        - last_voted_year < 2000 or never voted → ghost
        
        Handles flexible column names (case-insensitive):
        - Age, age, AGE
        - DOB, dob, Dob, date_of_birth
        - Last_Voted_Year, last_voted_year, last_voted
        - Voter_ID, voter_id, VoterID
        """
        from datetime import datetime
        
        results = []
        current_year = datetime.now().year
        
        # Find column names flexibly (case-insensitive)
        age_col = self._get_column(df, ['age', 'Age', 'AGE'])
        dob_col = self._get_column(df, ['dob', 'DOB', 'Dob', 'date_of_birth', 'DateOfBirth'])
        voter_id_col = self._get_column(df, ['voter_id', 'Voter_ID', 'VoterID', 'id', 'ID'])
        last_voted_col = self._get_column(df, ['last_voted_year', 'Last_Voted_Year', 'last_voted', 'LastVotedYear'])
        
        for idx in range(len(df)):
            row = df.iloc[idx]
            
            # Get voter ID
            voter_id = row[voter_id_col] if voter_id_col else f"row_{idx}"
            reasons = []
            
            # Get age - prefer Age column if exists, otherwise calculate from DOB
            age = 0
            if age_col:
                try:
                    age = int(row[age_col])
                except:
                    age = 0
            elif dob_col:
                # Calculate age from DOB
                try:
                    dob_str = str(row[dob_col])
                    if '-' in dob_str:
                        dob_parts = dob_str.split('-')
                        # Handle both DD-MM-YYYY and YYYY-MM-DD formats
                        if len(dob_parts) == 3:
                            if len(dob_parts[0]) == 4:  # YYYY-MM-DD
                                birth_year = int(dob_parts[0])
                            else:  # DD-MM-YYYY
                                birth_year = int(dob_parts[2])
                            age = current_year - birth_year
                    elif '/' in dob_str:
                        dob_parts = dob_str.split('/')
                        if len(dob_parts) == 3:
                            birth_year = int(dob_parts[2]) if len(dob_parts[2]) == 4 else int(dob_parts[0])
                            age = current_year - birth_year
                except:
                    age = 0
            
            # Check age >= 110 (ghost indicator)
            is_ghost_age = age >= 110
            if is_ghost_age:
                reasons.append(f"Age is {age} years (>= 110)")
            
            # Check last_voted_year
            is_inactive = False
            if last_voted_col:
                last_voted = row[last_voted_col]
                last_voted_str = str(last_voted).strip().lower()
                
                if pd.isna(last_voted) or last_voted_str == '' or last_voted_str == 'never voted' or last_voted_str == 'nan':
                    is_inactive = True
                    reasons.append("Never voted or last vote year unknown")
                else:
                    try:
                        last_voted_year = int(float(last_voted_str))
                        if last_voted_year < 2000:
                            is_inactive = True
                            reasons.append(f"Last voted in {last_voted_year} (before 2000)")
                    except ValueError:
                        pass  # Can't parse, don't mark as inactive
            
            # GHOST = age >= 110 OR last_voted < 2000 OR never voted
            is_flagged = is_ghost_age or is_inactive
            
            if is_flagged:
                confidence = 0.6 if is_ghost_age else 0.4
                if is_ghost_age and is_inactive:
                    confidence = 1.0
                
                results.append(GhostDetectionResult(
                    voter_id=str(voter_id),
                    is_flagged=True,
                    anomaly_score=-1.0,
                    confidence=confidence,
                    reasons=reasons,
                    feature_contributions={}
                ))
        
        return results
    
    def detect_ghosts(
        self,
        df: pd.DataFrame,
        features_df: pd.DataFrame
    ) -> List[GhostDetectionResult]:
        """
        Run full ghost detection pipeline with explanations.
        
        Args:
            df: Full DataFrame with all voter data
            features_df: Preprocessed features DataFrame
            
        Returns:
            List of GhostDetectionResult for flagged records
        """
        predictions, scores = self.predict(features_df)
        
        results = []
        
        # Helper to safely convert to number
        def safe_num(val, default=0):
            try:
                if pd.isna(val):
                    return default
                return float(str(val).strip())
            except (ValueError, TypeError):
                return default
        
        for idx in range(len(df)):
            voter_id = df.iloc[idx]['Voter_ID']
            is_anomaly = predictions[idx] == -1
            anomaly_score = scores[idx]
            
            # Rule-based checks (high confidence patterns) - use safe_num for type safety
            age = safe_num(df.iloc[idx].get('Age', 0), 0)
            years_since_vote = safe_num(df.iloc[idx].get('Years_Since_Last_Vote', 0), 0)
            
            # Strong ghost indicators
            is_ghost_age = age > self.age_threshold
            is_long_inactive = years_since_vote > self.inactivity_threshold
            
            # Combine ML prediction with rule-based checks
            # Rule-based checks override ML for clear cases
            is_flagged = is_anomaly or is_ghost_age
            
            if is_flagged:
                # Generate explanation
                reasons = self._generate_reasons(df.iloc[idx], features_df.iloc[idx])
                feature_contributions = self._get_feature_contributions(
                    features_df.iloc[idx], anomaly_score
                )
                
                # Calculate confidence (0-1 scale)
                confidence = self._calculate_confidence(
                    is_ghost_age, is_long_inactive, is_anomaly, anomaly_score
                )
                
                results.append(GhostDetectionResult(
                    voter_id=str(voter_id),
                    is_flagged=True,
                    anomaly_score=float(anomaly_score),
                    confidence=confidence,
                    reasons=reasons,
                    feature_contributions=feature_contributions
                ))
        
        return results
    
    def _generate_reasons(self, row: pd.Series, features: pd.Series) -> List[str]:
        """Generate human-readable reasons for flagging"""
        reasons = []
        
        # Helper to safely convert to number
        def safe_num(val, default=0):
            try:
                if pd.isna(val):
                    return default
                return float(str(val).strip())
            except (ValueError, TypeError):
                return default
        
        age = safe_num(row.get('Age', 0), 0)
        years_since_vote = safe_num(row.get('Years_Since_Last_Vote', 0), 0)
        registration_year = safe_num(row.get('Registration_Year', 2000), 2000)
        
        if age > 130:
            reasons.append(f"Extremely unrealistic age of {int(age)} years (likely deceased)")
        elif age > 110:
            reasons.append(f"Voter age of {int(age)} years exceeds expected lifespan")
        elif age > 100:
            reasons.append(f"Voter is {int(age)} years old - requires verification")
        
        if years_since_vote > 25:
            reasons.append(f"No voting activity in {int(years_since_vote)} years")
        elif years_since_vote > 20:
            reasons.append(f"Long voting gap of {int(years_since_vote)} years")
        
        if registration_year < 1960:
            reasons.append(f"Very old registration from {int(registration_year)}")
        
        last_voted = row.get('Last_Voted_Year', 'Unknown')
        if str(last_voted).lower() in ["never voted", "never", "none", "n/a", "na", ""]:
            reasons.append("No voting record found")
        
        if not reasons:
            reasons.append("Statistical anomaly detected in voter pattern")
        
        return reasons
    
    def _get_feature_contributions(
        self,
        features: pd.Series,
        anomaly_score: float
    ) -> Dict[str, float]:
        """Calculate which features contributed most to the anomaly"""
        contributions = {}
        
        # Helper to safely convert to number
        def safe_num(val, default=0):
            try:
                if pd.isna(val):
                    return default
                return float(str(val).strip())
            except (ValueError, TypeError):
                return default
        
        # Simple contribution estimation based on feature values
        for name in self.feature_names:
            value = safe_num(features[name], 0)
            if name == 'Age':
                # Higher age = more contribution if anomalous
                contributions[name] = min(1.0, value / 150) if value > 90 else 0.0
            elif name == 'Years_Since_Last_Vote':
                contributions[name] = min(1.0, value / 50) if value > 10 else 0.0
            elif name == 'Is_Ghost_Age':
                contributions[name] = value * 0.8
            elif name == 'Is_Very_Old':
                contributions[name] = value * 0.5
            elif name == 'Long_Voting_Gap':
                contributions[name] = value * 0.4
            else:
                contributions[name] = 0.1 if value > 0 else 0.0
        
        # Normalize contributions
        total = sum(contributions.values())
        if total > 0:
            contributions = {k: round(v / total, 3) for k, v in contributions.items()}
        
        return contributions
    
    def _calculate_confidence(
        self,
        is_ghost_age: bool,
        is_long_inactive: bool,
        is_ml_anomaly: bool,
        anomaly_score: float
    ) -> float:
        """Calculate confidence score for the detection"""
        confidence = 0.0
        
        # Strong indicator: age > 110
        if is_ghost_age:
            confidence += 0.7
        
        # Supporting indicator: long inactivity
        if is_long_inactive:
            confidence += 0.15
        
        # ML confirmation
        if is_ml_anomaly:
            confidence += 0.15
        
        return min(1.0, confidence)


if __name__ == "__main__":
    # Test the detector
    from preprocessor import VoterDataPreprocessor
    
    preprocessor = VoterDataPreprocessor()
    df = preprocessor.load_data("../voter_data.csv")
    df = preprocessor.extract_features(df)
    
    features_df, feature_names = preprocessor.get_ghost_detection_features(df)
    
    detector = GhostVoterDetector(contamination=0.05)
    detector.fit(features_df, feature_names)
    
    results = detector.detect_ghosts(df, features_df)
    
    print(f"\n🔍 Ghost Voter Detection Results")
    print(f"=" * 50)
    print(f"Total records analyzed: {len(df)}")
    print(f"Flagged as potential ghosts: {len(results)}")
    
    print(f"\n📋 Sample flagged records:")
    for result in results[:5]:
        print(f"\n  Voter ID: {result.voter_id}")
        print(f"  Confidence: {result.confidence:.2%}")
        print(f"  Reasons: {', '.join(result.reasons)}")

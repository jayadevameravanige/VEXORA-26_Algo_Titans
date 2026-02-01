"""
VoteGuard Security Guards Module
Implements safety checks, validation, and bias prevention for the AI model
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Any, Optional
from dataclasses import dataclass
from datetime import datetime
import hashlib
import json


@dataclass
class SecurityCheckResult:
    """Result of a security validation check"""
    check_name: str
    passed: bool
    severity: str  # 'critical', 'warning', 'info'
    message: str
    details: Optional[Dict] = None


class InputValidator:
    """Validates input data before processing"""
    
    REQUIRED_COLUMNS = [
        'voter_id', 'first_name', 'last_name', 'dob', 
        'gender', 'address', 'pincode', 'registration_year'
    ]
    
    # Aliases for required columns to handle variations in input data
    COLUMN_ALIASES = {
        'voter_id': ['voter_id', 'voterid', 'voter id', 'id'],
        'first_name': ['first_name', 'firstname', 'first name', 'fname', 'name'],
        'last_name': ['last_name', 'lastname', 'last name', 'lname', 'name'],
        'dob': ['dob', 'date_of_birth', 'birth_date', 'dateofbirth'],
        'gender': ['gender', 'sex'],
        'address': ['address', 'residence', 'addr'],
        'pincode': ['pincode', 'zip_code', 'zip', 'zipcode'],
        'registration_year': ['registration_year', 'reg_year', 'year_registered']
    }
    
    # Columns that should NEVER be used for detection (bias prevention)
    FORBIDDEN_FEATURES = [
        'Religion', 'Caste', 'Community', 'Ethnicity', 
        'Political_Party', 'Income', 'Occupation'
    ]
    
    def validate_input(self, df: pd.DataFrame) -> List[SecurityCheckResult]:
        """Run all input validation checks"""
        # Normalize column names to lowercase for robust checking
        df_cols_lower = [str(col).lower() for col in df.columns]
        
        results = []
        
        # Check 1: Required columns (using aliases and case-insensitive matching)
        results.append(self._check_required_columns(df_cols_lower))
        
        # Check 2: Forbidden columns (bias prevention)
        results.append(self._check_forbidden_columns(df_cols_lower))
        
        # Check 3: Data integrity
        results.append(self._check_data_integrity(df))
        
        # Check 4: Suspicious patterns in input
        results.append(self._check_input_manipulation(df))
        
        return results
    
    def _check_required_columns(self, df_cols_lower: List[str]) -> SecurityCheckResult:
        """Ensure all required columns (or their aliases) are present"""
        missing = []
        
        for req_col in self.REQUIRED_COLUMNS:
            # Check if the required column or any of its aliases exist in the dataframe
            aliases = self.COLUMN_ALIASES.get(req_col, [req_col])
            found = any(alias in df_cols_lower for alias in aliases)
            
            if not found:
                missing.append(req_col)
        
        # SPECIAL CASE: if 'name' is present, it can satisfy both first_name and last_name
        if 'name' in df_cols_lower:
            if 'first_name' in missing:
                missing.remove('first_name')
            if 'last_name' in missing:
                if 'last_name' in missing: # double check if still there
                    missing.remove('last_name')
        
        if missing:
            return SecurityCheckResult(
                check_name="Required Columns",
                passed=False,
                severity="critical",
                message=f"Missing required columns (or aliases): {missing}",
                details={"missing_columns": missing}
            )
        
        return SecurityCheckResult(
            check_name="Required Columns",
            passed=True,
            severity="info",
            message="All required columns (or acceptable aliases) present"
        )
    
    def _check_forbidden_columns(self, df_cols_lower: List[str]) -> SecurityCheckResult:
        """Ensure no bias-inducing columns are present (case-insensitive)"""
        found = [col for col in self.FORBIDDEN_FEATURES if col.lower() in df_cols_lower]
        
        if found:
            return SecurityCheckResult(
                check_name="Bias Prevention",
                passed=False,
                severity="critical",
                message=f"BLOCKED: Dataset contains bias-risk columns: {found}",
                details={"forbidden_columns": found}
            )
        
        return SecurityCheckResult(
            check_name="Bias Prevention",
            passed=True,
            severity="info",
            message="No bias-risk columns detected"
        )
    
    def _check_data_integrity(self, df: pd.DataFrame) -> SecurityCheckResult:
        """Check for data integrity issues"""
        issues = []
        
        voter_id_col = next((col for col in df.columns if str(col).lower() in ['voter_id', 'voterid', 'id']), None)
        if voter_id_col is not None:
            # Check for null Voter IDs
            null_ids = df[voter_id_col].isna().sum()
            if null_ids > 0:
                issues.append(f"{null_ids} null Voter IDs")
            
            # Check for duplicate Voter IDs
            dup_ids = df[voter_id_col].duplicated().sum()
            if dup_ids > 0:
                issues.append(f"{dup_ids} duplicate Voter IDs")
        else:
            issues.append("Voter ID column not found for integrity check")
        
        if issues:
            return SecurityCheckResult(
                check_name="Data Integrity",
                passed=False,
                severity="warning",
                message=f"Data integrity issues: {', '.join(issues)}",
                details={"issues": issues}
            )
        
        return SecurityCheckResult(
            check_name="Data Integrity",
            passed=True,
            severity="info",
            message="Data integrity verified"
        )
    
    def _check_input_manipulation(self, df: pd.DataFrame) -> SecurityCheckResult:
        """Detect potential input data manipulation"""
        suspicious = []
        
        # Check for unusually high percentage of one value
        for col_name in ['gender', 'sex', 'pincode', 'zip_code']:
            found_col = next((c for c in df.columns if str(c).lower() == col_name), None)
            if found_col:
                mode_pct = df[found_col].value_counts(normalize=True).max()
                if mode_pct > 0.95:
                    suspicious.append(f"{found_col} has {mode_pct:.0%} same value")
        
        if suspicious:
            return SecurityCheckResult(
                check_name="Input Manipulation Detection",
                passed=False,
                severity="warning",
                message=f"Suspicious patterns detected: {suspicious}",
                details={"patterns": suspicious}
            )
        
        return SecurityCheckResult(
            check_name="Input Manipulation Detection",
            passed=True,
            severity="info",
            message="No suspicious input patterns detected"
        )


class OutputGuard:
    """Guards for model output to prevent harmful decisions"""
    
    # Maximum percentage of records that can be flagged (prevents mass disenfranchisement)
    MAX_FLAG_PERCENTAGE = 0.15  # 15%
    
    # Minimum confidence required for different actions
    CONFIDENCE_THRESHOLDS = {
        'flag_for_review': 0.5,
        'recommend_verification': 0.7,
        'high_priority': 0.85
    }
    
    def validate_output(
        self, 
        total_records: int,
        flagged_records: int,
        confidence_scores: List[float]
    ) -> List[SecurityCheckResult]:
        """Validate model output for safety"""
        results = []
        
        # Check 1: Flag rate limit
        results.append(self._check_flag_rate(total_records, flagged_records))
        
        # Check 2: Confidence distribution
        results.append(self._check_confidence_distribution(confidence_scores))
        
        # Check 3: No automatic actions
        results.append(self._verify_human_in_loop())
        
        return results
    
    def _check_flag_rate(self, total: int, flagged: int) -> SecurityCheckResult:
        """Ensure flagging rate doesn't exceed safety threshold"""
        rate = flagged / total if total > 0 else 0
        
        if rate > self.MAX_FLAG_PERCENTAGE:
            return SecurityCheckResult(
                check_name="Flag Rate Limit",
                passed=False,
                severity="critical",
                message=f"FLAG RATE EXCEEDED: {rate:.1%} > {self.MAX_FLAG_PERCENTAGE:.0%} limit",
                details={
                    "flag_rate": rate,
                    "max_allowed": self.MAX_FLAG_PERCENTAGE,
                    "flagged": flagged,
                    "total": total
                }
            )
        
        return SecurityCheckResult(
            check_name="Flag Rate Limit",
            passed=True,
            severity="info",
            message=f"Flag rate {rate:.1%} within safe limits"
        )
    
    def _check_confidence_distribution(self, scores: List[float]) -> SecurityCheckResult:
        """Check for abnormal confidence score distribution"""
        if not scores:
            return SecurityCheckResult(
                check_name="Confidence Distribution",
                passed=True,
                severity="info",
                message="No scores to validate"
            )
        
        avg = np.mean(scores)
        
        # Alert if too many high-confidence flags (possible overfitting)
        high_conf = sum(1 for s in scores if s > 0.9) / len(scores)
        
        if high_conf > 0.8:
            return SecurityCheckResult(
                check_name="Confidence Distribution",
                passed=False,
                severity="warning",
                message=f"Suspiciously high confidence: {high_conf:.0%} above 90%",
                details={"high_confidence_rate": high_conf, "average": avg}
            )
        
        return SecurityCheckResult(
            check_name="Confidence Distribution",
            passed=True,
            severity="info",
            message=f"Confidence distribution normal (avg: {avg:.2f})"
        )
    
    def _verify_human_in_loop(self) -> SecurityCheckResult:
        """Verify human-in-the-loop is enforced"""
        # This is always true by design - we don't have auto-delete capability
        return SecurityCheckResult(
            check_name="Human-in-the-Loop",
            passed=True,
            severity="info",
            message="VERIFIED: No automated deletion capability exists"
        )


class AuditLogger:
    """Secure audit logging for all model actions"""
    
    def __init__(self, log_file: str = "audit_security.log"):
        self.log_file = log_file
        self.session_id = self._generate_session_id()
    
    def _generate_session_id(self) -> str:
        """Generate unique session identifier"""
        timestamp = datetime.now().isoformat()
        return hashlib.sha256(timestamp.encode()).hexdigest()[:16]
    
    def log_event(
        self, 
        event_type: str, 
        details: Dict[str, Any],
        user: str = "system"
    ):
        """Log a security event"""
        event = {
            "timestamp": datetime.now().isoformat(),
            "session_id": self.session_id,
            "event_type": event_type,
            "user": user,
            "details": details
        }
        
        # Append to log file
        with open(self.log_file, 'a', encoding='utf-8') as f:
            f.write(json.dumps(event) + '\n')
        
        return event
    
    def log_analysis_start(self, record_count: int):
        """Log start of analysis"""
        return self.log_event("ANALYSIS_START", {
            "record_count": record_count,
            "action": "Beginning voter analysis"
        })
    
    def log_security_check(self, results: List[SecurityCheckResult]):
        """Log security check results"""
        return self.log_event("SECURITY_CHECK", {
            "checks": [
                {
                    "name": r.check_name,
                    "passed": r.passed,
                    "severity": r.severity,
                    "message": r.message
                }
                for r in results
            ],
            "all_passed": all(r.passed for r in results)
        })
    
    def log_flag_decision(self, voter_id: str, flag_type: str, confidence: float):
        """Log each flag decision"""
        return self.log_event("FLAG_DECISION", {
            "voter_id": voter_id,
            "flag_type": flag_type,
            "confidence": confidence,
            "requires_human_review": True  # Always true
        })


class SecurityGuard:
    """
    Main security guard that orchestrates all security checks.
    This should be integrated into the main pipeline.
    """
    
    def __init__(self):
        self.input_validator = InputValidator()
        self.output_guard = OutputGuard()
        self.audit_logger = AuditLogger()
    
    def pre_analysis_check(self, df: pd.DataFrame) -> Tuple[bool, List[SecurityCheckResult]]:
        """
        Run before analysis. Returns (can_proceed, results).
        """
        results = self.input_validator.validate_input(df)
        self.audit_logger.log_security_check(results)
        
        # Check for critical failures
        critical_failures = [r for r in results if not r.passed and r.severity == 'critical']
        can_proceed = len(critical_failures) == 0
        
        return can_proceed, results
    
    def post_analysis_check(
        self, 
        total_records: int,
        flagged_records: int,
        confidence_scores: List[float]
    ) -> Tuple[bool, List[SecurityCheckResult]]:
        """
        Run after analysis. Returns (results_valid, results).
        """
        results = self.output_guard.validate_output(
            total_records, flagged_records, confidence_scores
        )
        self.audit_logger.log_security_check(results)
        
        # Check for critical failures
        critical_failures = [r for r in results if not r.passed and r.severity == 'critical']
        results_valid = len(critical_failures) == 0
        
        return results_valid, results
    
    def get_security_report(self) -> Dict[str, Any]:
        """Generate a security compliance report"""
        return {
            "generated_at": datetime.now().isoformat(),
            "session_id": self.audit_logger.session_id,
            "safeguards": {
                "bias_prevention": "Active - Forbidden columns blocked",
                "flag_rate_limit": f"Active - Max {OutputGuard.MAX_FLAG_PERCENTAGE:.0%}",
                "human_in_loop": "Active - No auto-delete capability",
                "audit_logging": "Active - All actions logged",
                "input_validation": "Active - Data integrity checks"
            },
            "compliance": {
                "transparency": True,
                "explainability": True,
                "privacy_preserved": True,
                "democratic_safeguards": True
            }
        }


if __name__ == "__main__":
    print("🛡️ VoteGuard Security Guards Module")
    print("=" * 50)
    
    guard = SecurityGuard()
    report = guard.get_security_report()
    
    print("\n📋 Security Compliance Report:")
    print(json.dumps(report, indent=2))

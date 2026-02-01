"""
Data Preprocessor for VoteGuard
Handles data loading, cleaning, and feature engineering
"""

import pandas as pd
import numpy as np
from datetime import datetime
from typing import Tuple, Optional
import jellyfish


class VoterDataPreprocessor:
    """Preprocessor for voter registry data"""
    
    def __init__(self):
        self.current_year = datetime.now().year
        self.current_date = datetime.now()
        
    def load_data(self, filepath: str) -> pd.DataFrame:
        """Load voter data from CSV file"""
        df = pd.read_csv(filepath)
        return df
    
    def calculate_age(self, dob_str: str) -> int:
        """Calculate age from DOB string (DD-MM-YYYY format)"""
        try:
            dob = datetime.strptime(dob_str, '%d-%m-%Y')
            age = (self.current_date - dob).days // 365
            return age
        except:
            return -1  # Invalid date
    
    def normalize_name(self, name: str) -> str:
        """Normalize name for comparison (lowercase, stripped, no extra spaces)"""
        if pd.isna(name):
            return ""
        return ' '.join(str(name).lower().strip().split())
    
    def get_soundex(self, name: str) -> str:
        """Get Soundex phonetic encoding for name matching"""
        if not name or pd.isna(name):
            return ""
        try:
            return jellyfish.soundex(str(name))
        except:
            return ""
    
    def get_metaphone(self, name: str) -> str:
        """Get Metaphone phonetic encoding for name matching"""
        if not name or pd.isna(name):
            return ""
        try:
            return jellyfish.metaphone(str(name))
        except:
            return ""
    
    def _get_column(self, df: pd.DataFrame, possible_names: list, default=None):
        """Get column name case-insensitively from multiple possible names"""
        df_columns_lower = {col.lower(): col for col in df.columns}
        for name in possible_names:
            if name.lower() in df_columns_lower:
                return df_columns_lower[name.lower()]
        return default
    
    def extract_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Extract features for ML models.
        
        Handles flexible column names (case-insensitive):
        - DOB, dob, date_of_birth
        - First_Name, first_name OR name, Name
        - Last_Name, last_name
        - Registration_Year, registration_year
        - Last_Voted_Year, last_voted_year
        """
        df = df.copy()
        
        # Find column names flexibly (case-insensitive)
        dob_col = self._get_column(df, ['dob', 'DOB', 'Dob', 'date_of_birth'])
        first_name_col = self._get_column(df, ['first_name', 'First_Name', 'FirstName'])
        last_name_col = self._get_column(df, ['last_name', 'Last_Name', 'LastName'])
        name_col = self._get_column(df, ['name', 'Name', 'NAME', 'full_name'])
        reg_year_col = self._get_column(df, ['registration_year', 'Registration_Year', 'reg_year'])
        last_voted_col = self._get_column(df, ['last_voted_year', 'Last_Voted_Year', 'last_voted'])
        age_col = self._get_column(df, ['age', 'Age', 'AGE'])
        voter_id_col = self._get_column(df, ['voter_id', 'Voter_ID', 'VoterID', 'id'])
        pincode_col = self._get_column(df, ['pincode', 'Pincode', 'PINCODE', 'zip_code'])
        gender_col = self._get_column(df, ['gender', 'Gender', 'GENDER', 'sex'])
        address_col = self._get_column(df, ['address', 'Address', 'ADDRESS', 'residence'])
        
        # Helper function to safely convert to int
        def safe_int(val, default=0):
            try:
                if pd.isna(val):
                    return default
                return int(float(str(val).strip()))
            except (ValueError, TypeError):
                return default
        
        # Create standardized columns for compatibility
        # Voter ID
        if voter_id_col and voter_id_col != 'Voter_ID':
            df['Voter_ID'] = df[voter_id_col]
        
        # DOB
        if dob_col and dob_col != 'DOB':
            df['DOB'] = df[dob_col]
        
        # Pincode
        if pincode_col and pincode_col != 'Pincode':
            df['Pincode'] = df[pincode_col]

        # Gender
        if gender_col and gender_col != 'Gender':
            df['Gender'] = df[gender_col]
        
        # Address
        if address_col and address_col != 'Address':
            df['Address'] = df[address_col]
        
        # Calculate age - use Age column if exists, otherwise calculate from DOB
        if age_col:
            df['Age'] = df[age_col].apply(lambda x: safe_int(x, -1))
        elif dob_col:
            df['Age'] = df[dob_col].apply(self.calculate_age)
        else:
            df['Age'] = -1
        
        # Handle names - create First_Name, Last_Name from 'name' column if needed
        if name_col and not first_name_col:
            # Split 'name' column into First_Name and Last_Name
            def split_name(full_name):
                if pd.isna(full_name):
                    return '', ''
                parts = str(full_name).strip().split()
                if len(parts) >= 2:
                    return parts[0], ' '.join(parts[1:])
                elif len(parts) == 1:
                    return parts[0], ''
                return '', ''
            
            df['First_Name'] = df[name_col].apply(lambda x: split_name(x)[0])
            df['Last_Name'] = df[name_col].apply(lambda x: split_name(x)[1])
        else:
            # Use existing First_Name, Last_Name columns
            if first_name_col and first_name_col != 'First_Name':
                df['First_Name'] = df[first_name_col]
            if last_name_col and last_name_col != 'Last_Name':
                df['Last_Name'] = df[last_name_col]
        
        # Ensure columns exist
        if 'First_Name' not in df.columns:
            df['First_Name'] = ''
        if 'Last_Name' not in df.columns:
            df['Last_Name'] = ''
        
        # Registration Year
        if reg_year_col:
            df['Registration_Year'] = df[reg_year_col]
            df['Registration_Year_Int'] = df[reg_year_col].apply(lambda x: safe_int(x, self.current_year))
        else:
            df['Registration_Year_Int'] = self.current_year
        
        # Last Voted Year
        if last_voted_col:
            df['Last_Voted_Year'] = df[last_voted_col]
            df['Years_Since_Last_Vote'] = df[last_voted_col].apply(
                lambda x: self.current_year - safe_int(x, 0) if safe_int(x, 0) > 1900 else 999
            )
            df['Last_Voted_Int'] = df[last_voted_col].apply(lambda x: safe_int(x, 0))
        else:
            df['Years_Since_Last_Vote'] = 999
            df['Last_Voted_Int'] = 0
        
        # Years since registration
        df['Years_Since_Registration'] = self.current_year - df['Registration_Year_Int']
        
        # Normalize names for duplicate detection
        df['First_Name_Normalized'] = df['First_Name'].apply(self.normalize_name)
        df['Last_Name_Normalized'] = df['Last_Name'].apply(self.normalize_name)
        df['Full_Name_Normalized'] = df['First_Name_Normalized'] + ' ' + df['Last_Name_Normalized']
        
        # Phonetic codes for fuzzy matching
        df['First_Name_Soundex'] = df['First_Name'].apply(self.get_soundex)
        df['Last_Name_Soundex'] = df['Last_Name'].apply(self.get_soundex)
        df['First_Name_Metaphone'] = df['First_Name'].apply(self.get_metaphone)
        df['Last_Name_Metaphone'] = df['Last_Name'].apply(self.get_metaphone)
        
        # Voting activity score (0 = never voted, higher = more active)
        election_years = [2024, 2019, 2014, 2009, 2004, 1999]
        df['Voting_Activity_Score'] = df.apply(
            lambda row: self._calculate_voting_score(row, election_years), axis=1
        )
        
        # Ghost likelihood features
        df['Is_Very_Old'] = (df['Age'] > 100).astype(int)
        df['Is_Ghost_Age'] = (df['Age'] > 110).astype(int)
        df['Long_Voting_Gap'] = (df['Years_Since_Last_Vote'] > 20).astype(int)
        df['Old_Registration'] = (df['Registration_Year_Int'] < 1970).astype(int)
        
        return df
    
    def _calculate_voting_score(self, row, election_years: list) -> float:
        """Calculate voting activity score based on last voted year"""
        last_voted = row.get('Last_Voted_Int', 0)
        if last_voted == 0:
            return 0.0
        
        # Score based on recency of voting
        if last_voted >= 2024:
            return 1.0
        elif last_voted >= 2019:
            return 0.8
        elif last_voted >= 2014:
            return 0.6
        elif last_voted >= 2009:
            return 0.4
        elif last_voted >= 2004:
            return 0.2
        else:
            return 0.1
    
    def get_ghost_detection_features(self, df: pd.DataFrame) -> Tuple[pd.DataFrame, list]:
        """Get features specifically for ghost voter detection"""
        feature_cols = [
            'Age',
            'Years_Since_Registration',
            'Years_Since_Last_Vote',
            'Voting_Activity_Score',
            'Is_Very_Old',
            'Long_Voting_Gap',
            'Old_Registration'
        ]
        
        # Replace infinite values
        features_df = df[feature_cols].copy()
        features_df = features_df.replace([np.inf, -np.inf], 999)
        features_df = features_df.fillna(0)
        
        return features_df, feature_cols
    
    def get_duplicate_detection_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Get features for duplicate voter detection"""
        return df[[
            'Voter_ID',
            'First_Name_Normalized',
            'Last_Name_Normalized',
            'Full_Name_Normalized',
            'DOB',
            'Pincode',
            'First_Name_Soundex',
            'Last_Name_Soundex',
            'First_Name_Metaphone',
            'Last_Name_Metaphone',
            'Masked_Aadhaar'
        ]].copy()


if __name__ == "__main__":
    # Test the preprocessor
    preprocessor = VoterDataPreprocessor()
    df = preprocessor.load_data("voter_data.csv")
    df = preprocessor.extract_features(df)
    
    print(f"Loaded {len(df)} records")
    print(f"Age range: {df['Age'].min()} - {df['Age'].max()}")
    print(f"Ghost age records (>110): {df['Is_Ghost_Age'].sum()}")
    print("\nSample features:")
    print(df[['Voter_ID', 'Full_Name_Normalized', 'Age', 'Is_Ghost_Age']].head())

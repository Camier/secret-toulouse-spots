#!/usr/bin/env python3
"""
Data Standardization Pipeline for Secret Spots
Normalizes, deduplicates, and enriches spot data
"""

import sqlite3
import json
import re
from datetime import datetime
from typing import Dict, List, Tuple, Optional
import unicodedata

class SpotStandardizer:
    def __init__(self, db_path='hidden_spots.db'):
        self.conn = sqlite3.connect(db_path)
        self.cursor = self.conn.cursor()
        
        # Standard spot types
        self.SPOT_TYPES = {
            'water': ['baignade', 'cascade', 'lac', 'rivière', 'source', 'piscine', 'plage', 'gorge'],
            'urbex': ['abandonné', 'friche', 'usine', 'urbex', 'ruine', 'château'],
            'nature': ['forêt', 'bois', 'grotte', 'caverne', 'montagne', 'colline'],
            'viewpoint': ['vue', 'panorama', 'belvédère', 'point de vue', 'sommet'],
            'historic': ['château', 'église', 'abbaye', 'moulin', 'pont', 'tour'],
            'recreation': ['pique-nique', 'camping', 'randonnée', 'vtt', 'escalade']
        }
        
        # Activity mappings
        self.ACTIVITY_MAPPING = {
            'baignade': ['swim', 'nager', 'plage', 'piscine'],
            'randonnée': ['hike', 'trek', 'marche', 'walking', 'promenade'],
            'escalade': ['climb', 'grimpe', 'varappe'],
            'VTT': ['bike', 'vélo', 'cyclisme', 'mountain bike'],
            'kayak': ['canoe', 'paddle', 'raft', 'nautique'],
            'pêche': ['fish', 'fishing', 'truite'],
            'camping': ['bivouac', 'tente', 'camp'],
            'photo': ['photography', 'photographe', 'instagram'],
            'pique-nique': ['picnic', 'bbq', 'barbecue']
        }

    def normalize_name(self, name: str) -> str:
        """Normalize spot names"""
        if not name:
            return "Spot Inconnu"
        
        # Remove extra whitespace
        name = ' '.join(name.split())
        
        # Remove common prefixes
        prefixes = ['Unknown', 'Spot de', 'Lieu de', 'Site de']
        for prefix in prefixes:
            if name.startswith(prefix):
                name = name[len(prefix):].strip()
        
        # Capitalize properly
        words = name.split()
        normalized = []
        for word in words:
            if word.lower() in ['de', 'du', 'des', 'la', 'le', 'les']:
                normalized.append(word.lower())
            else:
                normalized.append(word.capitalize())
        
        return ' '.join(normalized)

    def determine_spot_type(self, name: str, text: str, activities: str) -> str:
        """Determine the primary type of spot"""
        combined_text = f"{name} {text} {activities}".lower()
        
        type_scores = {}
        for spot_type, keywords in self.SPOT_TYPES.items():
            score = sum(1 for keyword in keywords if keyword in combined_text)
            if score > 0:
                type_scores[spot_type] = score
        
        if type_scores:
            return max(type_scores, key=type_scores.get)
        return 'other'

    def standardize_activities(self, activities: str) -> str:
        """Standardize activity descriptions"""
        if not activities:
            return None
        
        activities_lower = activities.lower()
        found_activities = set()
        
        for standard_activity, variations in self.ACTIVITY_MAPPING.items():
            if standard_activity in activities_lower:
                found_activities.add(standard_activity)
            else:
                for variation in variations:
                    if variation in activities_lower:
                        found_activities.add(standard_activity)
                        break
        
        return ', '.join(sorted(found_activities)) if found_activities else activities

    def calculate_confidence_score(self, spot: Dict) -> float:
        """Calculate data quality confidence score (0-1)"""
        score = 0.0
        
        # Has coordinates: +0.3
        if spot.get('latitude') and spot.get('longitude'):
            score += 0.3
        
        # Has proper name: +0.2
        if spot.get('extracted_name') and spot['extracted_name'] != 'Unknown':
            score += 0.2
        
        # Has activities: +0.1
        if spot.get('activities'):
            score += 0.1
        
        # Has description: +0.2
        if spot.get('raw_text') and len(spot['raw_text']) > 50:
            score += 0.2
        
        # Is verified/hidden: +0.1
        if spot.get('is_hidden'):
            score += 0.1
        
        # Has source URL: +0.1
        if spot.get('source_url') and spot['source_url'] != 'manual_entry':
            score += 0.1
        
        return min(score, 1.0)

    def find_duplicates(self) -> List[Tuple]:
        """Find potential duplicate spots"""
        # Get all spots
        self.cursor.execute('''
            SELECT id, extracted_name, latitude, longitude, source
            FROM spots
            ORDER BY extracted_name
        ''')
        spots = self.cursor.fetchall()
        
        duplicates = []
        
        for i, spot1 in enumerate(spots):
            for spot2 in spots[i+1:]:
                # Check name similarity
                if spot1[1] and spot2[1]:
                    name1 = self.normalize_name(spot1[1]).lower()
                    name2 = self.normalize_name(spot2[1]).lower()
                    
                    # Exact name match
                    if name1 == name2:
                        duplicates.append((spot1[0], spot2[0], 'exact_name'))
                        continue
                    
                    # Similar names
                    if self.similar_names(name1, name2):
                        duplicates.append((spot1[0], spot2[0], 'similar_name'))
                
                # Check coordinate proximity
                if spot1[2] and spot1[3] and spot2[2] and spot2[3]:
                    distance = self.calculate_distance(
                        spot1[2], spot1[3], spot2[2], spot2[3]
                    )
                    if distance < 0.1:  # Less than 100m
                        duplicates.append((spot1[0], spot2[0], 'same_location'))
        
        return duplicates

    def similar_names(self, name1: str, name2: str) -> bool:
        """Check if two names are similar"""
        # Remove accents
        name1 = unicodedata.normalize('NFD', name1)
        name1 = ''.join(char for char in name1 if unicodedata.category(char) != 'Mn')
        name2 = unicodedata.normalize('NFD', name2)
        name2 = ''.join(char for char in name2 if unicodedata.category(char) != 'Mn')
        
        # Check if one contains the other
        if name1 in name2 or name2 in name1:
            return True
        
        # Check Levenshtein distance (simple version)
        if len(name1) > 5 and len(name2) > 5:
            common_chars = sum(1 for c1, c2 in zip(name1, name2) if c1 == c2)
            if common_chars / max(len(name1), len(name2)) > 0.8:
                return True
        
        return False

    def calculate_distance(self, lat1, lon1, lat2, lon2):
        """Calculate distance in km"""
        from math import radians, sin, cos, sqrt, atan2
        R = 6371
        dlat = radians(lat2 - lat1)
        dlon = radians(lon2 - lon1)
        a = sin(dlat/2)**2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon/2)**2
        c = 2 * atan2(sqrt(a), sqrt(1-a))
        return R * c

    def merge_duplicates(self, id1: int, id2: int):
        """Merge two duplicate spots, keeping the best data"""
        # Get both spots
        self.cursor.execute('SELECT * FROM spots WHERE id IN (?, ?)', (id1, id2))
        spots = self.cursor.fetchall()
        
        if len(spots) != 2:
            return
        
        # Convert to dicts
        columns = [desc[0] for desc in self.cursor.description]
        spot1 = dict(zip(columns, spots[0]))
        spot2 = dict(zip(columns, spots[1]))
        
        # Determine which has better data
        score1 = self.calculate_confidence_score(spot1)
        score2 = self.calculate_confidence_score(spot2)
        
        if score1 >= score2:
            keep, merge = spot1, spot2
            keep_id, merge_id = id1, id2
        else:
            keep, merge = spot2, spot1
            keep_id, merge_id = id2, id1
        
        # Merge data (fill missing fields)
        for field in columns:
            if not keep.get(field) and merge.get(field):
                keep[field] = merge[field]
        
        # Update the kept record
        self.cursor.execute('''
            UPDATE spots SET
                extracted_name = ?,
                latitude = ?,
                longitude = ?,
                activities = ?,
                raw_text = ?
            WHERE id = ?
        ''', (
            keep['extracted_name'],
            keep['latitude'],
            keep['longitude'],
            keep['activities'],
            keep['raw_text'],
            keep_id
        ))
        
        # Delete the merged record
        self.cursor.execute('DELETE FROM spots WHERE id = ?', (merge_id,))

    def standardize_all(self):
        """Run full standardization pipeline"""
        print("🔧 Starting data standardization...")
        
        # Get all spots
        self.cursor.execute('SELECT * FROM spots')
        columns = [desc[0] for desc in self.cursor.description]
        spots = [dict(zip(columns, row)) for row in self.cursor.fetchall()]
        
        print(f"📊 Processing {len(spots)} spots...")
        
        # Standardize each spot
        for spot in spots:
            # Normalize name
            normalized_name = self.normalize_name(spot['extracted_name'])
            
            # Determine spot type
            spot_type = self.determine_spot_type(
                spot['extracted_name'] or '',
                spot['raw_text'] or '',
                spot['activities'] or ''
            )
            
            # Standardize activities
            std_activities = self.standardize_activities(spot['activities'])
            
            # Calculate confidence
            confidence = self.calculate_confidence_score(spot)
            
            # Update database
            self.cursor.execute('''
                UPDATE spots SET
                    extracted_name = ?,
                    location_type = ?,
                    activities = ?,
                    metadata = ?
                WHERE id = ?
            ''', (
                normalized_name,
                spot_type,
                std_activities,
                json.dumps({
                    'confidence_score': confidence,
                    'original_name': spot['extracted_name'],
                    'standardized': True,
                    'standardized_at': datetime.now().isoformat()
                }),
                spot['id']
            ))
        
        self.conn.commit()
        print(f"✅ Standardized {len(spots)} spots")
        
        # Find and handle duplicates
        print("\n🔍 Finding duplicates...")
        duplicates = self.find_duplicates()
        
        if duplicates:
            print(f"⚠️  Found {len(duplicates)} potential duplicates")
            
            # Group duplicates
            dup_groups = {}
            for id1, id2, reason in duplicates:
                if id1 not in dup_groups:
                    dup_groups[id1] = []
                dup_groups[id1].append((id2, reason))
            
            # Show examples
            print("\nExample duplicates:")
            for main_id, dups in list(dup_groups.items())[:5]:
                self.cursor.execute('SELECT extracted_name FROM spots WHERE id = ?', (main_id,))
                main_name = self.cursor.fetchone()[0]
                print(f"\n  '{main_name}' (ID: {main_id})")
                for dup_id, reason in dups:
                    self.cursor.execute('SELECT extracted_name FROM spots WHERE id = ?', (dup_id,))
                    dup_name = self.cursor.fetchone()[0]
                    print(f"    → '{dup_name}' (ID: {dup_id}, reason: {reason})")
        
        # Generate report
        self.generate_report()

    def generate_report(self):
        """Generate standardization report"""
        # Statistics
        self.cursor.execute('SELECT COUNT(*) FROM spots')
        total = self.cursor.fetchone()[0]
        
        self.cursor.execute('SELECT COUNT(*) FROM spots WHERE latitude IS NOT NULL')
        with_coords = self.cursor.fetchone()[0]
        
        self.cursor.execute('SELECT location_type, COUNT(*) FROM spots GROUP BY location_type')
        type_counts = self.cursor.fetchall()
        
        self.cursor.execute('SELECT source, COUNT(*) FROM spots GROUP BY source')
        source_counts = self.cursor.fetchall()
        
        report = {
            'timestamp': datetime.now().isoformat(),
            'total_spots': total,
            'with_coordinates': with_coords,
            'without_coordinates': total - with_coords,
            'by_type': dict(type_counts),
            'by_source': dict(source_counts),
            'standardization_complete': True
        }
        
        with open('standardization_report.json', 'w') as f:
            json.dump(report, f, indent=2)
        
        print(f"\n📊 Standardization Report:")
        print(f"   Total spots: {total}")
        print(f"   With coordinates: {with_coords} ({with_coords/total*100:.1f}%)")
        print(f"   Without coordinates: {total - with_coords}")
        print(f"\n   By type:")
        for spot_type, count in type_counts:
            print(f"     {spot_type}: {count}")

def main():
    standardizer = SpotStandardizer()
    standardizer.standardize_all()
    standardizer.conn.close()

if __name__ == "__main__":
    main()
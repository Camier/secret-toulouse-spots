#!/usr/bin/env python3
"""
NLP Pipeline for French Location Extraction
Uses spaCy with French language model for entity recognition and custom patterns
"""

import json
import logging
import re
from typing import List, Dict, Tuple, Set, Optional
from collections import defaultdict

import spacy
from spacy.matcher import Matcher, PhraseMatcher
from spacy.tokens import Doc, Span
import pandas as pd


logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class FrenchLocationExtractor:
    """NLP pipeline for extracting French outdoor locations from text"""
    
    def __init__(self, model_name: str = "fr_core_news_lg"):
        """Initialize with French spaCy model"""
        try:
            self.nlp = spacy.load(model_name)
        except:
            logger.error(f"Model {model_name} not found. Installing...")
            import subprocess
            subprocess.run([sys.executable, "-m", "spacy", "download", model_name])
            self.nlp = spacy.load(model_name)
        
        # Add custom pipeline components
        self.matcher = Matcher(self.nlp.vocab)
        self.phrase_matcher = PhraseMatcher(self.nlp.vocab)
        
        # Initialize patterns
        self._setup_location_patterns()
        self._setup_french_geography()
        
        # Statistics
        self.stats = {
            'texts_processed': 0,
            'locations_extracted': 0,
            'entities_recognized': 0
        }
        
        # Track extracted locations for statistics
        self.extracted_locations = []
    
    def _setup_location_patterns(self):
        """Setup custom patterns for French outdoor locations"""
        
        # Pattern 1: Natural features with proper names
        patterns = [
            # Cascade/Waterfall patterns
            [{"LOWER": {"IN": ["cascade", "cascades", "chute", "chutes"]}}, 
             {"LOWER": {"IN": ["de", "du", "des", "d'"]}}, 
             {"POS": "PROPN", "OP": "+"}],
            
            # Lake patterns  
            [{"LOWER": {"IN": ["lac", "lacs", "étang", "étangs"]}},
             {"LOWER": {"IN": ["de", "du", "des", "d'"]}},
             {"POS": "PROPN", "OP": "+"}],
            
            # Spring patterns
            [{"LOWER": {"IN": ["source", "sources", "résurgence", "fontaine"]}},
             {"LOWER": {"IN": ["de", "du", "des", "d'"]}},
             {"POS": "PROPN", "OP": "+"}],
            
            # Cave patterns
            [{"LOWER": {"IN": ["grotte", "grottes", "caverne", "gouffre", "aven"]}},
             {"LOWER": {"IN": ["de", "du", "des", "d'"]}},
             {"POS": "PROPN", "OP": "+"}],
            
            # Mountain features
            [{"LOWER": {"IN": ["col", "pic", "mont", "sommet", "crête", "aiguille"]}},
             {"LOWER": {"IN": ["de", "du", "des", "d'"]}, "OP": "?"},
             {"POS": "PROPN", "OP": "+"}],
            
            # Valley/Gorge patterns
            [{"LOWER": {"IN": ["gorge", "gorges", "vallée", "vallon", "ravin"]}},
             {"LOWER": {"IN": ["de", "du", "des", "d'"]}},
             {"POS": "PROPN", "OP": "+"}],
            
            # Beach/Coast patterns
            [{"LOWER": {"IN": ["plage", "calanque", "crique", "anse", "baie"]}},
             {"LOWER": {"IN": ["de", "du", "des", "d'"]}},
             {"POS": "PROPN", "OP": "+"}]
        ]
        
        # Pattern 2: Location indicators
        location_indicators = [
            # Near/Close to patterns
            [{"LOWER": {"IN": ["près", "proche"]}},
             {"LOWER": "de"},
             {"POS": "PROPN", "OP": "+"}],
            
            [{"LOWER": {"IN": ["à", "au", "aux"]}},
             {"IS_DIGIT": True, "OP": "?"},
             {"LOWER": {"IN": ["km", "kilomètres", "mètres", "m"]}, "OP": "?"},
             {"LOWER": {"IN": ["de", "du", "des"]}, "OP": "?"},
             {"POS": "PROPN", "OP": "+"}],
            
            # Direction patterns
            [{"LOWER": {"IN": ["nord", "sud", "est", "ouest"]}},
             {"LOWER": {"IN": ["de", "du"]}},
             {"POS": "PROPN", "OP": "+"}],
            
            # Between patterns
            [{"LOWER": "entre"},
             {"POS": "PROPN", "OP": "+"},
             {"LOWER": "et"},
             {"POS": "PROPN", "OP": "+"}]
        ]
        
        # Pattern 3: Activity locations
        activity_patterns = [
            # Swimming spots
            [{"LOWER": {"IN": ["baignade", "piscine"]}},
             {"LOWER": {"IN": ["naturelle", "sauvage"]}, "OP": "?"},
             {"LOWER": {"IN": ["à", "de", "du"]}},
             {"POS": "PROPN", "OP": "+"}],
            
            # Hiking trails
            [{"LOWER": {"IN": ["sentier", "chemin", "gr"]}},
             {"LOWER": {"IN": ["de", "du", "des"]}},
             {"POS": "PROPN", "OP": "+"}],
            
            # Climbing spots
            [{"LOWER": {"IN": ["site", "spot", "falaise", "voie"]}},
             {"LOWER": {"IN": ["d'escalade", "de", "du"]}},
             {"POS": "PROPN", "OP": "+"}]
        ]
        
        # Add all patterns
        for i, pattern in enumerate(patterns + location_indicators + activity_patterns):
            self.matcher.add(f"LOCATION_PATTERN_{i}", [pattern])
    
    def _setup_french_geography(self):
        """Setup French geographical knowledge base"""
        
        # French regions
        self.regions = {
            "Auvergne-Rhône-Alpes", "Bourgogne-Franche-Comté", "Bretagne",
            "Centre-Val de Loire", "Corse", "Grand Est", "Hauts-de-France",
            "Île-de-France", "Normandie", "Nouvelle-Aquitaine", "Occitanie",
            "Pays de la Loire", "Provence-Alpes-Côte d'Azur", "PACA"
        }
        
        # French departments
        self.departments = {
            "Ain", "Aisne", "Allier", "Alpes-de-Haute-Provence", "Hautes-Alpes",
            "Alpes-Maritimes", "Ardèche", "Ardennes", "Ariège", "Aube", "Aude",
            "Aveyron", "Bouches-du-Rhône", "Calvados", "Cantal", "Charente",
            "Charente-Maritime", "Cher", "Corrèze", "Corse-du-Sud", "Haute-Corse",
            "Côte-d'Or", "Côtes-d'Armor", "Creuse", "Dordogne", "Doubs", "Drôme",
            "Eure", "Eure-et-Loir", "Finistère", "Gard", "Haute-Garonne", "Gers",
            "Gironde", "Hérault", "Ille-et-Vilaine", "Indre", "Indre-et-Loire",
            "Isère", "Jura", "Landes", "Loir-et-Cher", "Loire", "Haute-Loire",
            "Loire-Atlantique", "Loiret", "Lot", "Lot-et-Garonne", "Lozère",
            "Maine-et-Loire", "Manche", "Marne", "Haute-Marne", "Mayenne",
            "Meurthe-et-Moselle", "Meuse", "Morbihan", "Moselle", "Nièvre",
            "Nord", "Oise", "Orne", "Pas-de-Calais", "Puy-de-Dôme",
            "Pyrénées-Atlantiques", "Hautes-Pyrénées", "Pyrénées-Orientales",
            "Bas-Rhin", "Haut-Rhin", "Rhône", "Haute-Saône", "Saône-et-Loire",
            "Sarthe", "Savoie", "Haute-Savoie", "Paris", "Seine-Maritime",
            "Seine-et-Marne", "Yvelines", "Deux-Sèvres", "Somme", "Tarn",
            "Tarn-et-Garonne", "Var", "Vaucluse", "Vendée", "Vienne",
            "Haute-Vienne", "Vosges", "Yonne", "Territoire de Belfort",
            "Essonne", "Hauts-de-Seine", "Seine-Saint-Denis", "Val-de-Marne",
            "Val-d'Oise", "Guadeloupe", "Martinique", "Guyane", "La Réunion",
            "Mayotte"
        }
        
        # Mountain ranges
        self.mountain_ranges = {
            "Alpes", "Pyrénées", "Massif Central", "Vosges", "Jura",
            "Morvan", "Ardennes", "Cévennes", "Corbières", "Alpilles"
        }
        
        # Natural parks
        self.natural_parks = {
            "Vanoise", "Écrins", "Mercantour", "Queyras", "Chartreuse",
            "Vercors", "Bauges", "Pilat", "Pyrénées", "Cévennes",
            "Morvan", "Ballons des Vosges", "Camargue", "Luberon",
            "Verdon", "Calanques", "Port-Cros", "Porquerolles"
        }
        
        # Add phrase patterns for known geographical entities
        region_patterns = [self.nlp(region) for region in self.regions]
        dept_patterns = [self.nlp(dept) for dept in self.departments]
        mountain_patterns = [self.nlp(mountain) for mountain in self.mountain_ranges]
        park_patterns = [self.nlp(park) for park in self.natural_parks]
        
        self.phrase_matcher.add("REGION", region_patterns)
        self.phrase_matcher.add("DEPARTMENT", dept_patterns)
        self.phrase_matcher.add("MOUNTAIN_RANGE", mountain_patterns)
        self.phrase_matcher.add("NATURAL_PARK", park_patterns)
    
    def extract_locations(self, text: str) -> List[Dict]:
        """Extract locations from French text"""
        doc = self.nlp(text)
        locations = []
        seen_locations = set()
        
        # Extract named entities
        for ent in doc.ents:
            if ent.label_ in ["LOC", "GPE"]:  # Location or Geopolitical entity
                loc_text = ent.text.strip()
                if loc_text and loc_text not in seen_locations:
                    locations.append({
                        'text': loc_text,
                        'type': 'named_entity',
                        'label': ent.label_,
                        'start': ent.start_char,
                        'end': ent.end_char,
                        'context': self._get_context(doc, ent.start, ent.end)
                    })
                    seen_locations.add(loc_text)
                    self.stats['entities_recognized'] += 1
        
        # Extract pattern matches
        matches = self.matcher(doc)
        for match_id, start, end in matches:
            span = doc[start:end]
            loc_text = span.text.strip()
            if loc_text and loc_text not in seen_locations:
                locations.append({
                    'text': loc_text,
                    'type': 'pattern_match',
                    'pattern': self.nlp.vocab.strings[match_id],
                    'start': span.start_char,
                    'end': span.end_char,
                    'context': self._get_context(doc, start, end)
                })
                seen_locations.add(loc_text)
        
        # Extract phrase matches (known geographical entities)
        phrase_matches = self.phrase_matcher(doc)
        for match_id, start, end in phrase_matches:
            span = doc[start:end]
            loc_text = span.text.strip()
            if loc_text and loc_text not in seen_locations:
                locations.append({
                    'text': loc_text,
                    'type': 'known_geography',
                    'category': self.nlp.vocab.strings[match_id],
                    'start': span.start_char,
                    'end': span.end_char,
                    'context': self._get_context(doc, start, end)
                })
                seen_locations.add(loc_text)
        
        # Post-process locations
        locations = self._postprocess_locations(locations, doc)
        
        self.stats['texts_processed'] += 1
        self.stats['locations_extracted'] += len(locations)
        
        # Track for statistics
        self.extracted_locations.extend(locations)
        
        return locations
    
    def _get_context(self, doc: Doc, start: int, end: int, window: int = 10) -> str:
        """Get context around a span"""
        context_start = max(0, start - window)
        context_end = min(len(doc), end + window)
        return doc[context_start:context_end].text
    
    def _postprocess_locations(self, locations: List[Dict], doc: Doc) -> List[Dict]:
        """Post-process extracted locations"""
        processed = []
        
        for loc in locations:
            # Clean location text
            loc['text'] = self._clean_location_text(loc['text'])
            
            # Skip if too short or invalid
            if len(loc['text']) < 3 or self._is_invalid_location(loc['text']):
                continue
            
            # Add geographical classification
            loc['geo_classification'] = self._classify_location(loc['text'])
            
            # Add activity type if detected
            loc['activity_type'] = self._detect_activity_type(loc['context'])
            
            # Check if it's a hidden spot
            loc['is_hidden'] = self._is_hidden_spot(doc.text, loc['start'], loc['end'])
            
            processed.append(loc)
        
        return processed
    
    def _clean_location_text(self, text: str) -> str:
        """Clean and normalize location text"""
        # Remove extra spaces
        text = ' '.join(text.split())
        
        # Remove trailing prepositions
        text = re.sub(r'\s+(de|du|des|d\')\s*$', '', text, flags=re.IGNORECASE)
        
        # Capitalize properly
        words = text.split()
        cleaned = []
        for word in words:
            if word.lower() in ['de', 'du', 'des', 'la', 'le', 'les']:
                cleaned.append(word.lower())
            else:
                cleaned.append(word.capitalize())
        
        return ' '.join(cleaned)
    
    def _is_invalid_location(self, text: str) -> bool:
        """Check if location text is invalid"""
        invalid_terms = {
            'ici', 'là', 'là-bas', 'endroit', 'lieu', 'place',
            'coin', 'spot', 'site', 'zone', 'secteur', 'région'
        }
        
        return text.lower() in invalid_terms or len(text) < 3
    
    def _classify_location(self, text: str) -> str:
        """Classify location type"""
        text_lower = text.lower()
        
        if any(region.lower() in text_lower for region in self.regions):
            return 'region'
        elif any(dept.lower() in text_lower for dept in self.departments):
            return 'department'
        elif any(mountain.lower() in text_lower for mountain in self.mountain_ranges):
            return 'mountain_range'
        elif any(park.lower() in text_lower for park in self.natural_parks):
            return 'natural_park'
        elif any(word in text_lower for word in ['cascade', 'chute']):
            return 'waterfall'
        elif any(word in text_lower for word in ['lac', 'étang']):
            return 'lake'
        elif any(word in text_lower for word in ['source', 'résurgence']):
            return 'spring'
        elif any(word in text_lower for word in ['grotte', 'caverne', 'gouffre']):
            return 'cave'
        elif any(word in text_lower for word in ['col', 'pic', 'mont', 'sommet']):
            return 'mountain_feature'
        elif any(word in text_lower for word in ['plage', 'calanque', 'crique']):
            return 'coastal_feature'
        else:
            return 'other'
    
    def _detect_activity_type(self, context: str) -> Optional[str]:
        """Detect activity type from context"""
        context_lower = context.lower()
        
        activity_keywords = {
            'baignade': ['baignade', 'nager', 'se baigner', 'piscine naturelle'],
            'randonnee': ['randonnée', 'marche', 'sentier', 'trek', 'gr'],
            'escalade': ['escalade', 'grimpe', 'voie', 'bloc'],
            'vtt': ['vtt', 'vélo', 'cyclisme', 'bike'],
            'kayak': ['kayak', 'canoë', 'pagayer', 'descente'],
            'canyoning': ['canyoning', 'canyon', 'rappel'],
            'ski': ['ski', 'neige', 'poudreuse'],
            'bivouac': ['bivouac', 'camping', 'nuit', 'dormir']
        }
        
        for activity, keywords in activity_keywords.items():
            if any(kw in context_lower for kw in keywords):
                return activity
        
        return None
    
    def _is_hidden_spot(self, full_text: str, start: int, end: int, window: int = 200) -> bool:
        """Check if location is described as hidden"""
        # Get wider context
        context_start = max(0, start - window)
        context_end = min(len(full_text), end + window)
        context = full_text[context_start:context_end].lower()
        
        hidden_keywords = [
            'secret', 'caché', 'peu connu', 'méconnu',
            'hors des sentiers battus', 'confidentiel',
            'pas touristique', 'préservé', 'sauvage',
            'difficile à trouver', 'pas indiqué'
        ]
        
        return any(keyword in context for keyword in hidden_keywords)
    
    def process_scraped_data(self, scraped_data: Dict) -> List[Dict]:
        """Process scraped data to extract locations"""
        all_locations = []
        
        # Process forum posts
        if 'data' in scraped_data:
            for post in scraped_data['data']:
                if 'text' in post:
                    locations = self.extract_locations(post['text'])
                    for loc in locations:
                        loc['source'] = post.get('url', 'forum')
                        loc['source_date'] = post.get('scraped_at')
                        all_locations.append(loc)
        
        # Process Instagram posts
        if 'posts' in scraped_data:
            for post in scraped_data['posts']:
                if 'caption' in post and post['caption']:
                    locations = self.extract_locations(post['caption'])
                    for loc in locations:
                        loc['source'] = post.get('url', 'instagram')
                        loc['source_date'] = post.get('date')
                        loc['instagram_location'] = post.get('location')
                        all_locations.append(loc)
        
        return all_locations
    
    def get_statistics(self) -> Dict:
        """Get extraction statistics"""
        return {
            **self.stats,
            'unique_locations': len(set(loc['text'] for loc in self.extracted_locations)),
            'hidden_spots': sum(1 for loc in self.extracted_locations if loc.get('is_hidden', False))
        }


def main():
    """Main execution function"""
    extractor = FrenchLocationExtractor()
    
    # Example texts
    test_texts = [
        "Nous avons découvert une cascade cachée près de Mende, dans les Cévennes. C'est un endroit secret que peu de gens connaissent.",
        "La piscine naturelle du Pont du Diable à Saint-Jean-de-Fos est parfaite pour la baignade sauvage.",
        "Entre Grenoble et Chambéry, il y a un lac de montagne peu connu, idéal pour le bivouac.",
        "Les gorges du Verdon offrent des spots d'escalade incroyables, notamment près de La Palud-sur-Verdon."
    ]
    
    print("Testing NLP Location Extraction:\n")
    
    for text in test_texts:
        print(f"Text: {text}")
        locations = extractor.extract_locations(text)
        print(f"Extracted locations: {len(locations)}")
        for loc in locations:
            print(f"  - {loc['text']} ({loc['type']}, {loc.get('geo_classification', 'unknown')})")
            if loc.get('is_hidden'):
                print("    [HIDDEN SPOT]")
        print()
    
    # Process scraped data files if they exist
    import os
    if os.path.exists('scraped_data/forum_hidden_spots.json'):
        with open('scraped_data/forum_hidden_spots.json', 'r', encoding='utf-8') as f:
            forum_data = json.load(f)
        
        forum_locations = extractor.process_scraped_data(forum_data)
        print(f"\nExtracted {len(forum_locations)} locations from forum data")
    
    print("\nExtraction Statistics:")
    stats = extractor.get_statistics()
    for key, value in stats.items():
        print(f"  {key}: {value}")


if __name__ == "__main__":
    main()
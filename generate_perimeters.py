#!/usr/bin/env python3
"""
Generate plausible perimeters for spots without coordinates
Based on location mentions in descriptions
"""

import json
import re
from typing import Dict, Optional

# Known locations with approximate coordinates and radius
KNOWN_LOCATIONS = {
    # Major cities/towns
    "toulouse": {"lat": 43.6047, "lon": 1.4442, "radius": 20000},  # 20km
    "albi": {"lat": 43.9298, "lon": 2.1480, "radius": 15000},
    "castres": {"lat": 43.6060, "lon": 2.2400, "radius": 10000},
    "montauban": {"lat": 44.0221, "lon": 1.3529, "radius": 12000},
    "carcassonne": {"lat": 43.2130, "lon": 2.3491, "radius": 15000},
    "foix": {"lat": 42.9660, "lon": 1.6055, "radius": 10000},
    "pamiers": {"lat": 43.1152, "lon": 1.6112, "radius": 8000},
    # Smaller towns mentioned in data
    "cordes-sur-ciel": {"lat": 44.0639, "lon": 1.9530, "radius": 5000},
    "saint-antonin-noble-val": {"lat": 44.1519, "lon": 1.7560, "radius": 8000},
    "gaillac": {"lat": 43.9014, "lon": 1.8956, "radius": 8000},
    "moissac": {"lat": 44.1047, "lon": 1.0851, "radius": 7000},
    "cahors": {"lat": 44.4477, "lon": 1.4414, "radius": 10000},
    # Natural areas
    "pyrenees": {"lat": 42.8, "lon": 0.5, "radius": 50000},
    "pyrénées": {"lat": 42.8, "lon": 0.5, "radius": 50000},
    "montagne noire": {"lat": 43.4, "lon": 2.3, "radius": 30000},
    "lauragais": {"lat": 43.4, "lon": 1.8, "radius": 25000},
    # Rivers
    "garonne": {"lat": 43.5, "lon": 1.4, "radius": 20000},
    "tarn": {"lat": 43.8, "lon": 1.7, "radius": 15000},
    "ariège": {"lat": 43.3, "lon": 1.5, "radius": 15000},
    "aveyron": {"lat": 44.1, "lon": 1.8, "radius": 15000},
}

# Distance-based radius for less specific mentions
DISTANCE_RADIUS = {
    r"(\d+)\s*km": lambda x: int(x) * 1000,  # Convert km to meters
    r"quelques\s*kilomètres": 5000,  # "a few kilometers"
    r"proche": 10000,  # "near"
    r"environs": 15000,  # "surroundings"
    r"région": 30000,  # "region"
}


def extract_location_info(text: str) -> Optional[Dict]:
    """Extract location information from text"""
    if not text:
        return None

    text_lower = text.lower()

    # Check for known locations
    for location, coords in KNOWN_LOCATIONS.items():
        if location in text_lower:
            # Check for distance modifiers
            for pattern, radius in DISTANCE_RADIUS.items():
                if isinstance(radius, int):
                    if re.search(pattern, text_lower):
                        return {
                            "center_lat": coords["lat"],
                            "center_lon": coords["lon"],
                            "radius": radius,
                            "confidence": "medium",
                            "reference": f"Near {location}",
                        }
                else:
                    match = re.search(pattern, text_lower)
                    if match:
                        return {
                            "center_lat": coords["lat"],
                            "center_lon": coords["lon"],
                            "radius": radius(match.group(1)),
                            "confidence": "high",
                            "reference": f"{match.group(0)} from {location}",
                        }

            # Default radius for the location
            return {
                "center_lat": coords["lat"],
                "center_lon": coords["lon"],
                "radius": coords["radius"],
                "confidence": "low",
                "reference": f"General area of {location}",
            }

    # Check for department numbers
    dept_match = re.search(r"\b(31|81|82|09|11|12|32|46|65|66)\b", text)
    if dept_match:
        dept = dept_match.group(1)
        dept_centers = {
            "31": {"lat": 43.6, "lon": 1.4, "name": "Haute-Garonne"},
            "81": {"lat": 43.9, "lon": 2.1, "name": "Tarn"},
            "82": {"lat": 44.0, "lon": 1.3, "name": "Tarn-et-Garonne"},
            "09": {"lat": 42.9, "lon": 1.5, "name": "Ariège"},
            "11": {"lat": 43.2, "lon": 2.3, "name": "Aude"},
            "12": {"lat": 44.3, "lon": 2.5, "name": "Aveyron"},
            "32": {"lat": 43.6, "lon": 0.5, "name": "Gers"},
            "46": {"lat": 44.6, "lon": 1.6, "name": "Lot"},
            "65": {"lat": 43.0, "lon": 0.1, "name": "Hautes-Pyrénées"},
            "66": {"lat": 42.6, "lon": 2.8, "name": "Pyrénées-Orientales"},
        }
        if dept in dept_centers:
            return {
                "center_lat": dept_centers[dept]["lat"],
                "center_lon": dept_centers[dept]["lon"],
                "radius": 40000,  # 40km for department
                "confidence": "low",
                "reference": f"Department {dept} - {dept_centers[dept]['name']}",
            }

    return None


def process_spots():
    """Process spots and generate perimeters"""
    # Load existing spots
    with open("hidden_spots_export.json", "r", encoding="utf-8") as f:
        spots = json.load(f)

    # Process each spot
    enhanced_spots = []
    stats = {
        "total": len(spots),
        "with_coords": 0,
        "with_perimeter": 0,
        "no_location": 0,
    }

    for spot in spots:
        if spot.get("latitude") and spot.get("longitude"):
            # Spot has exact coordinates
            spot["location_type"] = "exact"
            spot["perimeter"] = None
            stats["with_coords"] += 1
        else:
            # Try to extract location info
            location_info = None

            # Check various text fields
            for field in ["extracted_name", "raw_text", "activities"]:
                if spot.get(field):
                    location_info = extract_location_info(spot.get(field))
                    if location_info:
                        break

            if location_info:
                spot["location_type"] = "perimeter"
                spot["perimeter"] = location_info
                stats["with_perimeter"] += 1
            else:
                spot["location_type"] = "unknown"
                spot["perimeter"] = None
                stats["no_location"] += 1

        enhanced_spots.append(spot)

    # Save enhanced spots
    with open("enhanced_spots_with_perimeters.json", "w", encoding="utf-8") as f:
        json.dump(enhanced_spots, f, ensure_ascii=False, indent=2)

    # Print statistics
    print(f"🗺️ Perimeter Generation Complete!")
    print(f"   Total spots: {stats['total']}")
    print(f"   With exact coordinates: {stats['with_coords']}")
    print(f"   With plausible perimeter: {stats['with_perimeter']}")
    print(f"   No location info: {stats['no_location']}")

    # Show examples of perimeters
    print("\n📍 Example perimeters generated:")
    examples = [s for s in enhanced_spots if s.get("perimeter")][:5]
    for spot in examples:
        p = spot["perimeter"]
        name = spot.get("extracted_name", "Unknown")[:50]
        print(f"   - {name}")
        print(
            f"     → {p['reference']} (radius: {p['radius']/1000:.1f}km, confidence: {p['confidence']})"
        )

    return enhanced_spots


if __name__ == "__main__":
    process_spots()

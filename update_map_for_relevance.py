#!/usr/bin/env python3
"""
Update the enhanced map HTML to use relevance filtering and add layer controls
"""

import json

def create_relevance_aware_map():
    """Create an updated map configuration"""
    
    # Read the filtered spots
    with open('filtered_spots_high_relevance.json', 'r', encoding='utf-8') as f:
        spots = json.load(f)
    
    # Process spots to add relevance categories
    for spot in spots:
        metadata = json.loads(spot['metadata']) if spot['metadata'] else {}
        relevance_score = metadata.get('relevance_score', 10)  # Default high for non-OSM
        
        # Add relevance category
        if relevance_score >= 7:
            spot['relevance_category'] = 'high'
            spot['relevance_label'] = '🌟 Incontournable'
        elif relevance_score >= 5:
            spot['relevance_category'] = 'medium-high'
            spot['relevance_label'] = '⭐ Très intéressant'
        elif relevance_score >= 3:
            spot['relevance_category'] = 'medium'
            spot['relevance_label'] = '📍 Intéressant'
        else:
            spot['relevance_category'] = 'low'
            spot['relevance_label'] = '🔍 À explorer'
    
    # Save enhanced version
    with open('spots_with_relevance.json', 'w', encoding='utf-8') as f:
        json.dump(spots, f, ensure_ascii=False, indent=2)
    
    print(f"✅ Created spots_with_relevance.json with {len(spots)} filtered spots")
    
    # Create JavaScript snippet for layer control
    layer_control_js = """
// Additional layer controls for relevance filtering
const relevanceLayers = {
    high: L.layerGroup(),
    'medium-high': L.layerGroup(),
    medium: L.layerGroup(),
    low: L.layerGroup()
};

// Add relevance filter UI
function addRelevanceFilters() {
    const relevanceSection = `
        <div class="mb-4">
            <h4 class="text-sm font-semibold text-gray-600 mb-2">
                <i class="fas fa-star mr-1"></i> Pertinence
            </h4>
            <div class="space-y-1">
                <label class="flex items-center text-sm">
                    <input type="checkbox" class="mr-2" checked data-relevance="high">
                    <span>🌟 Incontournables</span>
                </label>
                <label class="flex items-center text-sm">
                    <input type="checkbox" class="mr-2" checked data-relevance="medium-high">
                    <span>⭐ Très intéressants</span>
                </label>
                <label class="flex items-center text-sm">
                    <input type="checkbox" class="mr-2" checked data-relevance="medium">
                    <span>📍 Intéressants</span>
                </label>
                <label class="flex items-center text-sm">
                    <input type="checkbox" class="mr-2" data-relevance="low">
                    <span>🔍 À explorer</span>
                </label>
            </div>
        </div>
        
        <div class="mb-4">
            <h4 class="text-sm font-semibold text-gray-600 mb-2">
                <i class="fas fa-database mr-1"></i> Sources
            </h4>
            <div class="space-y-1">
                <label class="flex items-center text-sm">
                    <input type="checkbox" class="mr-2" checked data-source="manual">
                    <span>📝 Contributions</span>
                </label>
                <label class="flex items-center text-sm">
                    <input type="checkbox" class="mr-2" checked data-source="reddit">
                    <span>💬 Reddit</span>
                </label>
                <label class="flex items-center text-sm">
                    <input type="checkbox" class="mr-2" checked data-source="tourism">
                    <span>🏛️ Tourisme</span>
                </label>
                <label class="flex items-center text-sm">
                    <input type="checkbox" class="mr-2" checked data-source="osm">
                    <span>🗺️ OpenStreetMap</span>
                </label>
            </div>
        </div>
    `;
    
    // Insert after existing filters
    document.getElementById('filters').insertAdjacentHTML('beforeend', relevanceSection);
    
    // Add event handlers
    document.querySelectorAll('[data-relevance]').forEach(checkbox => {
        checkbox.addEventListener('change', updateRelevanceLayers);
    });
    
    document.querySelectorAll('[data-source]').forEach(checkbox => {
        checkbox.addEventListener('change', updateSourceLayers);
    });
}

// Update layers based on relevance
function updateRelevanceLayers() {
    // Clear existing markers
    markers.clearLayers();
    
    // Add spots based on active filters
    filteredSpots.forEach(spot => {
        const relevanceCheckbox = document.querySelector(`[data-relevance="${spot.relevance_category}"]`);
        const sourceType = spot.source.includes('osm') ? 'osm' : 
                          spot.source.includes('reddit') ? 'reddit' :
                          spot.source.includes('tourism') ? 'tourism' : 'manual';
        const sourceCheckbox = document.querySelector(`[data-source="${sourceType}"]`);
        
        if (relevanceCheckbox?.checked && sourceCheckbox?.checked) {
            // Add marker with relevance styling
            const marker = createRelevanceMarker(spot);
            markers.addLayer(marker);
        }
    });
}

// Create marker with relevance-based styling
function createRelevanceMarker(spot) {
    const type = spotTypes[spot.type] || spotTypes.unknown;
    let iconSize = [32, 32];
    let opacity = 1;
    
    // Adjust marker based on relevance
    switch(spot.relevance_category) {
        case 'high':
            iconSize = [36, 36];
            break;
        case 'medium-high':
            iconSize = [32, 32];
            break;
        case 'medium':
            iconSize = [28, 28];
            opacity = 0.9;
            break;
        case 'low':
            iconSize = [24, 24];
            opacity = 0.7;
            break;
    }
    
    const icon = L.divIcon({
        html: `<div class="spot-marker" style="opacity: ${opacity}; font-size: ${iconSize[0]}px;">
                ${type.icon}
               </div>`,
        className: 'custom-div-icon',
        iconSize: iconSize,
        iconAnchor: [iconSize[0]/2, iconSize[1]/2]
    });
    
    const marker = L.marker([spot.latitude, spot.longitude], { icon });
    
    // Enhanced popup with relevance info
    const popupContent = `
        ${createPopup(spot)}
        <div class="mt-2 pt-2 border-t">
            <span class="text-xs">${spot.relevance_label}</span>
        </div>
    `;
    
    marker.bindPopup(popupContent);
    return marker;
}
"""
    
    # Save the JavaScript enhancement
    with open('map_relevance_enhancement.js', 'w', encoding='utf-8') as f:
        f.write(layer_control_js)
    
    print("✅ Created map_relevance_enhancement.js")
    
    # Print usage instructions
    print("\n📝 To integrate with enhanced-map.html:")
    print("1. Replace 'enhanced_spots_with_perimeters.json' with 'spots_with_relevance.json'")
    print("2. Add the relevance layer controls from map_relevance_enhancement.js")
    print("3. The map will now show filtered spots with relevance indicators")

if __name__ == "__main__":
    create_relevance_aware_map()